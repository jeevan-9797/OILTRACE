from pydantic import BaseModel


class Vessel(BaseModel):
    mmsi: str
    name: str
    latitude: float
    longitude: float
    speed: float
    heading: float
    timestamp: str