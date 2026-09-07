from typing import Optional
from pydantic import BaseModel


class Vessel(BaseModel):
    mmsi: str
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: Optional[str] = None