-- ==============================================================================
-- OILTRACE — ALL-IN-ONE SUPABASE / POSTGRESQL SETUP SCRIPT
-- Paste and run this script directly in the Supabase SQL Editor.
-- It will:
--   1. Enable UUID extensions
--   2. Drop existing tables cleanly
--   3. Create all 7 tables with check constraints and foreign keys
--   4. Create performance indexes
--   5. Configure updated_at triggers
--   6. Enable Row Level Security (RLS) policies
--   7. Insert complete realistic seed data for SP-001 & candidate vessels
-- ==============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. DROP TABLES
DROP TABLE IF EXISTS attribution_scores CASCADE;
DROP TABLE IF EXISTS spill_drift_points CASCADE;
DROP TABLE IF EXISTS vessel_positions CASCADE;
DROP TABLE IF EXISTS vessels CASCADE;
DROP TABLE IF EXISTS spills CASCADE;
DROP TABLE IF EXISTS satellite_images CASCADE;
DROP TABLE IF EXISTS weather_ocean_data CASCADE;

-- 3. TRIGGER FUNCTION
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. TABLES
CREATE TABLE satellite_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    satellite TEXT NOT NULL,
    sensor TEXT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    image_url TEXT,
    local_path TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE spills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spill_code TEXT NOT NULL UNIQUE,
    detected BOOLEAN NOT NULL DEFAULT TRUE,
    confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    area_km2 DOUBLE PRECISION NOT NULL CHECK (area_km2 >= 0),
    centroid_latitude DOUBLE PRECISION NOT NULL CHECK (centroid_latitude BETWEEN -90 AND 90),
    centroid_longitude DOUBLE PRECISION NOT NULL CHECK (centroid_longitude BETWEEN -180 AND 180),
    polygon JSONB NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    estimated_origin_at TIMESTAMPTZ,
    estimated_age_hours DOUBLE PRECISION CHECK (estimated_age_hours >= 0),
    status TEXT NOT NULL DEFAULT 'detected' CHECK (status IN ('detected', 'investigating', 'resolved', 'closed')),
    source_image_id UUID REFERENCES satellite_images(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE vessels (
    mmsi BIGINT PRIMARY KEY,
    name TEXT,
    imo_number TEXT,
    vessel_type TEXT,
    flag TEXT,
    length_m DOUBLE PRECISION CHECK (length_m >= 0),
    width_m DOUBLE PRECISION CHECK (width_m >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_vessels_updated_at
BEFORE UPDATE ON vessels
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE vessel_positions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mmsi BIGINT NOT NULL REFERENCES vessels(mmsi) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    speed_knots DOUBLE PRECISION CHECK (speed_knots >= 0),
    heading_deg DOUBLE PRECISION CHECK (heading_deg >= 0 AND heading_deg <= 360),
    course_deg DOUBLE PRECISION CHECK (course_deg >= 0 AND course_deg <= 360),
    navigation_status TEXT,
    source TEXT NOT NULL DEFAULT 'sample_ais' CHECK (source IN ('sample_ais', 'real_ais', 'mock', 'satellite_ais'))
);

CREATE TABLE spill_drift_points (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spill_id UUID NOT NULL REFERENCES spills(id) ON DELETE CASCADE,
    sequence_no INTEGER NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    timestamp TIMESTAMPTZ NOT NULL,
    path_type TEXT NOT NULL CHECK (path_type IN ('origin', 'historical', 'predicted')),
    model_source TEXT NOT NULL DEFAULT 'mock',
    confidence NUMERIC(5,4) CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

CREATE TABLE attribution_scores (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spill_id UUID NOT NULL REFERENCES spills(id) ON DELETE CASCADE,
    mmsi BIGINT NOT NULL REFERENCES vessels(mmsi) ON DELETE CASCADE,
    spatial_score NUMERIC(5,2) NOT NULL CHECK (spatial_score BETWEEN 0.0 AND 100.0),
    temporal_score NUMERIC(5,2) NOT NULL CHECK (temporal_score BETWEEN 0.0 AND 100.0),
    trajectory_score NUMERIC(5,2) NOT NULL CHECK (trajectory_score BETWEEN 0.0 AND 100.0),
    behaviour_score NUMERIC(5,2) NOT NULL CHECK (behaviour_score BETWEEN 0.0 AND 100.0),
    environment_score NUMERIC(5,2) CHECK (environment_score BETWEEN 0.0 AND 100.0),
    final_score NUMERIC(5,2) NOT NULL CHECK (final_score BETWEEN 0.0 AND 100.0),
    rank INTEGER NOT NULL CHECK (rank >= 1),
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version TEXT NOT NULL DEFAULT 'v1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_spill_vessel_attribution UNIQUE (spill_id, mmsi)
);

CREATE TABLE weather_ocean_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    wind_speed DOUBLE PRECISION CHECK (wind_speed >= 0),
    wind_direction DOUBLE PRECISION CHECK (wind_direction BETWEEN 0 AND 360),
    current_speed DOUBLE PRECISION CHECK (current_speed >= 0),
    current_direction DOUBLE PRECISION CHECK (current_direction BETWEEN 0 AND 360),
    source TEXT NOT NULL DEFAULT 'mock',
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 5. INDEXES
CREATE INDEX idx_vessel_positions_mmsi ON vessel_positions (mmsi);
CREATE INDEX idx_vessel_positions_timestamp ON vessel_positions (timestamp);
CREATE INDEX idx_vessel_positions_mmsi_timestamp ON vessel_positions (mmsi, timestamp DESC);
CREATE INDEX idx_vessel_positions_lat_lon ON vessel_positions (latitude, longitude);

CREATE INDEX idx_spills_spill_code ON spills (spill_code);
CREATE INDEX idx_spills_detected_at ON spills (detected_at DESC);
CREATE INDEX idx_spills_status ON spills (status);

CREATE INDEX idx_attribution_scores_spill_id ON attribution_scores (spill_id);
CREATE INDEX idx_attribution_scores_spill_rank ON attribution_scores (spill_id, rank ASC);
CREATE INDEX idx_attribution_scores_spill_final_score ON attribution_scores (spill_id, final_score DESC);
CREATE INDEX idx_attribution_scores_mmsi ON attribution_scores (mmsi);

CREATE INDEX idx_spill_drift_points_spill_seq ON spill_drift_points (spill_id, sequence_no ASC);
CREATE INDEX idx_spill_drift_points_spill_timestamp ON spill_drift_points (spill_id, timestamp ASC);
CREATE INDEX idx_spill_drift_points_spill_path_type ON spill_drift_points (spill_id, path_type);

CREATE INDEX idx_satellite_images_acquired_at ON satellite_images (acquired_at DESC);
CREATE INDEX idx_weather_ocean_data_timestamp ON weather_ocean_data (timestamp DESC);
CREATE INDEX idx_weather_ocean_data_lat_lon ON weather_ocean_data (latitude, longitude);

-- 6. ROW LEVEL SECURITY (RLS) POLICIES
ALTER TABLE satellite_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE spills ENABLE ROW LEVEL SECURITY;
ALTER TABLE vessels ENABLE ROW LEVEL SECURITY;
ALTER TABLE vessel_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE spill_drift_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE attribution_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_ocean_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public Read satellite_images" ON satellite_images FOR SELECT USING (true);
CREATE POLICY "Public Read spills" ON spills FOR SELECT USING (true);
CREATE POLICY "Public Read vessels" ON vessels FOR SELECT USING (true);
CREATE POLICY "Public Read vessel_positions" ON vessel_positions FOR SELECT USING (true);
CREATE POLICY "Public Read spill_drift_points" ON spill_drift_points FOR SELECT USING (true);
CREATE POLICY "Public Read attribution_scores" ON attribution_scores FOR SELECT USING (true);
CREATE POLICY "Public Read weather_ocean_data" ON weather_ocean_data FOR SELECT USING (true);

CREATE POLICY "Service Role Full Access satellite_images" ON satellite_images FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access spills" ON spills FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access vessels" ON vessels FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access vessel_positions" ON vessel_positions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access spill_drift_points" ON spill_drift_points FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access attribution_scores" ON attribution_scores FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access weather_ocean_data" ON weather_ocean_data FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 7. SEED DATA
-- Satellite Image
INSERT INTO satellite_images (
    id, provider, satellite, sensor, acquired_at, latitude, longitude, image_url, local_path, metadata
) VALUES (
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d',
    'Copernicus / ESA', 'Sentinel-1A', 'SAR (C-Band Synthetic Aperture Radar)',
    '2026-08-24 06:15:00+00', 18.9200, 72.7500,
    'https://storage.oiltrace.ai/satellite-scenes/20260824_S1A_IW_GRDH_SP001.tif',
    '/data/satellite_cache/20260824_S1A_IW_GRDH_SP001.png',
    jsonb_build_object('polarization', 'VV+VH', 'orbit_direction', 'DESCENDING', 'relative_orbit', 142, 'resolution_m', 10.0, 'swath_width_km', 250, 'incidence_angle_deg', 37.4, 'cloud_cover_pct', 0.0)
);

-- Spill SP-001
INSERT INTO spills (
    id, spill_code, detected, confidence, area_km2, centroid_latitude, centroid_longitude,
    polygon, detected_at, estimated_origin_at, estimated_age_hours, status, source_image_id
) VALUES (
    'f47ac10b-58cc-4372-a567-0e02b2c3d479', 'SP-001', TRUE, 0.9450, 14.85, 18.9200, 72.7500,
    jsonb_build_object('type', 'Polygon', 'coordinates', jsonb_build_array(jsonb_build_array(
        jsonb_build_array(72.7310, 18.9320),
        jsonb_build_array(72.7640, 18.9280),
        jsonb_build_array(72.7720, 18.9110),
        jsonb_build_array(72.7550, 18.9040),
        jsonb_build_array(72.7380, 18.9150),
        jsonb_build_array(72.7310, 18.9320)
    ))),
    '2026-08-24 06:30:00+00', '2026-08-24 01:15:00+00', 5.25, 'investigating', 'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d'
);

-- Vessels
INSERT INTO vessels (mmsi, name, imo_number, vessel_type, flag, length_m, width_m) VALUES
    (211234567, 'VESSEL ALPHA', 'IMO9245671', 'Tanker - Crude Oil', 'Panama', 244.5, 42.0),
    (355987654, 'VESSEL BRAVO', 'IMO9432190', 'Cargo - Container', 'Liberia', 182.0, 28.5),
    (412876543, 'VESSEL CHARLIE', 'IMO9318724', 'Bulk Carrier', 'Marshall Islands', 225.0, 32.2);

-- AIS Positions
INSERT INTO vessel_positions (mmsi, timestamp, latitude, longitude, speed_knots, heading_deg, course_deg, navigation_status, source) VALUES
    (211234567, '2026-08-24 00:00:00+00', 19.0450, 72.6320, 14.4, 155.0, 154.5, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 00:30:00+00', 19.0180, 72.6550, 14.1, 153.0, 153.2, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 01:00:00+00', 18.9920, 72.6780, 9.5,  152.0, 151.8, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 01:15:00+00', 18.9850, 72.6820, 5.8,  150.0, 150.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 01:30:00+00', 18.9770, 72.6880, 6.2,  149.0, 149.5, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 02:00:00+00', 18.9520, 72.7050, 11.2, 148.0, 148.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 03:00:00+00', 18.8950, 72.7480, 14.0, 147.0, 147.2, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 04:00:00+00', 18.8350, 72.7910, 14.3, 146.0, 146.5, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 05:00:00+00', 18.7750, 72.8340, 14.2, 146.0, 146.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-08-24 06:00:00+00', 18.7150, 72.8770, 14.5, 145.0, 145.2, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-23 23:30:00+00', 19.0800, 72.7500, 16.8, 175.0, 174.5, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-24 00:15:00+00', 19.0100, 72.7550, 16.6, 175.0, 175.0, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-24 01:00:00+00', 18.9400, 72.7600, 16.5, 174.0, 174.2, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-24 01:45:00+00', 18.8700, 72.7650, 16.7, 175.0, 175.1, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-08-24 02:30:00+00', 18.8000, 72.7700, 16.5, 175.0, 174.8, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-08-24 02:30:00+00', 19.0500, 72.5200, 12.0, 160.0, 160.0, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-08-24 03:30:00+00', 18.9700, 72.5550, 12.2, 160.0, 159.8, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-08-24 04:30:00+00', 18.8900, 72.5900, 12.1, 161.0, 160.5, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-08-24 05:30:00+00', 18.8100, 72.6250, 11.9, 160.0, 160.2, 'Under way using engine', 'sample_ais');

-- Spill Drift Points
INSERT INTO spill_drift_points (spill_id, sequence_no, latitude, longitude, timestamp, path_type, model_source, confidence) VALUES
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 1, 18.9850, 72.6820, '2026-08-24 01:15:00+00', 'origin',     'ocean-current-v1', 0.9100),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 2, 18.9620, 72.7050, '2026-08-24 03:00:00+00', 'historical', 'ocean-current-v1', 0.9250),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 3, 18.9380, 72.7310, '2026-08-24 05:00:00+00', 'historical', 'ocean-current-v1', 0.9400),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 4, 18.9200, 72.7500, '2026-08-24 06:30:00+00', 'historical', 'sentinel-1-sar',  0.9450),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 5, 18.8980, 72.7750, '2026-08-24 09:30:00+00', 'predicted',  'ocean-current-v1', 0.8800),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 6, 18.8740, 72.8020, '2026-08-24 12:30:00+00', 'predicted',  'ocean-current-v1', 0.8200),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 7, 18.8350, 72.8450, '2026-08-24 18:30:00+00', 'predicted',  'ocean-current-v1', 0.7400);

