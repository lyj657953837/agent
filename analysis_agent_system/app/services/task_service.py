"""Task Orchestration Layer – business logic for task planning & progress."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from analysis_agent_system.app.models.task import (
    CreateTaskRequest,
    CreateTaskResponseData,
    SubTask,
    TaskProgressResponseData,
    AgentStatus,
    ResourceUsage,
)
from analysis_agent_system.app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


# ======================================================================
# 3.1 Create and Dispatch Analysis Task
# ======================================================================

async def create_task(
    db: Session,
    request: CreateTaskRequest,
) -> CreateTaskResponseData:
    """Create an analysis task: use LLM to plan sub-tasks, persist to DB."""

    task_id = f"task_{uuid.uuid4().hex[:12]}"

    # --- Use LLM to decompose the task into sub-tasks ---
    sub_tasks: list[SubTask] = []
    try:
        llm_result = await llm_client.analyse_json(
            system_prompt=(
                "You are an AI task planner for UAV/drone flight analysis. "
                "Given a task description and constraints, decompose it into sub-tasks. "
                "Each sub-task should have: sub_task_id (string), assigned_agent "
                "(one of: EFFECT_ANALYSER, REPORT_GENERATOR, QUALITY_SCORER), "
                "action (string description), dependence (list of sub_task_ids it depends on). "
                "Return JSON: {\"sub_tasks\": [...]}"
            ),
            user_prompt=json.dumps({
                "task_name": request.task_name,
                "description": request.description,
                "data_ids": request.data_ids,
                "constraints": request.constraints.model_dump() if request.constraints else None,
            }, ensure_ascii=False),
        )
        if isinstance(llm_result, dict) and "sub_tasks" in llm_result:
            for st in llm_result["sub_tasks"]:
                sub_tasks.append(SubTask(
                    sub_task_id=st.get("sub_task_id", f"sub_{uuid.uuid4().hex[:8]}"),
                    assigned_agent=st.get("assigned_agent", "EFFECT_ANALYSER"),
                    action=st.get("action", ""),
                    dependence=st.get("dependence", []),
                ))
    except Exception as exc:
        logger.warning("LLM task planning failed for %s: %s", task_id, exc)
        # Fallback: create default sub-tasks
        sub_tasks = [
            SubTask(sub_task_id=f"sub_{uuid.uuid4().hex[:8]}", assigned_agent="EFFECT_ANALYSER", action="Coverage & accuracy analysis", dependence=[]),
            SubTask(sub_task_id=f"sub_{uuid.uuid4().hex[:8]}", assigned_agent="REPORT_GENERATOR", action="Generate automated report", dependence=[]),
            SubTask(sub_task_id=f"sub_{uuid.uuid4().hex[:8]}", assigned_agent="QUALITY_SCORER", action="Quality scoring & optimization", dependence=[]),
        ]

    # --- Persist task to DB ---
    try:
        db.execute(
            text(
                """
                INSERT INTO analysis_tasks
                    (task_id, task_name, description, data_ids, constraints,
                     status, sub_tasks_json, created_at)
                VALUES
                    (:task_id, :task_name, :description, :data_ids, :constraints,
                     :status, :sub_tasks_json, :created_at)
                """
            ),
            {
                "task_id": task_id,
                "task_name": request.task_name,
                "description": request.description,
                "data_ids": json.dumps(request.data_ids),
                "constraints": request.constraints.model_dump_json() if request.constraints else None,
                "status": "PLANNED",
                "sub_tasks_json": json.dumps([st.model_dump() for st in sub_tasks]),
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB insert task failed for %s: %s", task_id, exc)
        raise

    return CreateTaskResponseData(
        task_id=task_id,
        status="PLANNED",
        sub_tasks=sub_tasks,
    )


# ======================================================================
# 3.2 Get Task Global Progress
# ======================================================================

async def get_task_progress(
    db: Session,
    task_id: str,
) -> TaskProgressResponseData:
    """Query task progress: aggregate from DB, enrich with LLM if needed."""

    # --- Fetch task from DB ---
    row = db.execute(
        text("SELECT * FROM analysis_tasks WHERE task_id = :task_id"),
        {"task_id": task_id},
    ).fetchone()

    if row is None:
        raise ValueError(f"Task {task_id} not found")

    # --- Build agents_status from sub-task rows ---
    sub_rows = db.execute(
        text("SELECT * FROM task_sub_tasks WHERE task_id = :task_id"),
        {"task_id": task_id},
    ).fetchall()

    agents_status: dict[str, AgentStatus] = {}
    progress_sum = 0.0
    for sr in sub_rows:
        status = sr.status if hasattr(sr, "status") else "PENDING"
        progress = float(sr.progress if hasattr(sr, "progress") else 0)
        agents_status[sr.assigned_agent] = AgentStatus(status=status, progress=progress)
        progress_sum += progress

    overall_status = row.status if hasattr(row, "status") else "PLANNED"
    progress_percent = progress_sum / len(sub_rows) if sub_rows else 0

    # --- Use LLM to estimate resource usage (optional) ---
    resource_usage: Optional[ResourceUsage] = None
    try:
        llm_result = await llm_client.analyse_json(
            system_prompt=(
                "You are a resource estimator. Given the task progress info, "
                "estimate CPU, GPU, and memory usage as percentage strings. "
                "Return JSON: {\"cpu_usage\": \"...%\", \"gpu_usage\": \"...%\", \"memory_usage\": \"...%\"}"
            ),
            user_prompt=json.dumps({
                "task_id": task_id,
                "overall_status": overall_status,
                "progress_percent": progress_percent,
                "agents_status": {k: v.model_dump() for k, v in agents_status.items()},
            }),
        )
        if isinstance(llm_result, dict):
            resource_usage = ResourceUsage(**llm_result)
    except Exception as exc:
        logger.warning("LLM resource estimation failed: %s", exc)

    return TaskProgressResponseData(
        task_id=task_id,
        overall_status=overall_status,
        progress_percent=progress_percent,
        agents_status=agents_status,
        resource_usage=resource_usage,
    )
