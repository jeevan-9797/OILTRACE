import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.attribution import (
    haversine_km,
    calculate_spatial_score,
    calculate_temporal_score,
    calculate_trajectory_score,
    calculate_behaviour_score,
    calculate_environment_score,
)
from app.api.routes.drift import (
    move_point,
    calculate_drift_step,
)
from app.services.georeferencing.dartis import (
    pixel_to_geo,
    calculate_polygon_area_km2,
)
from app.core.timeutil import parse_timestamp, is_valid_coordinate


client = TestClient(app)


# =====================================================================
# 1. CORE UTILITIES & CALCULATIONS
# =====================================================================

def test_haversine_same_point():
    """Haversine distance between the same point should be 0.0 km."""
    d = haversine_km(12.345, 74.567, 12.345, 74.567)
    assert round(d, 4) == 0.0


def test_haversine_known_distance():
    """Haversine distance between two known coordinates."""
    # Approx 1 degree latitude ~ 111 km
    d = haversine_km(0.0, 0.0, 1.0, 0.0)
    assert 110.0 <= d <= 112.0


def test_spatial_scoring():
    """Test spatial score bounds and decay."""
    assert calculate_spatial_score(0.0) == 100.0
    assert calculate_spatial_score(25.0) == 50.0
    assert calculate_spatial_score(50.0) == 0.0
    assert calculate_spatial_score(100.0) == 0.0


def test_temporal_scoring():
    """Test temporal score bounds and decay."""
    t1 = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
    assert calculate_temporal_score(t1, t2) == 100.0

    t3 = t1 + timedelta(hours=12)
    assert calculate_temporal_score(t1, t3) == 50.0

    t4 = t1 + timedelta(hours=24)
    assert calculate_temporal_score(t1, t4) == 0.0


def test_behaviour_scoring():
    """Test vessel behaviour speed scoring."""
    assert calculate_behaviour_score({"speed_knots": 10.0}) == 80.0
    assert calculate_behaviour_score({"speed_knots": 1.0}) == 50.0
    assert calculate_behaviour_score({"speed_knots": 30.0}) == 60.0
    assert calculate_behaviour_score({}) == 50.0


def test_trajectory_scoring():
    """Test trajectory distance to drift points."""
    drift_points = [
        {"latitude": 10.0, "longitude": 20.0},
        {"latitude": 10.1, "longitude": 20.1},
    ]
    # Vessel is at first drift point
    score = calculate_trajectory_score(10.0, 20.0, drift_points)
    assert score == 100.0

    # Vessel is far away
    score_far = calculate_trajectory_score(50.0, 50.0, drift_points)
    assert score_far == 0.0

    # Empty drift points
    assert calculate_trajectory_score(10.0, 20.0, []) == 0.0


def test_environment_scoring():
    """Test environment score calculation against drift points."""
    drift_points = [
        {
            "latitude": 10.0,
            "longitude": 20.0,
            "timestamp": "2026-08-22T12:00:00+00:00"
        }
    ]
    vessel_pos = {
        "latitude": 10.0,
        "longitude": 20.0,
        "timestamp": "2026-08-22T12:00:00+00:00"
    }
    score = calculate_environment_score(vessel_pos, drift_points)
    assert score == 100.0
    assert calculate_environment_score(vessel_pos, []) == 0.0


def test_pixel_to_geo():
    """Test bilinear pixel to geographic conversion."""
    corners = {
        "ul": (20.0, 10.0),  # (lon, lat)
        "ur": (30.0, 10.0),
        "br": (30.0, 0.0),
        "bl": (20.0, 0.0),
    }
    # Top-left pixel (0, 0)
    geo_ul = pixel_to_geo(0, 0, 101, 101, corners)
    assert round(geo_ul[0], 2) == 10.0  # lat
    assert round(geo_ul[1], 2) == 20.0  # lon

    # Center pixel (50, 50)
    geo_center = pixel_to_geo(50, 50, 101, 101, corners)
    assert round(geo_center[0], 2) == 5.0
    assert round(geo_center[1], 2) == 25.0


def test_polygon_area():
    """Test polygon area calculation in km²."""
    # A box in degrees
    polygon = [
        [10.0, 20.0],
        [10.0, 20.1],
        [10.1, 20.1],
        [10.1, 20.0],
    ]
    area = calculate_polygon_area_km2(polygon)
    assert area is not None
    assert area > 0.0
    assert calculate_polygon_area_km2([]) is None


