"""Execution / Result Layer – FastAPI router (Section 4)."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from analysis_agent_system.app.models.common import ApiResponse, success_response, error_response
from analysis_agent_system.app.models.result import (
    EffectResultResponseData,
    ReportResultResponseData,
    QualityResultResponseData,
)
from analysis_agent_system.app.services import result_service
from analysis_agent_system.app.services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/result", tags=["Execution Results"])


# --- Request models for this router ---

class AnalyseEffectRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to analyse")
    data_ids: list[str] = Field(default_factory=list, description="Related data IDs")


class GenerateReportRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to generate report for")
    data_ids: list[str] = Field(default_factory=list, description="Related data IDs")


class ScoreQualityRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to score")
    data_ids: list[str] = Field(default_factory=list, description="Related data IDs")


# ======================================================================
# 4.1 Task Effect Analysis (Sub-Agent 1)
# ======================================================================

@router.post(
    "/effect",
    summary="Task effect analysis (coverage & accuracy)",
    response_model=ApiResponse[EffectResultResponseData],
)
async def analyse_effect(
    request: AnalyseEffectRequest,
    db: Session = Depends(get_db),
):
    """Run coverage & accuracy analysis using LLM."""
    try:
        result = await result_service.analyse_effect(db, request.task_id, request.data_ids)
        return success_response(data=result.model_dump())
    except Exception as exc:
        logger.exception("Effect analysis failed")
        return error_response(code=500, message=str(exc))


# ======================================================================
# 4.2 Automated Report Data (Sub-Agent 2)
# ======================================================================

@router.post(
    "/report",
    summary="Generate automated report data",
    response_model=ApiResponse[ReportResultResponseData],
)
async def generate_report(
    request: GenerateReportRequest,
    db: Session = Depends(get_db),
):
    """Generate automated flight analysis report using LLM."""
    try:
        result = await result_service.generate_report(db, request.task_id, request.data_ids)
        return success_response(data=result.model_dump())
    except Exception as exc:
        logger.exception("Report generation failed")
        return error_response(code=500, message=str(exc))


# ======================================================================
# 4.3 Quality Scoring (Sub-Agent 3)
# ======================================================================

@router.post(
    "/quality",
    summary="Quality scoring and optimization suggestions",
    response_model=ApiResponse[QualityResultResponseData],
)
async def score_quality(
    request: ScoreQualityRequest,
    db: Session = Depends(get_db),
):
    """Run quality scoring and get optimization suggestions using LLM."""
    try:
        result = await result_service.score_quality(db, request.task_id, request.data_ids)
        return success_response(data=result.model_dump())
    except Exception as exc:
        logger.exception("Quality scoring failed")
        return error_response(code=500, message=str(exc))
