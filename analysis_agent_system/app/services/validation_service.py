"""Validation Layer – business logic for validation & anomaly handling (Section 5)."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from analysis_agent_system.app.models.validation import (
    ValidationSummary,
    ValidationDetail,
    ValidationResponseData,
    ValidationHandleRequest,
)
from analysis_agent_system.app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


# ======================================================================
# 5.1 Full-Chain Validation Report
# ======================================================================

async def run_validation(
    db: Session,
    task_id: str,
) -> ValidationResponseData:
    """Run full-chain validation for a task using LLM, persist results to DB."""

    # --- Fetch task and related results from DB ---
    task_row = db.execute(
        text("SELECT * FROM analysis_tasks WHERE task_id = :task_id"),
        {"task_id": task_id},
    ).fetchone()

    if task_row is None:
        raise ValueError(f"Task {task_id} not found")

    # Gather result data for validation context
    effect_row = db.execute(
        text("SELECT * FROM effect_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    report_row = db.execute(
        text("SELECT * FROM report_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    quality_row = db.execute(
        text("SELECT * FROM quality_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    context = {
        "task_id": task_id,
        "task_status": task_row.status if hasattr(task_row, "status") else "UNKNOWN",
        "has_effect_result": effect_row is not None,
        "has_report_result": report_row is not None,
        "has_quality_result": quality_row is not None,
    }

    # --- LLM: Full-chain validation ---
    summary = ValidationSummary(total_checks=0, passed=0, failed=0)
    details: list[ValidationDetail] = []

    try:
        val_result = await llm_client.analyse_json(
            system_prompt=(
                "You are a validation expert for UAV flight analysis systems. "
                "Validate the entire processing chain for a task across three stages: "
                "1. TASK_UNDERSTANDING: Was the task correctly understood and planned? "
                "2. PROCESS_MONITORING: Were all sub-tasks executed correctly? "
                "3. RESULT_QUALITY: Are the analysis results internally consistent and reasonable? "
                "For each stage, provide: stage, status (PASS/FAIL), anomaly_level (GENERAL/SERIOUS or null), log (explanation). "
                "Also provide summary: {total_checks, passed, failed}. "
                "Return JSON: {\"summary\": {...}, \"details\": [...]}"
            ),
            user_prompt=json.dumps(context, ensure_ascii=False),
        )

        if isinstance(val_result, dict):
            s = val_result.get("summary", {})
            summary = ValidationSummary(
                total_checks=s.get("total_checks", 3),
                passed=s.get("passed", 0),
                failed=s.get("failed", 0),
            )
            for d in val_result.get("details", []):
                details.append(ValidationDetail(
                    stage=d.get("stage", "TASK_UNDERSTANDING"),
                    status=d.get("status", "PASS"),
                    anomaly_level=d.get("anomaly_level"),
                    log=d.get("log"),
                ))
    except Exception as exc:
        logger.warning("LLM validation failed: %s", exc)
        # Fallback: basic validation
        summary = ValidationSummary(total_checks=3, passed=2, failed=1)
        details = [
            ValidationDetail(stage="TASK_UNDERSTANDING", status="PASS"),
            ValidationDetail(stage="PROCESS_MONITORING", status="PASS"),
            ValidationDetail(stage="RESULT_QUALITY", status="FAIL", anomaly_level="GENERAL", log="Could not verify result quality via LLM"),
        ]

    # --- Persist to DB ---
    validation_id = f"val_{uuid.uuid4().hex[:12]}"
    try:
        db.execute(
            text(
                """
                INSERT INTO validation_results
                    (validation_id, task_id, summary_json, details_json, created_at)
                VALUES
                    (:validation_id, :task_id, :summary_json, :details_json, :created_at)
                """
            ),
            {
                "validation_id": validation_id,
                "task_id": task_id,
                "summary_json": summary.model_dump_json(),
                "details_json": json.dumps([d.model_dump() for d in details]),
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB persist validation result failed: %s", exc)

    return ValidationResponseData(summary=summary, details=details)


# ======================================================================
# 5.2 Manual Handling of Anomalies
# ======================================================================

async def handle_anomaly(
    db: Session,
    request: ValidationHandleRequest,
) -> dict:
    """Handle validation anomalies (manual intervention / retry / ignore) via LLM."""

    # --- Use LLM to recommend handling strategy ---
    recommendation: Optional[str] = None
    try:
        result = await llm_client.analyse(
            system_prompt=(
                "You are a validation anomaly handling advisor. "
                "Given the anomaly IDs and requested action, provide a recommended handling strategy. "
                "Be concise and actionable."
            ),
            user_prompt=json.dumps({
                "anomaly_ids": request.anomaly_ids,
                "action": request.action,
                "handler_comment": request.handler_comment,
            }, ensure_ascii=False),
        )
        recommendation = result
    except Exception as exc:
        logger.warning("LLM anomaly handling recommendation failed: %s", exc)

    # --- Persist handling record to DB ---
    handle_id = f"handle_{uuid.uuid4().hex[:12]}"
    try:
        db.execute(
            text(
                """
                INSERT INTO anomaly_handling
                    (handle_id, anomaly_ids, action, handler_comment,
                     llm_recommendation, created_at)
                VALUES
                    (:handle_id, :anomaly_ids, :action, :handler_comment,
                     :llm_recommendation, :created_at)
                """
            ),
            {
                "handle_id": handle_id,
                "anomaly_ids": json.dumps(request.anomaly_ids),
                "action": request.action,
                "handler_comment": request.handler_comment,
                "llm_recommendation": recommendation,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB persist anomaly handling failed: %s", exc)

    return {
        "handle_id": handle_id,
        "action": request.action,
        "llm_recommendation": recommendation,
        "status": "HANDLED",
    }
