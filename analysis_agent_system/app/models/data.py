"""Models for Input Layer (Section 2): data upload & sensor push."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 2.1 Multimodal Data Upload
# ---------------------------------------------------------------------------

class DataType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    TEXT = "TEXT"


class GPSInfo(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    altitude: Optional[float] = Field(None, description="Altitude in meters")


class MetadataExtracted(BaseModel):
    gps: Optional[GPSInfo] = None
    shoot_time: Optional[str] = Field(None, description="Shoot time in ISO 8601 format")
    camera_params: Optional[str] = Field(None, description="Camera parameters")


class UploadResponseData(BaseModel):
    data_id: str = Field(..., description="Unique ID for the uploaded data")
    data_type: DataType
    storage_path: str = Field(..., description="Storage path (e.g. minio://...)")
    metadata_extracted: Optional[MetadataExtracted] = None
    status: str = Field("PREPROCESSED", description="Processing status")


# ---------------------------------------------------------------------------
# 2.2 Sensor High-Frequency Data Push
# ---------------------------------------------------------------------------

class IMUData(BaseModel):
    pitch: float
    roll: float
    yaw: float


class BatteryData(BaseModel):
    level: int = Field(..., ge=0, le=100, description="Battery level (%)")
    voltage: float = Field(..., description="Voltage (V)")
    current: float = Field(..., description="Current (A)")


class SensorPushRequest(BaseModel):
    device_id: str = Field(..., description="Device identifier (e.g. UAV_001)")
    timestamp: int = Field(..., description="Unix timestamp in ms")
    gps: GPSInfo
    imu: Optional[IMUData] = None
    battery: Optional[BatteryData] = None


class SensorPushResponseData(BaseModel):
    received_count: int = Field(1, description="Number of data points received")
    anomaly_detected: bool = Field(False, description="Whether anomaly was detected")
