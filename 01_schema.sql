-- ==============================================================================
-- OILTRACE DATABASE SCHEMA SPECIFICATION
-- Target: PostgreSQL / Supabase (PostgreSQL 14+)
-- Project: OILTRACE - Marine Oil Spill Detection & Explainable Vessel Attribution
-- Hackathon: Smart India Hackathon (SIH) Internal Hackathon
-- Author: Data / DB Lead
-- ==============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================================================
-- 2. DROP EXISTING TABLES (FOR CLEAN RE-RUNS IN DEV/TEST ENVIRONMENTS)
-- ==============================================================================
DROP TABLE IF EXISTS attribution_scores CASCADE;
DROP TABLE IF EXISTS spill_drift_points CASCADE;
DROP TABLE IF EXISTS vessel_positions CASCADE;
DROP TABLE IF EXISTS vessels CASCADE;
DROP TABLE IF EXISTS spills CASCADE;
DROP TABLE IF EXISTS satellite_images CASCADE;
DROP TABLE IF EXISTS weather_ocean_data CASCADE;

-- ==============================================================================
-- 3. HELPER FUNCTION & TRIGGER FOR updated_at TIMESTAMPS
-- ==============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- 4. TABLE: satellite_images (SHOULD - Metadata for satellite detection source)
-- ==============================================================================
CREATE TABLE satellite_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,                           -- e.g. 'Copernicus', 'Sentinel', 'Planet'
    satellite TEXT NOT NULL,                          -- e.g. 'Sentinel-1A', 'Sentinel-1B', 'Sentinel-2'
    sensor TEXT NOT NULL,                             -- e.g. 'SAR', 'C-SAR', 'EO'
    acquired_at TIMESTAMPTZ NOT NULL,                 -- Image acquisition time in UTC
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),     -- Scene center lat
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180), -- Scene center lon
    image_url TEXT,                                   -- Reference / URL to storage (e.g. Supabase Storage / S3)
    local_path TEXT,                                  -- Local cache/file path (avoids huge binaries in DB)
    metadata JSONB DEFAULT '{}'::jsonb,               -- Polarization (VV/VH), orbit, resolution, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE satellite_images IS 'Satellite scene metadata and references for oil spill detection traceability';

