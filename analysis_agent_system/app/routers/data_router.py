"""Data Management Layer – FastAPI router (Section 2)."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from analysis_agent_system.app.models.common import ApiResponse, success_response, error_response
from analysis_agent_system.app.models.data import (
    DataType,
    GPSInfo,
    SensorPushRequest,
    SensorPushResponseData,
    UploadResponseData,
)
from analysis_agent_system.app.services import data_service
from analysis_agent_system.app.services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data", tags=["Data Management"])


# ======================================================================
# 2.1 Multimodal Data Upload
# ======================================================================

@router.post(
    "/upload",
    summary="Upload multimodal data (image/video/audio/text)",
    response_model=ApiResponse[UploadResponseData],
)
async def upload_data(
    file: UploadFile = File(..., description="The uploaded file"),
    data_type: DataType = Form(..., description="IMAGE / VIDEO / AUDIO / TEXT"),
    lat: Optional[float] = Form(None, description="Latitude"),
    lon: Optional[float] = Form(None, description="Longitude"),
    altitude: Optional[float] = Form(None, description="Altitude in meters"),
    shoot_time: Optional[str] = Form(None, description="Shoot time ISO 8601"),
    camera_params: Optional[str] = Form(None, description="Camera parameters"),
    db: Session = Depends(get_db),
):
    """Upload a data file, extract metadata via LLM, and persist to DB."""
    try:
        # Build optional GPS
        gps = GPSInfo(lat=lat, lon=lon, altitude=altitude) if (lat is not None and lon is not None) else None

        result = await data_service.upload_data(
            db,
            file_name=file.filename or "unknown",
            data_type=data_type,
            storage_path=f"./uploads/{file.filename}",
            gps=gps,
            shoot_time=shoot_time,
            camera_params=camera_params,
        )
        return success_response(data=result.model_dump())
    except Exception as exc:
        logger.exception("Upload failed")
        return error_response(code=500, message=str(exc))


# ======================================================================
# 2.2 Sensor High-Frequency Data Push
# ======================================================================

@router.post(
    "/sensor/push",
    summary="Push high-frequency sensor data",
    response_model=ApiResponse[SensorPushResponseData],
)
async def push_sensor_data(
    request: SensorPushRequest,
    db: Session = Depends(get_db),
):
    """Receive sensor data, persist to DB, run anomaly detection via LLM."""
    try:
        result = await data_service.push_sensor_data(db, request)
        return success_response(data=result.model_dump())
    except Exception as exc:
        logger.exception("Sensor push failed")
        return error_response(code=500, message=str(exc))
