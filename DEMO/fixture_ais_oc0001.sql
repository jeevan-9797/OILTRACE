-- ==============================================================================
-- OILTRACE DEMO AIS FIXTURE: oc-0001.jpg (Cyprus / Levantine Basin)
-- ==============================================================================
--
-- IMPORTANT NOTICE:
-- This is a SYNTHETIC DEMO FIXTURE created specifically for hackathon demonstrations
-- using the Sentinel-1 SAR imagery file: evaluation/test_images/oc-0001.jpg.
--
-- Geographic Alignment:
-- Center of oc-0001.jpg: Latitude ~35.80° N, Longitude ~34.45° E (off Karpas Peninsula, Cyprus)
-- Derived from: Backend/data/image_geospatial_metadata.csv
--
-- Vessel Fleet Roles:
-- 1. MMSI 211234567 (VESSEL ALPHA): Primary suspect tanker passing ~0.18 km from slick
--    origin with a characteristic speed drop (13.8 kn -> 5.2 kn -> 12.4 kn).
-- 2. MMSI 355987654 (VESSEL BRAVO): Secondary candidate container ship cruising steady
--    ~14.6 km northwest at constant transit speed (16.5 kn).
-- 3. MMSI 412876543 (VESSEL CHARLIE): Weaker candidate bulk carrier passing ~28.0 km
--    south-southwest ~3 hours earlier.
-- 4. MMSI 538009876 (VESSEL DELTA): Deliberately distant coastal vessel located off
--    Limassol (~180 km away) to demonstrate P1 attribution eligibility gating exclusion.
--
-- Apply after 01_schema.sql and 02_seed_data.sql.
-- ==============================================================================

BEGIN;

-- 1. Ensure VESSEL DELTA exists in vessels table
INSERT INTO vessels (mmsi, name, imo_number, vessel_type, flag, length_m, width_m)
VALUES (538009876, 'VESSEL DELTA', 'IMO9518820', 'Tug / Offshore Support', 'Cyprus', 65.0, 15.0)
ON CONFLICT (mmsi) DO UPDATE SET
    name = EXCLUDED.name,
    vessel_type = EXCLUDED.vessel_type,
    flag = EXCLUDED.flag;

-- 2. Clean previous demo Cyprus positions if any exist (leaving Mumbai positions intact)
DELETE FROM vessel_positions
WHERE latitude BETWEEN 34.0 AND 37.0
  AND longitude BETWEEN 32.0 AND 36.0;

-- 3. Insert Geographically Aligned AIS Positions (Cyprus / oc-0001 corridor)
-- Note: Timestamps use NOW() - INTERVAL for live evaluation; explicit ISO strings
-- can also be substituted for fixed-date replays.
INSERT INTO vessel_positions (
    mmsi,
    timestamp,
    latitude,
    longitude,
    speed_knots,
    heading_deg,
    course_deg,
    navigation_status,
    source
) VALUES
    -- --------------------------------------------------------------------------
    -- VESSEL ALPHA (MMSI 211234567): Primary Suspect Track
    -- Speed drop from 13.8 to 5.2 knots within 180m of primary slick centroid
    -- --------------------------------------------------------------------------
    (211234567, NOW() - INTERVAL '90 minutes', 35.8150, 34.4350, 13.8, 135.0, 135.0, 'Under way using engine', 'sample_ais'),
    (211234567, NOW() - INTERVAL '60 minutes', 35.8060, 34.4500,  8.5, 135.0, 135.0, 'Under way using engine', 'sample_ais'),
    (211234567, NOW() - INTERVAL '30 minutes', 35.8010, 34.4580,  5.2, 135.0, 135.0, 'Under way using engine', 'sample_ais'), -- Discharge point (~180m from slick)
    (211234567, NOW() - INTERVAL '5 minutes',  35.7890, 34.4720, 12.4, 135.0, 135.0, 'Under way using engine', 'sample_ais'),

    -- --------------------------------------------------------------------------
    -- VESSEL BRAVO (MMSI 355987654): Secondary Candidate Track
    -- Constant cruise at ~16.5 knots, passing ~14.6 km north
    -- --------------------------------------------------------------------------
    (355987654, NOW() - INTERVAL '180 minutes', 35.9500, 34.4000, 16.5, 100.0, 100.0, 'Under way using engine', 'sample_ais'),
    (355987654, NOW() - INTERVAL '120 minutes', 35.9400, 34.4400, 16.5, 100.0, 100.0, 'Under way using engine', 'sample_ais'),
    (355987654, NOW() - INTERVAL '60 minutes',  35.9300, 34.4800, 16.5, 100.0, 100.0, 'Under way using engine', 'sample_ais'),

    -- --------------------------------------------------------------------------
    -- VESSEL CHARLIE (MMSI 412876543): Weaker Candidate Track
    -- Transiting ~28.0 km south-southwest at ~11.2 knots
    -- --------------------------------------------------------------------------
    (412876543, NOW() - INTERVAL '300 minutes', 35.5300, 34.3000, 11.5, 75.0, 75.0, 'Under way using engine', 'sample_ais'),
    (412876543, NOW() - INTERVAL '240 minutes', 35.5400, 34.3600, 11.4, 75.0, 75.0, 'Under way using engine', 'sample_ais'),
    (412876543, NOW() - INTERVAL '180 minutes', 35.5500, 34.4200, 11.2, 75.0, 75.0, 'Under way using engine', 'sample_ais'),

    -- --------------------------------------------------------------------------
    -- VESSEL DELTA (MMSI 538009876): Deliberately Ineligible Track
    -- Located near Limassol (~180 km away, > 50 km gate cutoff)
    -- --------------------------------------------------------------------------
    (538009876, NOW() - INTERVAL '120 minutes', 34.6500, 33.0500,  2.1,  0.0,  0.0, 'Under way using engine', 'sample_ais');

COMMIT;
