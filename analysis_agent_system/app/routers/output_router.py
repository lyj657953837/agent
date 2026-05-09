"""Output Layer – FastAPI router (Section 6)."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from analysis_agent_system.app.config import settings
from analysis_agent_system.app.models.common import ApiResponse, success_response, error_response
from analysis_agent_system.app.models.output import (
    ExportFormat,
    ExportResponseData,
    FeedbackRequest,
    FeedbackResponseData,
    VisualizationResponseData,
)
from analysis_agent_system.app.services import output_service
from analysis_agent_system.app.services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/output", tags=["Output"])


# --- Request models for this router ---

class VisualizationRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to visualize")


class ExportRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to export")
    format: ExportFormat = Field(default_factory=ExportFormat)


class FeedbackSubmission(BaseModel):
    task_id: str = Field(..., description="Task ID for the feedback")
    feedback: FeedbackRequest


# ======================================================================
# 6.1 Visualization Data
# ======================================================================

@router.post(
    "/visualization",
    summary="Get visualization data for a task",
    response_model=ApiResponse[VisualizationResponseData],
)
async def get_visualization(
    request: VisualizationRequest,
    db: Session = Depends(get_db),
):
    """Generate visualization data (geo + charts) for a task using LLM."""
    try:
        result = await output_service.get_visualization(db, request.task_id)
        return success_response(data=result.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Visualization failed")
        return error_response(code=500, message=str(exc))


# ======================================================================
# 6.2 Export Report
# ======================================================================

@router.post(
    "/export",
    summary="Export a task report",
    response_model=ApiResponse[ExportResponseData],
)
async def export_report(
    request: ExportRequest,
    db: Session = Depends(get_db),
):
    """Export a task report in PDF/WORD/HTML/GeoJSON format using LLM."""
    try:
        result = await output_service.export_report(db, request.task_id, request.format)
        return success_response(data=result.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Export failed")
        return error_response(code=500, message=str(exc))


@router.get(
    "/export/{job_id}/download",
    summary="Download exported report file",
)
async def download_export(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Download the exported report file by job ID."""
    from sqlalchemy import text
    
    try:
        # Fetch export job from database
        row = db.execute(
            text("SELECT * FROM export_jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        ).fetchone()
        
        if row is None:
            raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
        
        if row.status != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=f"Export job status is {row.status}, not COMPLETED"
            )
        
        if not row.download_url:
            raise HTTPException(status_code=404, detail="Download URL not available")
        
        # Construct file path
        # The download_url is like "/api/v1/output/export/{job_id}/download"
        # We need to find the actual file based on task_id and format
        task_id = row.task_id
        export_format = row.format.lower()
        
        # Try to find the file in export directory
        export_dir = Path(settings.EXPORT_DIR)
        
        # For PDF and WORD, we actually saved as HTML
        if export_format in ["pdf", "word"]:
            filename = f"report_{task_id}.html"
        else:
            filename = f"report_{task_id}.{export_format}"
        
        file_path = export_dir / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Export file not found: {filename}"
            )
        
        # Determine media type
        media_type_map = {
            "pdf": "application/pdf",
            "word": "application/msword",
            "html": "text/html",
            "geojson": "application/geo+json",
            "json": "application/json",
        }
        media_type = media_type_map.get(export_format, "application/octet-stream")
        
        # Return file
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Download failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ======================================================================
# 6.3 User Feedback
# ======================================================================

@router.post(
    "/feedback",
    summary="Submit user feedback",
    response_model=ApiResponse[FeedbackResponseData],
)
async def submit_feedback(
    request: FeedbackSubmission,
    db: Session = Depends(get_db),
):
    """Submit user feedback with LLM-assisted analysis and RAG sync."""
    try:
        result = await output_service.submit_feedback(db, request.task_id, request.feedback)
        return success_response(data=result.model_dump())
    except Exception as exc:
        logger.exception("Feedback submission failed")
        return error_response(code=500, message=str(exc))
