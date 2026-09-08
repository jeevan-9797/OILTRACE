-- OILTRACE demo AIS fixture for nc-0009-00-000009.jpg
-- Uses the existing vessel identities and vessel_positions schema.
-- Apply after the vessels table has been seeded.

BEGIN;

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
    -- VESSEL ALPHA: aligned primary candidate, slowing near the spill path.
    (211234567, '2026-09-08 12:23:45+00', 30.9400, 31.4000, 10.5, 135.0, 135.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-09-08 13:23:45+00', 30.8900, 31.4500,  9.6, 135.0, 135.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-09-08 14:23:45+00', 30.8400, 31.5000,  8.4, 135.0, 135.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-09-08 15:23:45+00', 30.8000, 31.5200,  5.5, 153.0, 153.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-09-08 16:23:45+00', 30.7850, 31.5250,  2.0, 162.0, 162.0, 'Under way using engine', 'sample_ais'),
    (211234567, '2026-09-08 17:23:45+00', 30.7850, 31.5250,  2.0,   0.0,   0.0, 'Under way using engine', 'sample_ais'),

    -- VESSEL BRAVO: temporally aligned but materially farther east.
    (355987654, '2026-09-08 14:23:45+00', 30.8400, 31.9000, 12.0, 105.0, 105.0, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-09-08 15:23:45+00', 30.8300, 31.9300, 12.0, 105.0, 105.0, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-09-08 16:23:45+00', 30.8200, 31.9600, 12.0, 105.0, 105.0, 'Under way using engine', 'sample_ais'),
    (355987654, '2026-09-08 17:23:45+00', 30.8100, 31.9900, 12.0, 105.0, 105.0, 'Under way using engine', 'sample_ais'),

    -- VESSEL CHARLIE: temporally aligned but well outside the spill area.
    (412876543, '2026-09-08 14:23:45+00', 31.3000, 32.3000, 11.5,  90.0,  90.0, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-09-08 15:23:45+00', 31.3000, 32.3400, 11.5,  90.0,  90.0, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-09-08 16:23:45+00', 31.3000, 32.3800, 11.5,  90.0,  90.0, 'Under way using engine', 'sample_ais'),
    (412876543, '2026-09-08 17:23:45+00', 31.3000, 32.4200, 11.5,  90.0,  90.0, 'Under way using engine', 'sample_ais');

COMMIT;
