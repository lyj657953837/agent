"""Task Orchestration Layer – FastAPI router (Section 3)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from analysis_agent_system.app.models.common import ApiResponse, success_response, error_response
from analysis_agent_system.app.models.task import (
    CreateTaskRequest,
    CreateTaskResponseData,
    TaskProgressResponseData,
)
from analysis_agent_system.app.services import task_service
from analysis_agent_system.app.services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/task", tags=["Task Orchestration"])


# ======================================================================
# 3.1 Create and Dispatch Analysis Task
# ======================================================================

@router.post(
    "/create",
    summary="Create and dispatch an analysis task",
    response_model=ApiResponse[CreateTaskResponseData],
)
async def create_task(
    request: CreateTaskRequest,
    db: Session = Depends(get_db),
):
    """Create a new analysis task. LLM decomposes it into sub-tasks automatically."""
    try:
        result = await task_service.create_task(db, request)
        return success_response(data=result.model_dump())
    except Exception as exc:
        logger.exception("Task creation failed")
        return error_response(code=500, message=str(exc))


# ======================================================================
# 3.2 Get Task Global Progress
# ======================================================================

@router.get(
    "/{task_id}/progress",
    summary="Get task global progress",
    response_model=ApiResponse[TaskProgressResponseData],
)
async def get_task_progress(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Get the overall progress and sub-agent status for a task."""
    try:
        result = await task_service.get_task_progress(db, task_id)
        return success_response(data=result.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Get progress failed")
        return error_response(code=500, message=str(exc))
