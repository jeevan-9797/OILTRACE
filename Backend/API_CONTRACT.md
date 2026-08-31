# OILTRACE API Contract

## 1. Health Check

GET /health

Response:
{
  "status": "healthy"
}


## 2. Oil Spill Detection

POST /api/spills/detect

Input:
- Satellite image

Response:
{
  "spill_id": "SP-001",
  "detected": true,
  "confidence": 0.96,
  "area_km2": 12.4,
  "centroid": {
    "latitude": 12.345,
    "longitude": 74.567
  },
  "polygon": []
}


## 3. Spill Details

GET /api/spills/{spill_id}

Response:
{
  "spill_id": "SP-001",
  "confidence": 0.96,
  "area_km2": 12.4,
  "centroid": {},
  "estimated_time": null
}


## 4. Spill Drift

GET /api/spills/{spill_id}/drift

Response:
{
  "spill_id": "SP-001",
  "origin": {},
  "historical_path": [],
  "predicted_path": []
}


## 5. Nearby Vessels

GET /api/spills/{spill_id}/vessels

Response:
{
  "vessels": [
    {
      "mmsi": "123456789",
      "name": "VESSEL A",
      "latitude": 12.345,
      "longitude": 74.567,
      "speed": 12.4,
      "heading": 183,
      "timestamp": "2026-08-22T12:30:00"
    }
  ]
}


## 6. Vessel Attribution

GET /api/spills/{spill_id}/attribution

Response:
{
  "spill_id": "SP-001",
  "candidates": [
    {
      "mmsi": "123456789",
      "vessel_name": "VESSEL A",
      "spatial_score": 94,
      "temporal_score": 96,
      "trajectory_score": 91,
      "behaviour_score": 83,
      "final_score": 91.4
    }
  ]
}


## 7. Vessel Details

GET /api/vessels/{mmsi}

Response:
{
  "mmsi": "123456789",
  "name": "VESSEL A",
  "positions": []
}