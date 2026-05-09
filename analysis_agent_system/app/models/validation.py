"""Models for Validation Layer (Section 5): validation report & manual handling."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 5.1 Full-Chain Validation Report
# ---------------------------------------------------------------------------

class ValidationSummary(BaseModel):
    total_checks: int
    passed: int
    failed: int


class ValidationDetail(BaseModel):
    stage: str = Field(..., description="TASK_UNDERSTANDING / PROCESS_MONITORING / RESULT_QUALITY")
    status: str = Field(..., description="PASS / FAIL")
    anomaly_level: Optional[str] = Field(None, description="GENERAL / SERIOUS (only when FAIL)")
    log: Optional[str] = None


class ValidationResponseData(BaseModel):
    summary: ValidationSummary
    details: list[ValidationDetail] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 5.2 Manual Handling of Anomalies
# ---------------------------------------------------------------------------

class ValidationHandleRequest(BaseModel):
    anomaly_ids: list[str] = Field(..., description="IDs of anomalies to handle")
    action: str = Field("MANUAL_INTERVENTION", description="MANUAL_INTERVENTION / RETRY / IGNORE")
    handler_comment: Optional[str] = Field(None, description="Handler's comment")
