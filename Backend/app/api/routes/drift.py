from fastapi import APIRouter

router = APIRouter(
    prefix="/api",
    tags=["Drift"]
)


MOCK_DRIFT = {
    "spill_id": "SP-001",

    "origin": {
        "latitude": 12.320,
        "longitude": 74.540
    },

    "historical_path": [
        {
            "latitude": 12.320,
            "longitude": 74.540,
            "timestamp": "2026-08-22T08:30:00"
        },
        {
            "latitude": 12.325,
            "longitude": 74.545,
            "timestamp": "2026-08-22T09:30:00"
        },
        {
            "latitude": 12.330,
            "longitude": 74.550,
            "timestamp": "2026-08-22T10:30:00"
        },
        {
            "latitude": 12.337,
            "longitude": 74.558,
            "timestamp": "2026-08-22T11:30:00"
        }
    ],

    "predicted_path": [
        {
            "latitude": 12.345,
            "longitude": 74.567,
            "timestamp": "2026-08-22T13:30:00"
        },
        {
            "latitude": 12.355,
            "longitude": 74.578,
            "timestamp": "2026-08-22T14:30:00"
        },
        {
            "latitude": 12.367,
            "longitude": 74.590,
            "timestamp": "2026-08-22T15:30:00"
        }
    ]
}


@router.get("/spills/{spill_id}/drift")
def get_drift(spill_id: str):

    if spill_id != MOCK_DRIFT["spill_id"]:
        return {
            "error": "Drift data not found"
        }

    return MOCK_DRIFT