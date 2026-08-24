-- ==============================================================================
-- OILTRACE DEMO & SEED DATASET (SP-001)
-- Target: PostgreSQL / Supabase
-- Purpose: Complete realistic demo dataset for SP-001, AIS tracks, drift points,
--          and explainable attribution scores for SIH Hackathon evaluation.
-- Author: Data / DB Lead
-- ==============================================================================

BEGIN;

-- ==============================================================================
-- 1. SATELLITE IMAGE METADATA
-- ==============================================================================
INSERT INTO satellite_images (
    id,
    provider,
    satellite,
    sensor,
    acquired_at,
    latitude,
    longitude,
    image_url,
    local_path,
    metadata
) VALUES (
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d',
    'Copernicus / ESA',
    'Sentinel-1A',
    'SAR (C-Band Synthetic Aperture Radar)',
    '2026-08-24 06:15:00+00',
    18.9200,
    72.7500,
    'https://storage.oiltrace.ai/satellite-scenes/20260824_S1A_IW_GRDH_SP001.tif',
    '/data/satellite_cache/20260824_S1A_IW_GRDH_SP001.png',
    jsonb_build_object(
        'polarization', 'VV+VH',
        'orbit_direction', 'DESCENDING',
        'relative_orbit', 142,
        'resolution_m', 10.0,
        'swath_width_km', 250,
        'incidence_angle_deg', 37.4,
        'cloud_cover_pct', 0.0
    )
);

-- ==============================================================================
-- 2. SPILL EVENT (SP-001)
-- ==============================================================================
INSERT INTO spills (
    id,
    spill_code,
    detected,
    confidence,
    area_km2,
    centroid_latitude,
    centroid_longitude,
    polygon,
    detected_at,
    estimated_origin_at,
    estimated_age_hours,
    status,
    source_image_id
) VALUES (
    'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    'SP-001',
    TRUE,
    0.9450,
    14.85,
    18.9200,
    72.7500,
    jsonb_build_object(
        'type', 'Polygon',
        'coordinates', jsonb_build_array(
            jsonb_build_array(
                jsonb_build_array(72.7310, 18.9320),
                jsonb_build_array(72.7640, 18.9280),
                jsonb_build_array(72.7720, 18.9110),
                jsonb_build_array(72.7550, 18.9040),
                jsonb_build_array(72.7380, 18.9150),
                jsonb_build_array(72.7310, 18.9320)
            )
        )
    ),
    '2026-08-24 06:30:00+00',
    '2026-08-24 01:15:00+00',
    5.25,
    'investigating',
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d'
);

-- ==============================================================================
-- 3. VESSELS (CANDIDATE FLEET)
-- ==============================================================================
INSERT INTO vessels (mmsi, name, imo_number, vessel_type, flag, length_m, width_m)
VALUES
    (211234567, 'VESSEL ALPHA', 'IMO9245671', 'Tanker - Crude Oil', 'Panama', 244.5, 42.0),
    (355987654, 'VESSEL BRAVO', 'IMO9432190', 'Cargo - Container', 'Liberia', 182.0, 28.5),
    (412876543, 'VESSEL CHARLIE', 'IMO9318724', 'Bulk Carrier', 'Marshall Islands', 225.0, 32.2);

-- ==============================================================================
-- 4. HISTORICAL AIS POSITIONS (vessel_positions)
-- ==============================================================================

