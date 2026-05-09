"""Models for Execution Layer (Section 4): sub-agent result models."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 4.1 Task Effect Analysis (Sub-Agent 1)
# ---------------------------------------------------------------------------

class CoverageAnalysis(BaseModel):
    total_coverage_rate: float = Field(..., ge=0, le=1)
    valid_coverage_rate: float = Field(..., ge=0, le=1)
    blind_area_square_meter: float = Field(..., ge=0)
    coverage_uniformity: str = Field("MEDIUM", description="HIGH / MEDIUM / LOW")
    heatmap_file_url: Optional[str] = None


class AccuracyAnalysis(BaseModel):
    track_deviation_meter: float
    altitude_deviation_meter: float
    speed_deviation_km_h: float
    target_overlap_rate: float = Field(..., ge=0, le=1)
    env_factors_normalized: bool = False


class EffectResultResponseData(BaseModel):
    coverage_analysis: CoverageAnalysis
    accuracy_analysis: AccuracyAnalysis


# ---------------------------------------------------------------------------
# 4.2 Automated Report Data (Sub-Agent 2)
# ---------------------------------------------------------------------------

class CoordinateLocation(BaseModel):
    lat: float
    lon: float
    altitude: Optional[float] = None
    heading: Optional[float] = None


class CoordinateItem(BaseModel):
    issue: str
    level: str = Field("NORMAL", description="HIGH / NORMAL / LOW")
    location: CoordinateLocation
    coord_system: str = "WGS84"
    address_desc: Optional[str] = None


class EvidenceItem(BaseModel):
    evidence_id: str
    source_data_id: str
    data_hash: str
    blockchain_tx_id: Optional[str] = None
    timestamp: Optional[str] = None


class RouteEfficiency(BaseModel):
    actual_distance_km: float
    theoretical_distance_km: float
    utilization_rate: float = Field(..., ge=0, le=1)
    turn_count: int = 0
    climb_descent_count: int = 0
    hover_time_min: float = 0
    low_efficiency_reasons: list[str] = Field(default_factory=list)


class AvoidanceDetail(BaseModel):
    time: str
    type: str
    method: str


class ObstacleAndEnergy(BaseModel):
    avoidance_count: int = 0
    avoidance_details: list[AvoidanceDetail] = Field(default_factory=list)
    battery_consumption_curve: list[float] = Field(default_factory=list)
    high_energy_phase: Optional[str] = None


class ReportResultResponseData(BaseModel):
    coordinates: list[CoordinateItem] = Field(default_factory=list)
    evidence_chain: list[EvidenceItem] = Field(default_factory=list)
    route_efficiency: Optional[RouteEfficiency] = None
    obstacle_and_energy: Optional[ObstacleAndEnergy] = None


# ---------------------------------------------------------------------------
# 4.3 Quality Scoring (Sub-Agent 3)
# ---------------------------------------------------------------------------

class DimensionScore(BaseModel):
    score: float = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)


class OptimizationSuggestion(BaseModel):
    target_dimension: str
    priority: str = "NORMAL"
    type: str = Field("PARAMETER_ADJUSTMENT", description="PARAMETER_ADJUSTMENT / ROUTE_CHANGE / DATA_SUPPLEMENT")
    content: str
    expected_effect: Optional[str] = None


class QualityResultResponseData(BaseModel):
    total_score: float = Field(..., ge=0, le=100)
    dimensions: dict[str, DimensionScore] = Field(default_factory=dict)
    optimization_suggestions: list[OptimizationSuggestion] = Field(default_factory=list)
