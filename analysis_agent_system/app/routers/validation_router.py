"""Validation Layer – FastAPI router (Section 5)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from analysis_agent_system.app.models.common import ApiResponse, success_response, error_response
from analysis_agent_system.app.models.validation import (
    ValidationHandleRequest,
    ValidationResponseData,
)
from analysis_agent_system.app.services import validation_service
from analysis_agent_system.app.services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/validation", tags=["Validation"])


# --- Request model for validation report ---

class ValidationRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to validate")


# ======================================================================
# 5.1 Full-Chain Validation Report
# ======================================================================

@router.post(
    "/report",
    summary="Run full-chain validation report",
    response_model=ApiResponse[ValidationResponseData],
)
async def run_validation(
    request: ValidationRequest,
    db: Session = Depends(get_db),
):
    """Run a full-chain validation for a task using LLM."""
    try:
        result = await validation_service.run_validation(db, request.task_id)
        return success_response(data=result.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Validation failed")
        return error_response(code=500, message=str(exc))


# ======================================================================
# 5.2 Manual Handling of Anomalies
# ======================================================================

@router.post(
    "/handle",
    summary="Handle validation anomalies",
    response_model=ApiResponse[dict],
)
async def handle_anomaly(
    request: ValidationHandleRequest,
    db: Session = Depends(get_db),
):
    """Handle validation anomalies with LLM-assisted recommendations."""
    try:
        result = await validation_service.handle_anomaly(db, request)
        return success_response(data=result)
    except Exception as exc:
        logger.exception("Anomaly handling failed")
        return error_response(code=500, message=str(exc))