-- ==============================================================================
-- 5. TABLE: spills (MUST - Detected oil spill events & geometries)
-- ==============================================================================
CREATE TABLE spills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spill_code TEXT NOT NULL UNIQUE,                  -- Human-readable ID, e.g. 'SP-001'
    detected BOOLEAN NOT NULL DEFAULT TRUE,           -- Detection active flag
    confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0), -- 0.0000 to 1.0000
    area_km2 DOUBLE PRECISION NOT NULL CHECK (area_km2 >= 0),                          -- Spill slick area in km²
    centroid_latitude DOUBLE PRECISION NOT NULL CHECK (centroid_latitude BETWEEN -90 AND 90),
    centroid_longitude DOUBLE PRECISION NOT NULL CHECK (centroid_longitude BETWEEN -180 AND 180),
    polygon JSONB NOT NULL,                           -- GeoJSON Polygon / MultiPolygon structure
    detected_at TIMESTAMPTZ NOT NULL,                 -- Detection observation time in UTC
    estimated_origin_at TIMESTAMPTZ,                  -- Estimated spill discharge origin timestamp (hindcast)
    estimated_age_hours DOUBLE PRECISION CHECK (estimated_age_hours >= 0), -- Slick age in hours
    status TEXT NOT NULL DEFAULT 'detected' CHECK (status IN ('detected', 'investigating', 'resolved', 'closed')),
    source_image_id UUID REFERENCES satellite_images(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE spills IS 'Detected oil spill incidents, bounding geometries (GeoJSON), and detection metrics';

-- ==============================================================================
-- 6. TABLE: vessels (MUST - Master vessel identity information)
-- ==============================================================================
CREATE TABLE vessels (
    mmsi BIGINT PRIMARY KEY,                          -- 9-digit AIS Maritime Mobile Service Identity
    name TEXT,                                        -- Vessel name (e.g. 'VESSEL ALPHA')
    imo_number TEXT,                                  -- International Maritime Organization number (e.g. 'IMO9123456')
    vessel_type TEXT,                                 -- e.g. 'Tanker - Crude Oil', 'Cargo - Container'
    flag TEXT,                                        -- Flag state country (e.g. 'Panama', 'Liberia', 'India')
    length_m DOUBLE PRECISION CHECK (length_m >= 0),  -- Length overall in meters
    width_m DOUBLE PRECISION CHECK (width_m >= 0),    -- Beam/width in meters
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE vessels IS 'Master catalog of vessels tracked via AIS';

-- Auto-update updated_at timestamp on vessel modifications
CREATE TRIGGER trg_vessels_updated_at
BEFORE UPDATE ON vessels
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ==============================================================================
-- 7. TABLE: vessel_positions (MUST - Historical AIS trajectory & positions)
-- ==============================================================================
CREATE TABLE vessel_positions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mmsi BIGINT NOT NULL REFERENCES vessels(mmsi) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,                   -- AIS broadcast timestamp in UTC
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    speed_knots DOUBLE PRECISION CHECK (speed_knots >= 0),       -- Speed over ground (SOG)
    heading_deg DOUBLE PRECISION CHECK (heading_deg >= 0 AND heading_deg <= 360), -- Heading in degrees
    course_deg DOUBLE PRECISION CHECK (course_deg >= 0 AND course_deg <= 360),    -- Course over ground (COG)
    navigation_status TEXT,                           -- e.g. 'Under way using engine', 'At anchor'
    source TEXT NOT NULL DEFAULT 'sample_ais' CHECK (source IN ('sample_ais', 'real_ais', 'mock', 'satellite_ais'))
);

COMMENT ON TABLE vessel_positions IS 'Historical and real-time AIS positions for vessel track reconstruction';

-- ==============================================================================
-- 8. TABLE: spill_drift_points (MUST - Drift, hindcast & forecast trajectory)
-- ==============================================================================
CREATE TABLE spill_drift_points (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spill_id UUID NOT NULL REFERENCES spills(id) ON DELETE CASCADE,
    sequence_no INTEGER NOT NULL,                     -- Sequential trajectory index (1, 2, 3...)
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    timestamp TIMESTAMPTZ NOT NULL,                   -- Modeled or observed time in UTC
    path_type TEXT NOT NULL CHECK (path_type IN ('origin', 'historical', 'predicted')), -- origin / historical hindcast / predicted forecast
    model_source TEXT NOT NULL DEFAULT 'mock',        -- Drift model engine (e.g. 'ocean-current-v1', 'mock')
    confidence NUMERIC(5,4) CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

COMMENT ON TABLE spill_drift_points IS 'Slick trajectory drift points containing origin, hindcast history, and forecast path';

-- ==============================================================================
-- 9. TABLE: attribution_scores (MUST - Candidate vessel scoring & evidence)
-- ==============================================================================
CREATE TABLE attribution_scores (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spill_id UUID NOT NULL REFERENCES spills(id) ON DELETE CASCADE,
    mmsi BIGINT NOT NULL REFERENCES vessels(mmsi) ON DELETE CASCADE,
    spatial_score NUMERIC(5,2) NOT NULL CHECK (spatial_score BETWEEN 0.0 AND 100.0),       -- Proximity to slick path
    temporal_score NUMERIC(5,2) NOT NULL CHECK (temporal_score BETWEEN 0.0 AND 100.0),     -- Time-delta alignment
    trajectory_score NUMERIC(5,2) NOT NULL CHECK (trajectory_score BETWEEN 0.0 AND 100.0), -- Heading & route intersection
    behaviour_score NUMERIC(5,2) NOT NULL CHECK (behaviour_score BETWEEN 0.0 AND 100.0),   -- Speed drop, loitering, AIS off
    environment_score NUMERIC(5,2) CHECK (environment_score BETWEEN 0.0 AND 100.0),       -- Current/wind drift consistency
    final_score NUMERIC(5,2) NOT NULL CHECK (final_score BETWEEN 0.0 AND 100.0),           -- Composite attribution score
    rank INTEGER NOT NULL CHECK (rank >= 1),                                               -- 1 = Most probable polluter
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,                                           -- Explainable AI factors & metrics
    model_version TEXT NOT NULL DEFAULT 'v1.0.0',                                          -- Engine version
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_spill_vessel_attribution UNIQUE (spill_id, mmsi)
);

COMMENT ON TABLE attribution_scores IS 'Explainable multi-criteria attribution scoring rankings for candidate polluters';

-- ==============================================================================
-- 10. TABLE: weather_ocean_data (SHOULD - Environmental context & drift inputs)
-- ==============================================================================
CREATE TABLE weather_ocean_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,                   -- Observation/forecast time in UTC
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    wind_speed DOUBLE PRECISION CHECK (wind_speed >= 0),           -- Wind speed in m/s or knots
    wind_direction DOUBLE PRECISION CHECK (wind_direction BETWEEN 0 AND 360), -- Wind direction in degrees
    current_speed DOUBLE PRECISION CHECK (current_speed >= 0),     -- Ocean current speed in m/s or knots
    current_direction DOUBLE PRECISION CHECK (current_direction BETWEEN 0 AND 360), -- Ocean current direction in degrees
    source TEXT NOT NULL DEFAULT 'mock',              -- Data source (e.g. 'NOAA_GFS', 'Copernicus_CMEMS', 'mock')
    metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE weather_ocean_data IS 'Wind and ocean current environmental data for drift modeling verification';

-- ==============================================================================
-- 11. PERFORMANCE INDEXES (CRITICAL FOR FAST AIS & SPATIAL-TEMPORAL RETRIEVAL)
-- ==============================================================================

-- vessel_positions indexes
CREATE INDEX idx_vessel_positions_mmsi ON vessel_positions (mmsi);
CREATE INDEX idx_vessel_positions_timestamp ON vessel_positions (timestamp);
CREATE INDEX idx_vessel_positions_mmsi_timestamp ON vessel_positions (mmsi, timestamp DESC);
CREATE INDEX idx_vessel_positions_lat_lon ON vessel_positions (latitude, longitude);

-- spills indexes
CREATE INDEX idx_spills_spill_code ON spills (spill_code);
CREATE INDEX idx_spills_detected_at ON spills (detected_at DESC);
CREATE INDEX idx_spills_status ON spills (status);

-- attribution_scores indexes
CREATE INDEX idx_attribution_scores_spill_id ON attribution_scores (spill_id);
CREATE INDEX idx_attribution_scores_spill_rank ON attribution_scores (spill_id, rank ASC);
CREATE INDEX idx_attribution_scores_spill_final_score ON attribution_scores (spill_id, final_score DESC);
CREATE INDEX idx_attribution_scores_mmsi ON attribution_scores (mmsi);

-- spill_drift_points indexes
CREATE INDEX idx_spill_drift_points_spill_seq ON spill_drift_points (spill_id, sequence_no ASC);
CREATE INDEX idx_spill_drift_points_spill_timestamp ON spill_drift_points (spill_id, timestamp ASC);
CREATE INDEX idx_spill_drift_points_spill_path_type ON spill_drift_points (spill_id, path_type);

-- satellite_images indexes
CREATE INDEX idx_satellite_images_acquired_at ON satellite_images (acquired_at DESC);

-- weather_ocean_data indexes
CREATE INDEX idx_weather_ocean_data_timestamp ON weather_ocean_data (timestamp DESC);
CREATE INDEX idx_weather_ocean_data_lat_lon ON weather_ocean_data (latitude, longitude);

-- ==============================================================================
-- 12. SUPABASE ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================
-- Enable RLS on all tables for security compliance
ALTER TABLE satellite_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE spills ENABLE ROW LEVEL SECURITY;
ALTER TABLE vessels ENABLE ROW LEVEL SECURITY;
ALTER TABLE vessel_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE spill_drift_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE attribution_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_ocean_data ENABLE ROW LEVEL SECURITY;

-- Allow public / anon read access for Hackathon MVP frontend & backend queries
CREATE POLICY "Public Read satellite_images" ON satellite_images FOR SELECT USING (true);
CREATE POLICY "Public Read spills" ON spills FOR SELECT USING (true);
CREATE POLICY "Public Read vessels" ON vessels FOR SELECT USING (true);
CREATE POLICY "Public Read vessel_positions" ON vessel_positions FOR SELECT USING (true);
CREATE POLICY "Public Read spill_drift_points" ON spill_drift_points FOR SELECT USING (true);
CREATE POLICY "Public Read attribution_scores" ON attribution_scores FOR SELECT USING (true);
CREATE POLICY "Public Read weather_ocean_data" ON weather_ocean_data FOR SELECT USING (true);

-- Allow service_role full read/write access for backend FastAPI pipelines
CREATE POLICY "Service Role Full Access satellite_images" ON satellite_images FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access spills" ON spills FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access vessels" ON vessels FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access vessel_positions" ON vessel_positions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access spill_drift_points" ON spill_drift_points FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access attribution_scores" ON attribution_scores FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access weather_ocean_data" ON weather_ocean_data FOR ALL TO service_role USING (true) WITH CHECK (true);
