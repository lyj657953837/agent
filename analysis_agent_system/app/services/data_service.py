"""Data Management Layer – business logic for data upload & sensor push."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from analysis_agent_system.app.models.data import (
    DataType,
    GPSInfo,
    MetadataExtracted,
    UploadResponseData,
    SensorPushRequest,
    SensorPushResponseData,
)
from analysis_agent_system.app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


# ======================================================================
# 2.1 Multimodal Data Upload
# ======================================================================

async def upload_data(
    db: Session,
    *,
    file_name: str,
    data_type: DataType,
    storage_path: str,
    gps: Optional[GPSInfo] = None,
    shoot_time: Optional[str] = None,
    camera_params: Optional[str] = None,
) -> UploadResponseData:
    """Process an uploaded data file: extract metadata via LLM, persist to DB."""

    data_id = f"data_{uuid.uuid4().hex[:12]}"

    # --- Use LLM to extract / enrich metadata if enough info is provided ---
    metadata_extracted: Optional[MetadataExtracted] = None
    try:
        user_content = json.dumps({
            "file_name": file_name,
            "data_type": data_type.value,
            "gps": gps.model_dump() if gps else None,
            "shoot_time": shoot_time,
            "camera_params": camera_params,
        }, ensure_ascii=False)

        result = await llm_client.analyse_json(
            system_prompt=(
                "You are a metadata extraction assistant for UAV/drone multimedia data. "
                "Given file information, extract or infer metadata (GPS, shoot_time, camera_params). "
                "Return a JSON object with keys: gps (object with lat, lon, altitude or null), "
                "shoot_time (ISO 8601 string or null), camera_params (string or null). "
                "If a field cannot be inferred, set it to null."
            ),
            user_prompt=user_content,
        )
        if isinstance(result, dict):
            gps_data = result.get("gps")
            metadata_extracted = MetadataExtracted(
                gps=GPSInfo(**gps_data) if gps_data else gps,
                shoot_time=result.get("shoot_time"),
                camera_params=result.get("camera_params"),
            )
    except Exception as exc:
        logger.warning("LLM metadata extraction failed for %s: %s", data_id, exc)
        # Fallback: use what the caller already provided
        metadata_extracted = MetadataExtracted(
            gps=gps,
            shoot_time=shoot_time,
            camera_params=camera_params,
        )

    # --- Persist to database ---
    try:
        db.execute(
            text(
                """
                INSERT INTO uploaded_data
                    (data_id, file_name, data_type, storage_path,
                     metadata_extracted, status, created_at)
                VALUES
                    (:data_id, :file_name, :data_type, :storage_path,
                     :metadata_extracted, :status, :created_at)
                """
            ),
            {
                "data_id": data_id,
                "file_name": file_name,
                "data_type": data_type.value,
                "storage_path": storage_path,
                "metadata_extracted": metadata_extracted.model_dump_json() if metadata_extracted else None,
                "status": "PREPROCESSED",
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB insert failed for %s: %s", data_id, exc)
        raise

    return UploadResponseData(
        data_id=data_id,
        data_type=data_type,
        storage_path=storage_path,
        metadata_extracted=metadata_extracted,
        status="PREPROCESSED",
    )


# ======================================================================
# 2.2 Sensor High-Frequency Data Push
# ======================================================================

async def push_sensor_data(
    db: Session,
    request: SensorPushRequest,
) -> SensorPushResponseData:
    """Receive high-frequency sensor data, run anomaly detection via LLM."""

    # --- Persist raw sensor data ---
    try:
        db.execute(
            text(
                """
                INSERT INTO sensor_data
                    (device_id, timestamp, gps_lat, gps_lon, gps_altitude,
                     imu_pitch, imu_roll, imu_yaw,
                     battery_level, battery_voltage, battery_current,
                     created_at)
                VALUES
                    (:device_id, :timestamp, :gps_lat, :gps_lon, :gps_altitude,
                     :imu_pitch, :imu_roll, :imu_yaw,
                     :battery_level, :battery_voltage, :battery_current,
                     :created_at)
                """
            ),
            {
                "device_id": request.device_id,
                "timestamp": request.timestamp,
                "gps_lat": request.gps.lat,
                "gps_lon": request.gps.lon,
                "gps_altitude": request.gps.altitude,
                "imu_pitch": request.imu.pitch if request.imu else None,
                "imu_roll": request.imu.roll if request.imu else None,
                "imu_yaw": request.imu.yaw if request.imu else None,
                "battery_level": request.battery.level if request.battery else None,
                "battery_voltage": request.battery.voltage if request.battery else None,
                "battery_current": request.battery.current if request.battery else None,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB insert sensor data failed: %s", exc)
        raise

    # --- Anomaly detection via LLM ---
    anomaly_detected = False
    try:
        result = await llm_client.analyse_json(
            system_prompt=(
                "You are an anomaly detection system for UAV/drone sensor data. "
                "Analyze the sensor reading and determine if there is an anomaly. "
                "Return JSON: {\"anomaly_detected\": true/false, \"reason\": \"...\"}"
            ),
            user_prompt=request.model_dump_json(),
        )
        if isinstance(result, dict):
            anomaly_detected = result.get("anomaly_detected", False)
    except Exception as exc:
        logger.warning("LLM anomaly detection failed: %s", exc)

    return SensorPushResponseData(
        received_count=1,
        anomaly_detected=anomaly_detected,
    )