-- VESSEL ALPHA (MMSI: 211234567) - Primary Suspect Track (Slowing down & discharging near origin)
INSERT INTO vessel_positions (mmsi, timestamp, latitude, longitude, speed_knots, heading_deg, course_deg, navigation_status, source)
VALUES
    (211234567, '2026-08-24 00:00:00+00', 19.0450, 72.6320, 14.4, 155.0, 154.5, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 00:30:00+00', 19.0180, 72.6550, 14.1, 153.0, 153.2, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 01:00:00+00', 18.9920, 72.6780, 9.5,  152.0, 151.8, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 01:15:00+00', 18.9850, 72.6820, 5.8,  150.0, 150.0, 'Under way using engine', 'sample_ais'), -- Origin intersection & speed drop
    (211234567, '2026-08-24 01:30:00+00', 18.9770, 72.6880, 6.2,  149.0, 149.5, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 02:00:00+00', 18.9520, 72.7050, 11.2, 148.0, 148.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 03:00:00+00', 18.8950, 72.7480, 14.0, 147.0, 147.2, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 04:00:00+00', 18.8350, 72.7910, 14.3, 146.0, 146.5, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 05:00:00+00', 18.7750, 72.8340, 14.2, 146.0, 146.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 06:00:00+00', 18.7150, 72.8770, 14.5, 145.0, 145.2, 'Under way using engine', 'sample_ais');

-- VESSEL BRAVO (MMSI: 355987654) - Secondary Candidate Track (Passed eastward 1 hour earlier at constant cruising speed)
INSERT INTO vessel_positions (mmsi, timestamp, latitude, longitude, speed_knots, heading_deg, course_deg, navigation_status, source)
VALUES
    (355987654, '2026-08-23 23:30:00+00', 19.0800, 72.7500, 16.8, 175.0, 174.5, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-24 00:15:00+00', 19.0100, 72.7550, 16.6, 175.0, 175.0, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-24 01:00:00+00', 18.9400, 72.7600, 16.5, 174.0, 174.2, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-24 01:45:00+00', 18.8700, 72.7650, 16.7, 175.0, 175.1, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-24 02:30:00+00', 18.8000, 72.7700, 16.5, 175.0, 174.8, 'Under way using engine', 'sample_ais');

-- VESSEL CHARLIE (MMSI: 412876543) - Distant Track (Passed 15km offshore west around 04:00 UTC)
INSERT INTO vessel_positions (mmsi, timestamp, latitude, longitude, speed_knots, heading_deg, course_deg, navigation_status, source)
VALUES
    (412876543, '2026-08-24 02:30:00+00', 19.0500, 72.5200, 12.0, 160.0, 160.0, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-08-24 03:30:00+00', 18.9700, 72.5550, 12.2, 160.0, 159.8, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-08-24 04:30:00+00', 18.8900, 72.5900, 12.1, 161.0, 160.5, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-08-24 05:30:00+00', 18.8100, 72.6250, 11.9, 160.0, 160.2, 'Under way using engine', 'sample_ais');

-- ==============================================================================
-- 5. SPILL DRIFT POINTS (spill_drift_points: Origin -> Hindcast -> Observed -> Forecast)
-- ==============================================================================
INSERT INTO spill_drift_points (
    spill_id,
    sequence_no,
    latitude,
    longitude,
    timestamp,
    path_type,
    model_source,
    confidence
) VALUES
    -- 1. Modeled origin (Hindcast point at estimated discharge time)
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 1, 18.9850, 72.6820, '2026-08-24 01:15:00+00', 'origin',     'ocean-current-v1', 0.9100),
    -- 2. Historical drift hindcast progression
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 2, 18.9620, 72.7050, '2026-08-24 03:00:00+00', 'historical', 'ocean-current-v1', 0.9250),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 3, 18.9380, 72.7310, '2026-08-24 05:00:00+00', 'historical', 'ocean-current-v1', 0.9400),
    -- 3. Satellite Detection Observation point
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 4, 18.9200, 72.7500, '2026-08-24 06:30:00+00', 'historical', 'sentinel-1-sar',  0.9450),
    -- 4. Forward drift trajectory forecasts
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 5, 18.8980, 72.7750, '2026-08-24 09:30:00+00', 'predicted',  'ocean-current-v1', 0.8800),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 6, 18.8740, 72.8020, '2026-08-24 12:30:00+00', 'predicted',  'ocean-current-v1', 0.8200),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 7, 18.8350, 72.8450, '2026-08-24 18:30:00+00', 'predicted',  'ocean-current-v1', 0.7400);

-- ==============================================================================
-- 6. ATTRIBUTION SCORES (Explainable multi-criteria ranking)
-- ==============================================================================

-- 1. VESSEL ALPHA - Rank 1 (Primary Suspect)
INSERT INTO attribution_scores (
    spill_id,
    mmsi,
    spatial_score,
    temporal_score,
    trajectory_score,
    behaviour_score,
    environment_score,
    final_score,
    rank,
    evidence,
    model_version
) VALUES (
    'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    211234567,
    96.50,
    93.00,
    91.00,
    86.50,
    88.00,
    91.20,
    1,
    jsonb_build_object(
        'risk_level', 'HIGH',
        'closest_approach_km', 0.12,
        'time_delta_mins', 4.5,
        'speed_drop_detected', TRUE,
        'speed_before_knots', 14.1,
        'speed_during_knots', 5.8,
        'speed_drop_percentage', 58.8,
        'drift_hindcast_overlap_pct', 95.4,
        'vessel_type_risk_weight', 1.25,
        'explanation_summary', 'Vessel Alpha passed directly through the hindcast discharge origin within 120m. Recorded an acute speed drop of 58.8% during transit.',
        'key_evidence_factors', jsonb_build_array(
            'Direct spatial intersection with estimated discharge origin (0.12 km CPA)',
            'Temporal synchronization with hindcast origin timestamp (Delta: 4.5 min)',
            'Sharp speed reduction from 14.1 kn to 5.8 kn characteristic of operational discharge',
            'Slick elongation vector (148 deg) matches vessel heading (150 deg)',
            'Crude oil tanker vessel type has highest risk profile'
        )
    ),
    'oiltrace-attribution-v1.0'
);