def test_timeutil_parsing():
    """Test timezone-aware timestamp parser."""
    dt = parse_timestamp("2026-08-22T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo == timezone.utc

    assert parse_timestamp(None) is None
    assert parse_timestamp("invalid-date") is None

    assert is_valid_coordinate(12.34, 74.56) is True
    assert is_valid_coordinate(95.0, 0.0) is False
    assert is_valid_coordinate(None, 10.0) is False


def test_move_point():
    """Test geographic point translation."""
    lat, lon = move_point(0.0, 0.0, 111.19, 0.0)  # Move North ~ 1 degree
    assert round(lat, 1) == 1.0
    assert round(lon, 1) == 0.0


# =====================================================================
# 2. FASTAPI ENDPOINTS (WITH MOCK SUPABASE)
# =====================================================================

def test_root_endpoint():
    """Test root endpoint /."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "project": "OILTRACE",
        "status": "running"
    }


@patch("app.api.routes.health.supabase")
def test_health_endpoint_healthy(mock_supabase):
    """Test /api/health when database is connected."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[{"id": "spill-123"}])

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"


@patch("app.api.routes.health.supabase")
def test_health_endpoint_unhealthy(mock_supabase):
    """Test /api/health when database fails returns 503."""
    mock_supabase.table.side_effect = Exception("DB Connection Timeout")

    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["database"] == "disconnected"


@patch("app.api.routes.spill_details.supabase")
def test_spill_details_not_found(mock_supabase):
    """Test GET /api/spills/{spill_id} returns 404 when spill doesn't exist."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])

    response = client.get("/api/spills/NONEXISTENT")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@patch("app.api.routes.spill_details.calculate_attribution_for_spill")
@patch("app.api.routes.spill_details.supabase")
def test_spill_details_success(mock_supabase, mock_attr):
    """Test GET /api/spills/{spill_id} complete payload."""
    mock_spill_table = MagicMock()
    mock_drift_table = MagicMock()
    mock_weather_table = MagicMock()

    def table_side_effect(name):
        if name == "spills":
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.limit.return_value = m
            m.execute.return_value = MagicMock(data=[{
                "id": "uuid-123",
                "spill_code": "SP-001",
                "detected": True,
                "confidence": 0.95,
                "area_km2": 5.2,
                "centroid_latitude": 12.34,
                "centroid_longitude": 74.56,
                "polygon": None,
                "detected_at": "2026-08-22T12:00:00+00:00",
                "estimated_origin_at": "2026-08-22T10:00:00+00:00",
                "estimated_age_hours": 2.0,
                "status": "detected",
                "source_image_id": "sat-img-1",
                "created_at": "2026-08-22T12:05:00+00:00"
            }])
            return m
        elif name == "spill_drift_points":
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.order.return_value = m
            m.execute.return_value = MagicMock(data=[
                {
                    "sequence_no": 1,
                    "latitude": 12.34,
                    "longitude": 74.56,
                    "timestamp": "2026-08-22T10:00:00+00:00",
                    "path_type": "origin",
                    "model_source": "spill-detection",
                    "confidence": 0.95
                },
                {
                    "sequence_no": 2,
                    "latitude": 12.36,
                    "longitude": 74.58,
                    "timestamp": "2026-08-22T13:00:00+00:00",
                    "path_type": "predicted",
                    "model_source": "environmental-drift-v1",
                    "confidence": 0.85
                }
            ])
            return m
        elif name == "weather_ocean_data":
            m = MagicMock()
            m.select.return_value = m
            m.order.return_value = m
            m.limit.return_value = m
            m.execute.return_value = MagicMock(data=[
                {
                    "id": "env-1",
                    "timestamp": "2026-08-22T10:00:00+00:00",
                    "latitude": 12.34,
                    "longitude": 74.56,
                    "wind_speed": 10.0,
                    "wind_direction": 180.0,
                    "current_speed": 1.5,
                    "current_direction": 90.0,
                    "source": "NOAA",
                    "metadata": {}
                }
            ])
            return m
        return MagicMock()

    mock_supabase.table.side_effect = table_side_effect
    mock_attr.return_value = [
        {
            "mmsi": "111222333",
            "vessel_name": "VESSEL ALPHA",
            "spatial_score": 95.0,
            "temporal_score": 90.0,
            "trajectory_score": 85.0,
            "behaviour_score": 80.0,
            "environment_score": 90.0,
            "final_score": 89.2
        }
    ]

    response = client.get("/api/spills/SP-001")
    assert response.status_code == 200
    data = response.json()
    assert "spill" in data
    assert "drift" in data
    assert "attribution" in data
    assert "environment" in data
    assert data["spill"]["spill_code"] == "SP-001"
    assert len(data["drift"]["historical"]) == 1
    assert len(data["drift"]["predicted"]) == 1
    assert data["attribution"]["total_candidates"] == 1
    assert data["attribution"]["top_candidate"]["vessel_name"] == "VESSEL ALPHA"
    assert data["environment"]["latest"] is not None


@patch("app.api.routes.vessels.supabase")
def test_vessels_endpoint_with_missing_position(mock_supabase):
    """Test GET /api/spills/{spill_id}/vessels handles vessels with and without positions."""
    def table_side_effect(name):
        m = MagicMock()
        m.select.return_value = m
        m.eq.return_value = m
        m.limit.return_value = m
        m.order.return_value = m
        if name == "spills":
            m.execute.return_value = MagicMock(data=[{"id": "uuid-1", "spill_code": "SP-001"}])
        elif name == "vessels":
            m.execute.return_value = MagicMock(data=[
                {"mmsi": "123456789", "name": "VESSEL ONE"},
                {"mmsi": "987654321", "name": "VESSEL TWO (NO POSITION)"},
            ])
        elif name == "vessel_positions":
            m.execute.return_value = MagicMock(data=[
                {
                    "mmsi": "123456789",
                    "latitude": 12.34,
                    "longitude": 74.56,
                    "speed_knots": 12.0,
                    "heading_deg": 180.0,
                    "timestamp": "2026-08-22T12:00:00+00:00"
                }
            ])
        return m

    mock_supabase.table.side_effect = table_side_effect

    response = client.get("/api/spills/SP-001/vessels")
    assert response.status_code == 200
    vessels = response.json()
    assert len(vessels) == 2
    # First vessel has position
    assert vessels[0]["mmsi"] == "123456789"
    assert vessels[0]["latitude"] == 12.34
    # Second vessel has null position but metadata is preserved
    assert vessels[1]["mmsi"] == "987654321"
    assert vessels[1]["latitude"] is None
    assert vessels[1]["name"] == "VESSEL TWO (NO POSITION)"


@patch("app.api.routes.attribution.calculate_attribution_for_spill")
@patch("app.api.routes.attribution.supabase")
def test_attribution_endpoint(mock_supabase, mock_attr):
    """Test GET /api/spills/{spill_id}/attribution."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[{"id": "uuid-1", "spill_code": "SP-001"}])

    mock_attr.return_value = [
        {
            "mmsi": "111222333",
            "vessel_name": "VESSEL BRAVO",
            "spatial_score": 96.7,
            "temporal_score": 95.0,
            "trajectory_score": 96.0,
            "behaviour_score": 80.0,
            "environment_score": 95.0,
            "final_score": 96.7
        }
    ]

    response = client.get("/api/spills/SP-001/attribution")
    assert response.status_code == 200
    data = response.json()
    assert data["spill_id"] == "SP-001"
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["vessel_name"] == "VESSEL BRAVO"
    assert data["candidates"][0]["final_score"] == 96.7


@patch("app.api.routes.drift.supabase")
def test_drift_endpoint(mock_supabase):
    """Test GET /api/spills/{spill_id}/drift."""
    def table_side_effect(name):
        m = MagicMock()
        m.select.return_value = m
        m.eq.return_value = m
        m.limit.return_value = m
        m.order.return_value = m
        if name == "spills":
            m.execute.return_value = MagicMock(data=[{
                "id": "uuid-1",
                "spill_code": "SP-001",
                "centroid_latitude": 12.34,
                "centroid_longitude": 74.56
            }])
        elif name == "spill_drift_points":
            m.execute.return_value = MagicMock(data=[
                {
                    "sequence_no": 1,
                    "latitude": 12.34,
                    "longitude": 74.56,
                    "timestamp": "2026-08-22T10:00:00+00:00",
                    "path_type": "origin"
                },
                {
                    "sequence_no": 2,
                    "latitude": 12.36,
                    "longitude": 74.58,
                    "timestamp": "2026-08-22T13:00:00+00:00",
                    "path_type": "predicted"
                }
            ])
        return m

    mock_supabase.table.side_effect = table_side_effect

    response = client.get("/api/spills/SP-001/drift")
    assert response.status_code == 200
    data = response.json()
    assert data["spill_id"] == "SP-001"
    assert len(data["historical_path"]) == 1
    assert len(data["predicted_path"]) == 1


# =====================================================================
# 3. UPLOAD VALIDATION TESTS
# =====================================================================

def test_detect_upload_invalid_file_extension():
    """Test POST /api/spills/detect rejects non-image files."""
    files = {"image": ("test.txt", b"dummy text content", "text/plain")}
    response = client.post("/api/spills/detect", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_detect_upload_empty_file():
    """Test POST /api/spills/detect rejects empty files."""
    files = {"image": ("test.jpg", b"", "image/jpeg")}
    response = client.post("/api/spills/detect", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
