"""Execution / Result Layer – business logic for sub-agent results (Section 4)."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from analysis_agent_system.app.models.result import (
    CoverageAnalysis,
    AccuracyAnalysis,
    EffectResultResponseData,
    CoordinateItem,
    CoordinateLocation,
    EvidenceItem,
    RouteEfficiency,
    ObstacleAndEnergy,
    AvoidanceDetail,
    ReportResultResponseData,
    DimensionScore,
    OptimizationSuggestion,
    QualityResultResponseData,
)
from analysis_agent_system.app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


# ======================================================================
# 4.1 Task Effect Analysis (Sub-Agent 1)
# ======================================================================

async def analyse_effect(
    db: Session,
    task_id: str,
    data_ids: list[str],
) -> EffectResultResponseData:
    """Run coverage & accuracy analysis via LLM, persist results to DB."""

    # --- Fetch related data from DB ---
    data_rows = db.execute(
        text("SELECT * FROM uploaded_data WHERE data_id IN :ids"),
        {"ids": tuple(data_ids) if data_ids else ("__none__",)},
    ).fetchall()

    data_summary = [
        {"data_id": r.data_id, "data_type": r.data_type, "storage_path": r.storage_path}
        for r in data_rows
    ] if data_rows else []

    # --- LLM: Coverage analysis ---
    coverage: Optional[CoverageAnalysis] = None
    try:
        cov_result = await llm_client.analyse_json(
            system_prompt=(
                "You are a UAV flight coverage analysis expert. "
                "Given flight data, compute coverage metrics. "
                "Return JSON: {\"total_coverage_rate\": 0.0-1.0, \"valid_coverage_rate\": 0.0-1.0, "
                "\"blind_area_square_meter\": float, \"coverage_uniformity\": \"HIGH\"|\"MEDIUM\"|\"LOW\", "
                "\"heatmap_file_url\": string or null}"
            ),
            user_prompt=json.dumps({"task_id": task_id, "data": data_summary}, ensure_ascii=False),
        )
        if isinstance(cov_result, dict):
            coverage = CoverageAnalysis(**cov_result)
    except Exception as exc:
        logger.warning("LLM coverage analysis failed: %s", exc)
        coverage = CoverageAnalysis(total_coverage_rate=0, valid_coverage_rate=0, blind_area_square_meter=0)

    # --- LLM: Accuracy analysis ---
    accuracy: Optional[AccuracyAnalysis] = None
    try:
        acc_result = await llm_client.analyse_json(
            system_prompt=(
                "You are a UAV flight accuracy analysis expert. "
                "Given flight data, compute accuracy metrics. "
                "Return JSON: {\"track_deviation_meter\": float, \"altitude_deviation_meter\": float, "
                "\"speed_deviation_km_h\": float, \"target_overlap_rate\": 0.0-1.0, "
                "\"env_factors_normalized\": bool}"
            ),
            user_prompt=json.dumps({"task_id": task_id, "data": data_summary}, ensure_ascii=False),
        )
        if isinstance(acc_result, dict):
            accuracy = AccuracyAnalysis(**acc_result)
    except Exception as exc:
        logger.warning("LLM accuracy analysis failed: %s", exc)
        accuracy = AccuracyAnalysis(track_deviation_meter=0, altitude_deviation_meter=0, speed_deviation_km_h=0, target_overlap_rate=0)

    # --- Persist to DB ---
    result_id = f"effect_{uuid.uuid4().hex[:12]}"
    try:
        db.execute(
            text(
                """
                INSERT INTO effect_results
                    (result_id, task_id, coverage_json, accuracy_json, created_at)
                VALUES
                    (:result_id, :task_id, :coverage_json, :accuracy_json, :created_at)
                """
            ),
            {
                "result_id": result_id,
                "task_id": task_id,
                "coverage_json": coverage.model_dump_json() if coverage else None,
                "accuracy_json": accuracy.model_dump_json() if accuracy else None,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB persist effect result failed: %s", exc)

    return EffectResultResponseData(
        coverage_analysis=coverage,
        accuracy_analysis=accuracy,
    )


# ======================================================================
# 4.2 Automated Report Data (Sub-Agent 2)
# ======================================================================

async def generate_report(
    db: Session,
    task_id: str,
    data_ids: list[str],
) -> ReportResultResponseData:
    """Generate automated report data via LLM, persist to DB."""

    # --- Fetch related data from DB ---
    data_rows = db.execute(
        text("SELECT * FROM uploaded_data WHERE data_id IN :ids"),
        {"ids": tuple(data_ids) if data_ids else ("__none__",)},
    ).fetchall()

    data_summary = [
        {"data_id": r.data_id, "data_type": r.data_type}
        for r in data_rows
    ] if data_rows else []

    # --- LLM: Coordinate analysis ---
    coordinates: list[CoordinateItem] = []
    evidence_chain: list[EvidenceItem] = []
    route_efficiency: Optional[RouteEfficiency] = None
    obstacle_and_energy: Optional[ObstacleAndEnergy] = None

    try:
        report_result = await llm_client.analyse_json(
            system_prompt=(
                "You are a UAV flight report generation expert. "
                "Analyze the flight data and generate a comprehensive report with: "
                "1. coordinates: list of {issue, level, location: {lat, lon, altitude, heading}, coord_system, address_desc} "
                "2. evidence_chain: list of {evidence_id, source_data_id, data_hash, blockchain_tx_id, timestamp} "
                "3. route_efficiency: {actual_distance_km, theoretical_distance_km, utilization_rate, turn_count, climb_descent_count, hover_time_min, low_efficiency_reasons} "
                "4. obstacle_and_energy: {avoidance_count, avoidance_details: [{time, type, method}], battery_consumption_curve: [float], high_energy_phase} "
                "Return JSON with these four keys."
            ),
            user_prompt=json.dumps({"task_id": task_id, "data": data_summary}, ensure_ascii=False),
        )

        if isinstance(report_result, dict):
            # Parse coordinates
            for c in report_result.get("coordinates", []):
                loc = c.get("location", {})
                coordinates.append(CoordinateItem(
                    issue=c.get("issue", ""),
                    level=c.get("level", "NORMAL"),
                    location=CoordinateLocation(**loc) if loc else CoordinateLocation(lat=0, lon=0),
                    coord_system=c.get("coord_system", "WGS84"),
                    address_desc=c.get("address_desc"),
                ))

            # Parse evidence chain
            for e in report_result.get("evidence_chain", []):
                evidence_chain.append(EvidenceItem(**e))

            # Parse route efficiency
            re_data = report_result.get("route_efficiency")
            if re_data:
                route_efficiency = RouteEfficiency(**re_data)

            # Parse obstacle & energy
            oe_data = report_result.get("obstacle_and_energy")
            if oe_data:
                obstacle_and_energy = ObstacleAndEnergy(**oe_data)

    except Exception as exc:
        logger.warning("LLM report generation failed: %s", exc)

    # --- Persist to DB ---
    result_id = f"report_{uuid.uuid4().hex[:12]}"
    try:
        db.execute(
            text(
                """
                INSERT INTO report_results
                    (result_id, task_id, coordinates_json, evidence_json,
                     route_efficiency_json, obstacle_energy_json, created_at)
                VALUES
                    (:result_id, :task_id, :coordinates_json, :evidence_json,
                     :route_efficiency_json, :obstacle_energy_json, :created_at)
                """
            ),
            {
                "result_id": result_id,
                "task_id": task_id,
                "coordinates_json": json.dumps([c.model_dump() for c in coordinates]),
                "evidence_json": json.dumps([e.model_dump() for e in evidence_chain]),
                "route_efficiency_json": route_efficiency.model_dump_json() if route_efficiency else None,
                "obstacle_energy_json": obstacle_and_energy.model_dump_json() if obstacle_and_energy else None,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB persist report result failed: %s", exc)

    return ReportResultResponseData(
        coordinates=coordinates,
        evidence_chain=evidence_chain,
        route_efficiency=route_efficiency,
        obstacle_and_energy=obstacle_and_energy,
    )


# ======================================================================
# 4.3 Quality Scoring (Sub-Agent 3)
# ======================================================================

async def score_quality(
    db: Session,
    task_id: str,
    data_ids: list[str],
) -> QualityResultResponseData:
    """Run quality scoring via LLM, persist results to DB."""

    # --- Fetch related data from DB ---
    data_rows = db.execute(
        text("SELECT * FROM uploaded_data WHERE data_id IN :ids"),
        {"ids": tuple(data_ids) if data_ids else ("__none__",)},
    ).fetchall()

    data_summary = [
        {"data_id": r.data_id, "data_type": r.data_type}
        for r in data_rows
    ] if data_rows else []

    # --- LLM: Quality scoring ---
    total_score = 0.0
    dimensions: dict[str, DimensionScore] = {}
    optimization_suggestions: list[OptimizationSuggestion] = []

    try:
        score_result = await llm_client.analyse_json(
            system_prompt=(
                "You are a UAV flight quality scoring expert. "
                "Analyze the flight data and provide: "
                "1. total_score: 0-100 overall score "
                "2. dimensions: dict of dimension_name -> {score: 0-100, weight: 0.0-1.0} "
                "   Dimensions should include: coverage_quality, accuracy_quality, route_efficiency, data_completeness, safety_compliance "
                "3. optimization_suggestions: list of {target_dimension, priority: HIGH|NORMAL|LOW, "
                "   type: PARAMETER_ADJUSTMENT|ROUTE_CHANGE|DATA_SUPPLEMENT, content, expected_effect} "
                "Return JSON with these three keys."
            ),
            user_prompt=json.dumps({"task_id": task_id, "data": data_summary}, ensure_ascii=False),
        )

        if isinstance(score_result, dict):
            total_score = float(score_result.get("total_score", 0))
            for dim_name, dim_data in score_result.get("dimensions", {}).items():
                dimensions[dim_name] = DimensionScore(**dim_data)
            for s in score_result.get("optimization_suggestions", []):
                optimization_suggestions.append(OptimizationSuggestion(**s))

    except Exception as exc:
        logger.warning("LLM quality scoring failed: %s", exc)

    # --- Persist to DB ---
    result_id = f"quality_{uuid.uuid4().hex[:12]}"
    try:
        db.execute(
            text(
                """
                INSERT INTO quality_results
                    (result_id, task_id, total_score, dimensions_json,
                     suggestions_json, created_at)
                VALUES
                    (:result_id, :task_id, :total_score, :dimensions_json,
                     :suggestions_json, :created_at)
                """
            ),
            {
                "result_id": result_id,
                "task_id": task_id,
                "total_score": total_score,
                "dimensions_json": json.dumps({k: v.model_dump() for k, v in dimensions.items()}),
                "suggestions_json": json.dumps([s.model_dump() for s in optimization_suggestions]),
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB persist quality result failed: %s", exc)

    return QualityResultResponseData(
        total_score=total_score,
        dimensions=dimensions,
        optimization_suggestions=optimization_suggestions,
    )