-- 2. VESSEL BRAVO - Rank 2 (Secondary Candidate)
INSERT INTO attribution_scores (
    spill_id,
    mmsi,
    spatial_score,
    temporal_score,
    trajectory_score,
    behaviour_score,
    environment_score,
    final_score,
    rank,
    evidence,
    model_version
) VALUES (
    'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    355987654,
    44.00,
    52.00,
    41.00,
    28.00,
    45.00,
    42.00,
    2,
    jsonb_build_object(
        'risk_level', 'LOW',
        'closest_approach_km', 4.85,
        'time_delta_mins', 75.0,
        'speed_drop_detected', FALSE,
        'speed_before_knots', 16.8,
        'speed_during_knots', 16.5,
        'speed_drop_percentage', 1.8,
        'drift_hindcast_overlap_pct', 38.2,
        'vessel_type_risk_weight', 0.90,
        'explanation_summary', 'Vessel Bravo passed 4.85 km east of origin point 1.25 hours earlier at steady cruising speed.',
        'key_evidence_factors', jsonb_build_array(
            'Distance to slick origin: 4.85 km (outside immediate discharge envelope)',
            'Constant speed maintained (16.5-16.8 kn) with no loitering or speed anomaly',
            'Cross-track current makes slick drift from this position unlikely'
        )
    ),
    'oiltrace-attribution-v1.0'
);

-- 3. VESSEL CHARLIE - Rank 3 (Low Probability)
INSERT INTO attribution_scores (
    spill_id,
    mmsi,
    spatial_score,
    temporal_score,
    trajectory_score,
    behaviour_score,
    environment_score,
    final_score,
    rank,
    evidence,
    model_version
) VALUES (
    'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    412876543,
    15.00,
    18.00,
    12.00,
    10.00,
    14.00,
    13.80,
    3,
    jsonb_build_object(
        'risk_level', 'NEGLIGIBLE',
        'closest_approach_km', 14.60,
        'time_delta_mins', 195.0,
        'speed_drop_detected', FALSE,
        'speed_before_knots', 12.0,
        'speed_during_knots', 12.1,
        'speed_drop_percentage', 0.0,
        'drift_hindcast_overlap_pct', 8.5,
        'vessel_type_risk_weight', 0.85,
        'explanation_summary', 'Vessel Charlie operated >14 km offshore with no correlation to slick trajectory.',
        'key_evidence_factors', jsonb_build_array(
            'Distant passage (>14.6 km) west of slick hindcast corridor',
            'Temporal misalignment (>3 hours after origin)',
            'Zero anomalous navigation indicators'
        )
    ),
    'oiltrace-attribution-v1.0'
);

-- ==============================================================================
-- 7. WEATHER & OCEAN DATA (ENVIRONMENTAL CORRIDOR)
-- ==============================================================================
INSERT INTO weather_ocean_data (
    timestamp,
    latitude,
    longitude,
    wind_speed,
    wind_direction,
    current_speed,
    current_direction,
    source,
    metadata
) VALUES
    ('2026-08-24 01:00:00+00', 18.9500, 72.7000, 12.4, 310.0, 0.45, 140.0, 'NOAA_GFS_CMEMS', '{"sea_temp_c": 28.5, "wave_height_m": 1.2}'::jsonb),
    ('2026-08-24 03:00:00+00', 18.9500, 72.7000, 13.1, 315.0, 0.48, 142.0, 'NOAA_GFS_CMEMS', '{"sea_temp_c": 28.4, "wave_height_m": 1.3}'::jsonb),
    ('2026-08-24 05:00:00+00', 18.9500, 72.7000, 14.0, 318.0, 0.52, 145.0, 'NOAA_GFS_CMEMS', '{"sea_temp_c": 28.3, "wave_height_m": 1.4}'::jsonb),
    ('2026-08-24 06:30:00+00', 18.9200, 72.7500, 14.5, 320.0, 0.55, 146.0, 'NOAA_GFS_CMEMS', '{"sea_temp_c": 28.2, "wave_height_m": 1.5}'::jsonb);

COMMIT;
