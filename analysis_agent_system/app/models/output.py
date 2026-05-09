"""Models for Output Layer (Section 6): visualization, export, feedback."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 6.1 Visualization Data
# ---------------------------------------------------------------------------

class GeoData(BaseModel):
    flight_trajectory: Optional[dict[str, Any]] = Field(None, description="GeoJSON FeatureCollection")
    coverage_heatmap: Optional[dict[str, Any]] = Field(None, description="GeoJSON FeatureCollection")
    key_findings: Optional[dict[str, Any]] = Field(None, description="GeoJSON FeatureCollection")


class ChartDataPoint(BaseModel):
    time: str
    level: float


class ChartData(BaseModel):
    battery_curve: list[ChartDataPoint] = Field(default_factory=list)


class VisualizationResponseData(BaseModel):
    geo_data: Optional[GeoData] = None
    chart_data: Optional[ChartData] = None


# ---------------------------------------------------------------------------
# 6.2 Export Report
# ---------------------------------------------------------------------------

class ExportFormat(BaseModel):
    format: str = Field("PDF", description="PDF / WORD / HTML / GeoJSON")
    include_evidence_chain: bool = True
    include_validation_report: bool = False


class ExportResponseData(BaseModel):
    job_id: str
    status: str = Field("PROCESSING", description="PROCESSING / COMPLETED / FAILED")
    estimated_time_sec: Optional[int] = None
    download_url: Optional[str] = None


# ---------------------------------------------------------------------------
# 6.3 User Feedback
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    satisfaction_score: float = Field(..., ge=0, le=5, description="Score 0-5")
    user_comment: Optional[str] = None
    corrected_info: Optional[dict[str, Any]] = Field(None, description="User-corrected data")


class FeedbackResponseData(BaseModel):
    feedback_id: str
    rag_sync_status: str = Field("QUEUED", description="QUEUED / SYNCED / FAILED")
