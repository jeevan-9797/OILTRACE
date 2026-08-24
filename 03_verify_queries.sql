-- ==============================================================================
-- OILTRACE DATABASE VERIFICATION & API QUERY TEST SUITE
-- Target: PostgreSQL / Supabase
-- Purpose: Verify all Backend API queries (Section 16) and constraints (Section 18)
-- ==============================================================================

-- ==============================================================================
-- 1. VERIFY: GET /api/spills/{spill_id} (or by spill_code 'SP-001')
-- Retrieves spill details, polygon GeoJSON, centroid, confidence, and source image
-- ==============================================================================
SELECT 
    s.id AS spill_id,
    s.spill_code,
    s.detected,
    s.confidence,
    s.area_km2,
    s.centroid_latitude,
    s.centroid_longitude,
    s.polygon,
    s.detected_at,
    s.estimated_origin_at,
    s.estimated_age_hours,
    s.status,
    s.created_at,
    img.satellite,
    img.sensor,
    img.acquired_at AS image_acquired_at,
    img.image_url
FROM spills s
LEFT JOIN satellite_images img ON s.source_image_id = img.id
WHERE s.spill_code = 'SP-001' OR s.id = 'f47ac10b-58cc-4372-a567-0e02b2c3d479';

-- ==============================================================================
-- 2. VERIFY: GET /api/spills/{spill_id}/vessels
-- Retrieves all vessels active in the spill area along with their latest known position
-- ==============================================================================
WITH latest_positions AS (
    SELECT DISTINCT ON (mmsi)
        mmsi,
        timestamp AS last_seen_at,
        latitude AS last_lat,
        longitude AS last_lon,
        speed_knots AS last_speed,
        course_deg AS last_course,
        navigation_status
    FROM vessel_positions
    ORDER BY mmsi, timestamp DESC
)
SELECT 
    v.mmsi,
    v.name,
    v.imo_number,
    v.vessel_type,
    v.flag,
    v.length_m,
    v.width_m,
    lp.last_seen_at,
    lp.last_lat,
    lp.last_lon,
    lp.last_speed,
    lp.last_course,
    lp.navigation_status
FROM vessels v
JOIN attribution_scores a ON v.mmsi = a.mmsi
JOIN spills s ON a.spill_id = s.id
LEFT JOIN latest_positions lp ON v.mmsi = lp.mmsi
WHERE s.spill_code = 'SP-001'
ORDER BY a.rank ASC;

-- ==============================================================================
-- 3. VERIFY: GET /api/spills/{spill_id}/drift
-- Retrieves origin, hindcast, and forecast drift points in chronological sequence
-- ==============================================================================
SELECT 
    sdp.id,
    sdp.sequence_no,
    sdp.latitude,
    sdp.longitude,
    sdp.timestamp,
    sdp.path_type,
    sdp.model_source,
    sdp.confidence
FROM spill_drift_points sdp
JOIN spills s ON sdp.spill_id = s.id
WHERE s.spill_code = 'SP-001'
ORDER BY sdp.sequence_no ASC;

-- ==============================================================================
-- 4. VERIFY: GET /api/spills/{spill_id}/attribution
-- Retrieves candidate vessels ranked by final attribution score with explainable evidence
-- ==============================================================================
SELECT 
    a.rank,
    v.name AS vessel_name,
    v.mmsi,
    v.vessel_type,
    v.flag,
    a.final_score,
    a.spatial_score,
    a.temporal_score,
    a.trajectory_score,
    a.behaviour_score,
    a.environment_score,
    a.evidence,
    a.model_version,
    a.created_at
FROM attribution_scores a
JOIN vessels v ON a.mmsi = v.mmsi
JOIN spills s ON a.spill_id = s.id
WHERE s.spill_code = 'SP-001'
ORDER BY a.rank ASC;

-- ==============================================================================
-- 5. VERIFY: GET /api/vessels/{mmsi}
-- Retrieves specific vessel master record and complete historical AIS track
-- ==============================================================================
-- 5a. Vessel Master
SELECT * FROM vessels WHERE mmsi = 211234567;

-- 5b. Vessel AIS Trajectory Track (Ordered chronologically)
SELECT 
    id,
    timestamp,
    latitude,
    longitude,
    speed_knots,
    heading_deg,
    course_deg,
    navigation_status,
    source
FROM vessel_positions
WHERE mmsi = 211234567
ORDER BY timestamp ASC;

-- ==============================================================================
-- 6. CONSTRAINT CHECKS & INTEGRITY VERIFICATIONS
-- ==============================================================================

-- 6a. Verify no orphan vessel_positions exist
SELECT COUNT(*) AS orphan_positions_count
FROM vessel_positions vp
LEFT JOIN vessels v ON vp.mmsi = v.mmsi
WHERE v.mmsi IS NULL;

-- 6b. Verify no orphan attribution_scores exist
SELECT COUNT(*) AS orphan_attribution_count
FROM attribution_scores att
LEFT JOIN spills s ON att.spill_id = s.id
LEFT JOIN vessels v ON att.mmsi = v.mmsi
WHERE s.id IS NULL OR v.mmsi IS NULL;

-- 6c. Verify summary counts across all tables
SELECT 
    (SELECT COUNT(*) FROM satellite_images) AS satellite_images_count,
    (SELECT COUNT(*) FROM spills) AS spills_count,
    (SELECT COUNT(*) FROM vessels) AS vessels_count,
    (SELECT COUNT(*) FROM vessel_positions) AS vessel_positions_count,
    (SELECT COUNT(*) FROM spill_drift_points) AS spill_drift_points_count,
    (SELECT COUNT(*) FROM attribution_scores) AS attribution_scores_count,
    (SELECT COUNT(*) FROM weather_ocean_data) AS weather_ocean_data_count;
