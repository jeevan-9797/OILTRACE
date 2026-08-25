from pydantic import BaseModel
from typing import Optional


class SpillDetectionResult(BaseModel):
    confidence: float
    bbox: list[float]
    centroid: list[float]
    area: float
    polygon: Optional[list[list[float]]] = None