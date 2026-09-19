"""
OILTRACE Demo AIS Seeding Script (P2: Geographic Alignment)

SYNTHETIC DEMO AIS DATA NOTICE:
This script populates synthetic demo AIS positions geographically aligned with the
Sentinel-1 DARTIS demonstration SAR image: evaluation/test_images/oc-0001.jpg
Location: Levantine Basin / Karpas Peninsula, Cyprus (35.80°N, 34.45°E)

Vessels:
- 211234567 (VESSEL ALPHA)   : Primary suspect tanker passing ~180m from slick origin with a speed drop
- 355987654 (VESSEL BRAVO)   : Secondary candidate container ship passing ~14.6 km north at cruise speed
- 412876543 (VESSEL CHARLIE) : Weaker candidate bulk carrier passing ~28.0 km south
- 538009876 (VESSEL DELTA)   : Deliberately distant vessel near Limassol (~180 km away, P1-excluded)

Existing Mumbai seed positions are preserved.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add Backend root to sys.path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.core.database import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("oiltrace.seed_demo_ais")


def seed_demo_ais(reference_time: datetime | None = None, clean_only: bool = False):
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    elif reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    logger.info("Reference timestamp for demo AIS: %s", reference_time.isoformat())

    # 1. Clean existing Cyprus demo records if any exist
    try:
        # Delete previous demo positions in Cyprus bounding box (lat 34-37, lon 32-36)
        # Note: gte and lte filters clean previous demo points while keeping Mumbai points (lat ~19, lon ~72)
        delete_resp = (
            supabase
            .table("vessel_positions")
            .delete()
            .gte("latitude", 34.0)
            .lte("latitude", 37.0)
            .gte("longitude", 32.0)
            .lte("longitude", 36.0)
            .execute()
        )
        logger.info("Cleaned previous Cyprus demo AIS points (if any)")
    except Exception as err:
        logger.warning("Failed to clean previous Cyprus demo points: %s", err)

    if clean_only:
        logger.info("Clean-only mode requested. Exiting.")
        return

    # 2. Ensure VESSEL DELTA exists in vessels table
    vessels_to_ensure = [
        {
            "mmsi": 211234567,
            "name": "VESSEL ALPHA",
            "imo_number": "IMO9245671",
            "vessel_type": "Tanker - Crude Oil",
            "flag": "Panama",
            "length_m": 244.5,
            "width_m": 42.0
        },
        {
            "mmsi": 355987654,
            "name": "VESSEL BRAVO",
            "imo_number": "IMO9432190",
            "vessel_type": "Cargo - Container",
            "flag": "Liberia",
            "length_m": 182.0,
            "width_m": 28.5
        },
        {
            "mmsi": 412876543,
            "name": "VESSEL CHARLIE",
            "imo_number": "IMO9318724",
            "vessel_type": "Bulk Carrier",
            "flag": "Marshall Islands",
            "length_m": 225.0,
            "width_m": 32.2
        },
        {
            "mmsi": 538009876,
            "name": "VESSEL DELTA",
            "imo_number": "IMO9518820",
            "vessel_type": "Tug / Offshore Support",
            "flag": "Cyprus",
            "length_m": 65.0,
            "width_m": 15.0
        }
    ]

    try:
        supabase.table("vessels").upsert(vessels_to_ensure, on_conflict="mmsi").execute()
        logger.info("Vessels table verified / updated (Alpha, Bravo, Charlie, Delta)")
    except Exception as v_err:
        logger.error("Failed to upsert vessels: %s", v_err)
        raise

    # 3. Build Geographically Aligned AIS Track Points for oc-0001 (Center: 35.80°N, 34.45°E)
    demo_positions = [
        # VESSEL ALPHA (Primary suspect, speed drop near origin ~180m away)
        {
            "mmsi": 211234567,
            "timestamp": (reference_time - timedelta(minutes=90)).isoformat(),
            "latitude": 35.8150,
            "longitude": 34.4350,
            "speed_knots": 13.8,
            "heading_deg": 135.0,
            "course_deg": 135.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },
        {
            "mmsi": 211234567,
            "timestamp": (reference_time - timedelta(minutes=60)).isoformat(),
            "latitude": 35.8060,
            "longitude": 34.4500,
            "speed_knots": 8.5,
            "heading_deg": 135.0,
            "course_deg": 135.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },
        {
            "mmsi": 211234567,
            "timestamp": (reference_time - timedelta(minutes=30)).isoformat(),
            "latitude": 35.8010,
            "longitude": 34.4580,
            "speed_knots": 5.2,
            "heading_deg": 135.0,
            "course_deg": 135.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },
        {
            "mmsi": 211234567,
            "timestamp": (reference_time - timedelta(minutes=5)).isoformat(),
            "latitude": 35.7890,
            "longitude": 34.4720,
            "speed_knots": 12.4,
            "heading_deg": 135.0,
            "course_deg": 135.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },

        # VESSEL BRAVO (Secondary candidate, constant cruise ~14.6 km north)
        {
            "mmsi": 355987654,
            "timestamp": (reference_time - timedelta(minutes=180)).isoformat(),
            "latitude": 35.9500,
            "longitude": 34.4000,
            "speed_knots": 16.5,
            "heading_deg": 100.0,
            "course_deg": 100.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },
        {
            "mmsi": 355987654,
            "timestamp": (reference_time - timedelta(minutes=120)).isoformat(),
            "latitude": 35.9400,
            "longitude": 34.4400,
            "speed_knots": 16.5,
            "heading_deg": 100.0,
            "course_deg": 100.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },
        {
            "mmsi": 355987654,
            "timestamp": (reference_time - timedelta(minutes=60)).isoformat(),
            "latitude": 35.9300,
            "longitude": 34.4800,
            "speed_knots": 16.5,
            "heading_deg": 100.0,
            "course_deg": 100.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },

        # VESSEL CHARLIE (Weaker candidate, cruising ~28.0 km south)
        {
            "mmsi": 412876543,
            "timestamp": (reference_time - timedelta(minutes=300)).isoformat(),
            "latitude": 35.5300,
            "longitude": 34.3000,
            "speed_knots": 11.5,
            "heading_deg": 75.0,
            "course_deg": 75.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },
        {
            "mmsi": 412876543,
            "timestamp": (reference_time - timedelta(minutes=240)).isoformat(),
            "latitude": 35.5400,
            "longitude": 34.3600,
            "speed_knots": 11.4,
            "heading_deg": 75.0,
            "course_deg": 75.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },
        {
            "mmsi": 412876543,
            "timestamp": (reference_time - timedelta(minutes=180)).isoformat(),
            "latitude": 35.5500,
            "longitude": 34.4200,
            "speed_knots": 11.2,
            "heading_deg": 75.0,
            "course_deg": 75.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        },

        # VESSEL DELTA (Deliberately ineligible: ~180 km away near Limassol)
        {
            "mmsi": 538009876,
            "timestamp": (reference_time - timedelta(minutes=120)).isoformat(),
            "latitude": 34.6500,
            "longitude": 33.0500,
            "speed_knots": 2.1,
            "heading_deg": 0.0,
            "course_deg": 0.0,
            "navigation_status": "Under way using engine",
            "source": "sample_ais"
        }
    ]

    try:
        insert_resp = supabase.table("vessel_positions").insert(demo_positions).execute()
        logger.info(
            "Successfully seeded %d demo AIS positions for oc-0001.jpg (4 vessels)",
            len(insert_resp.data or demo_positions)
        )
    except Exception as ins_err:
        logger.error("Failed to insert demo AIS positions: %s", ins_err)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo AIS data for oc-0001.jpg")
    parser.add_argument("--reference-time", type=str, default=None, help="Reference ISO timestamp (defaults to current UTC time)")
    parser.add_argument("--clean", action="store_true", help="Only clean Cyprus demo points without inserting new ones")
    args = parser.parse_args()

    ref_dt = None
    if args.reference_time:
        ref_dt = datetime.fromisoformat(args.reference_time.replace("Z", "+00:00"))

    seed_demo_ais(reference_time=ref_dt, clean_only=args.clean)
