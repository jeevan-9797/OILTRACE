from pydantic import BaseModel
from typing import List


class VesselScore(BaseModel):

    mmsi: str

    vessel_name: str

    spatial_score: float

    temporal_score: float

    trajectory_score: float

    behaviour_score: float

    environment_score: float

    final_score: float


class AttributionResponse(BaseModel):

    spill_id: str

    candidates: List[VesselScore]