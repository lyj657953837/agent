"""Common response models and utilities."""
from __future__ import annotations

import time
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Unified response structures (Section 1.1)
# ---------------------------------------------------------------------------

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    code: int = Field(200, description="Business status code")
    message: str = Field("Execution successful", description="Message")
    data: Optional[T] = Field(None, description="Response payload")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Unix timestamp in ms")


class PaginationData(BaseModel, Generic[T]):
    """Paginated list wrapper."""
    total: int
    page_num: int
    page_size: int
    list: list[T]


# ---------------------------------------------------------------------------
# Helper to build responses
# ---------------------------------------------------------------------------

def success_response(data: Any = None, message: str = "Execution successful") -> dict:
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }


def error_response(code: int, message: str) -> dict:
    return {
        "code": code,
        "message": message,
        "data": None,
        "timestamp": int(time.time() * 1000),
    }
