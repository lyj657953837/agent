"""Models for Task Planning Layer (Section 3): task creation & progress."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 3.1 Create and Dispatch Analysis Task
# ---------------------------------------------------------------------------

class TaskConstraints(BaseModel):
    target_area_geo: Optional[str] = Field(None, description="WKT geometry for target area")
    priority: Optional[str] = Field("NORMAL", description="Task priority: HIGH / NORMAL / LOW")


class CreateTaskRequest(BaseModel):
    task_name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    data_ids: list[str] = Field(default_factory=list, description="Related data IDs")
    constraints: Optional[TaskConstraints] = None


class SubTask(BaseModel):
    sub_task_id: str
    assigned_agent: str
    action: str
    dependence: list[str] = Field(default_factory=list)


class CreateTaskResponseData(BaseModel):
    task_id: str
    status: str = "PLANNED"
    sub_tasks: list[SubTask] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 3.2 Get Task Global Progress
# ---------------------------------------------------------------------------

class AgentStatus(BaseModel):
    status: str = Field(..., description="PENDING / EXECUTING / COMPLETED / FAILED")
    progress: float = Field(..., ge=0, le=100)


class ResourceUsage(BaseModel):
    cpu_usage: str
    gpu_usage: str
    memory_usage: str


class TaskProgressResponseData(BaseModel):
    task_id: str
    overall_status: str = Field(..., description="PLANNED / EXECUTING / COMPLETED / FAILED")
    progress_percent: float = Field(..., ge=0, le=100)
    agents_status: dict[str, AgentStatus] = Field(default_factory=dict)
    resource_usage: Optional[ResourceUsage] = None