-- Attribution Scores
INSERT INTO attribution_scores (
    spill_id, mmsi, spatial_score, temporal_score, trajectory_score,
    behaviour_score, environment_score, final_score, rank, evidence, model_version
) VALUES
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 211234567, 96.50, 93.00, 91.00, 86.50, 88.00, 91.20, 1,
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
     ), 'oiltrace-attribution-v1.0'),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 355987654, 44.00, 52.00, 41.00, 28.00, 45.00, 42.00, 2,
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
     ), 'oiltrace-attribution-v1.0'),
    ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 412876543, 15.00, 18.00, 12.00, 10.00, 14.00, 13.80, 3,
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
     ), 'oiltrace-attribution-v1.0');

-- Weather & Ocean Data
INSERT INTO weather_ocean_data (timestamp, latitude, longitude, wind_speed, wind_direction, current_speed, current_direction, source, metadata) VALUES
    ('2026-08-24 01:00:00+00', 18.9500, 72.7000, 12.4, 310.0, 0.45, 140.0, 'NOAA_GFS_CMEMS', '{"sea_temp_c": 28.5, "wave_height_m": 1.2}'::jsonb),
    ('2026-08-24 03:00:00+00', 18.9500, 72.7000, 13.1, 315.0, 0.48, 142.0, 'NOAA_GFS_CMEMS', '{"sea_temp_c": 28.4, "wave_height_m": 1.3}'::jsonb),
    ('2026-08-24 05:00:00+00', 18.9500, 72.7000, 14.0, 318.0, 0.52, 145.0, 'NOAA_GFS_CMEMS', '{"sea_temp_c": 28.3, "wave_height_m": 1.4}'::jsonb),
    ('2026-08-24 06:30:00+00', 18.9200, 72.7500, 14.5, 320.0, 0.55, 146.0, 'NOAA_GFS_CMEMS', '{"sea_temp_c": 28.2, "wave_height_m": 1.5}'::jsonb);
