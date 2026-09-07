from pydantic import BaseModel
from typing import List, Optional


class Centroid(BaseModel):
    latitude: float
    longitude: float


class SpillResponse(BaseModel):
    spill_id: str
    detected: bool
    confidence: float
    area_km2: float
    centroid: Centroid
    polygon: List[List[float]]
    estimated_time: Optional[str] = None