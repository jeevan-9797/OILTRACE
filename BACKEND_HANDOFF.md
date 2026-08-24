# OILTRACE — Backend Hand-Off & Integration Guide

> **To:** Backend Lead & Development Team  
> **From:** Data / DB Lead  
> **Topic:** Database Hand-Off for FastAPI Endpoints & Supabase Integration  
> **Compliance:** OILTRACE Database Implementation Specification (SIH Hackathon)

---

## 1. Required Environment Variables

Add these variable names to your backend `.env` file (see [`.env.example`](file:///e:/Database/.env.example)):

```bash
DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
SUPABASE_URL="https://[PROJECT-REF].supabase.co"
SUPABASE_ANON_KEY="<anon-key-here>"
SUPABASE_SERVICE_ROLE_KEY="<service-role-key-here>"
```

> [!WARNING]
> Never commit `.env` files or credentials to Git repositories or public chats. Use secret managers or local `.env` only.

---

## 2. Table Names, Columns, & Data Types

### 1. `spills`
| Column | Type | Nullable | Default / Constraints | Notes / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary Key |
| `spill_code` | `text` | NO | `UNIQUE` | Human-readable ID (e.g. `'SP-001'`) |
| `detected` | `boolean` | NO | `TRUE` | Active detection status |
| `confidence` | `numeric(5,4)` | NO | `CHECK (0.0 <= conf <= 1.0)` | Model confidence (e.g. `0.9450`) |
| `area_km2` | `double precision`| NO | `CHECK (area >= 0)` | Spill slick area in km² |
| `centroid_latitude` | `double precision`| NO | `CHECK (-90 <= lat <= 90)` | Center latitude |
| `centroid_longitude`| `double precision`| NO | `CHECK (-180 <= lon <= 180)`| Center longitude |
| `polygon` | `jsonb` | NO | GeoJSON object | GeoJSON Polygon/MultiPolygon |
| `detected_at` | `timestamptz` | NO | None | Satellite observation time (UTC) |
| `estimated_origin_at` | `timestamptz` | YES | None | Hindcast estimated discharge time |
| `estimated_age_hours` | `double precision`| YES | `CHECK (age >= 0)` | Estimated age in hours |
| `status` | `text` | NO | `'detected'` | `'detected' \| 'investigating' \| 'resolved' \| 'closed'` |
| `source_image_id` | `uuid` | YES | `FK -> satellite_images(id)` | Foreign key to satellite image |
| `created_at` | `timestamptz` | NO | `now()` | Record creation timestamp |

---

### 2. `vessels`
| Column | Type | Nullable | Default / Constraints | Notes / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `mmsi` | `bigint` | NO | `PRIMARY KEY` | 9-digit AIS identity |
| `name` | `text` | YES | None | e.g. `'VESSEL ALPHA'` |
| `imo_number` | `text` | YES | None | e.g. `'IMO9245671'` |
| `vessel_type` | `text` | YES | None | e.g. `'Tanker - Crude Oil'` |
| `flag` | `text` | YES | None | e.g. `'Panama'` |
| `length_m` | `double precision`| YES | `CHECK (length >= 0)` | Length overall in meters |
| `width_m` | `double precision`| YES | `CHECK (width >= 0)` | Beam/width in meters |
| `created_at` | `timestamptz` | NO | `now()` | Timestamp |
| `updated_at` | `timestamptz` | NO | `now()` | Auto-updated via trigger |

---

### 3. `vessel_positions`
| Column | Type | Nullable | Default / Constraints | Notes / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `bigint` | NO | `GENERATED ALWAYS AS IDENTITY`| Primary Key |
| `mmsi` | `bigint` | NO | `FK -> vessels(mmsi) ON DELETE CASCADE`| Vessel reference |
| `timestamp` | `timestamptz` | NO | None | AIS broadcast timestamp (UTC) |
| `latitude` | `double precision`| NO | `CHECK (-90 <= lat <= 90)` | Latitude |
| `longitude` | `double precision`| NO | `CHECK (-180 <= lon <= 180)`| Longitude |
| `speed_knots` | `double precision`| YES | `CHECK (speed >= 0)` | Speed over ground (SOG) |
| `heading_deg` | `double precision`| YES | `CHECK (0 <= heading <= 360)` | Heading in degrees |
| `course_deg` | `double precision`| YES | `CHECK (0 <= course <= 360)` | Course over ground (COG) |
| `navigation_status` | `text` | YES | None | e.g. `'Under way using engine'` |
| `source` | `text` | NO | `'sample_ais'` | `'sample_ais' \| 'real_ais' \| 'mock'` |

---

### 4. `spill_drift_points`
| Column | Type | Nullable | Default / Constraints | Notes / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `bigint` | NO | `GENERATED ALWAYS AS IDENTITY`| Primary Key |
| `spill_id` | `uuid` | NO | `FK -> spills(id) ON DELETE CASCADE` | Spill reference |
| `sequence_no` | `integer` | NO | Sequential index | `1, 2, 3, ...` |
| `latitude` | `double precision`| NO | `CHECK (-90 <= lat <= 90)` | Latitude |
| `longitude` | `double precision`| NO | `CHECK (-180 <= lon <= 180)`| Longitude |
| `timestamp` | `timestamptz` | NO | None | Model / observed time (UTC) |
| `path_type` | `text` | NO | `CHECK (type IN ('origin', 'historical', 'predicted'))` | Path classification |
| `model_source`| `text` | NO | `'mock'` | e.g. `'ocean-current-v1'` |
| `confidence` | `numeric(5,4)` | YES | `CHECK (0.0 <= conf <= 1.0)` | Point confidence |

---

### 5. `attribution_scores`
| Column | Type | Nullable | Default / Constraints | Notes / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `bigint` | NO | `GENERATED ALWAYS AS IDENTITY`| Primary Key |
| `spill_id` | `uuid` | NO | `FK -> spills(id) ON DELETE CASCADE` | Spill reference |
| `mmsi` | `bigint` | NO | `FK -> vessels(mmsi) ON DELETE CASCADE`| Vessel reference |
| `spatial_score` | `numeric(5,2)` | NO | `CHECK (0 <= score <= 100)` | Proximity score (0-100) |
| `temporal_score`| `numeric(5,2)` | NO | `CHECK (0 <= score <= 100)` | Time alignment score (0-100) |
| `trajectory_score`| `numeric(5,2)`| NO | `CHECK (0 <= score <= 100)` | Course intersection score (0-100) |
| `behaviour_score`| `numeric(5,2)` | NO | `CHECK (0 <= score <= 100)` | Speed drop / loitering score (0-100) |
| `environment_score`| `numeric(5,2)`| YES | `CHECK (0 <= score <= 100)` | Drift & weather alignment (0-100) |
| `final_score` | `numeric(5,2)` | NO | `CHECK (0 <= score <= 100)` | Composite attribution score |
| `rank` | `integer` | NO | `CHECK (rank >= 1)` | `1 = Highest suspect` |
| `evidence` | `jsonb` | NO | `DEFAULT '{}'::jsonb` | Explainable AI factor breakdown |
| `model_version`| `text` | NO | `'v1.0.0'` | Engine model identifier |
| `created_at` | `timestamptz` | NO | `now()` | Creation timestamp |

---

### 6. `satellite_images` (Optional / Traceability)
| Column | Type | Nullable | Default / Constraints | Notes / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary Key |
| `provider` | `text` | NO | None | e.g. `'Copernicus / ESA'` |
| `satellite` | `text` | NO | None | e.g. `'Sentinel-1A'` |
| `sensor` | `text` | NO | None | e.g. `'SAR'` |
| `acquired_at` | `timestamptz` | NO | None | Acquisition time (UTC) |
| `latitude` | `double precision`| NO | `CHECK (-90 <= lat <= 90)` | Center lat |
| `longitude` | `double precision`| NO | `CHECK (-180 <= lon <= 180)`| Center lon |
| `image_url` | `text` | YES | None | Direct image URL |
| `local_path` | `text` | YES | None | Local path reference |
| `metadata` | `jsonb` | YES | `'{}'::jsonb` | Polarization, resolution, orbit |

---

### 7. `weather_ocean_data` (Optional / Reproducibility)
| Column | Type | Nullable | Default / Constraints | Notes / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `bigint` | NO | `GENERATED ALWAYS AS IDENTITY`| Primary Key |
| `timestamp` | `timestamptz` | NO | None | Grid time (UTC) |
| `latitude` | `double precision`| NO | `CHECK (-90 <= lat <= 90)` | Latitude |
| `longitude` | `double precision`| NO | `CHECK (-180 <= lon <= 180)`| Longitude |
| `wind_speed` | `double precision`| YES | `CHECK (speed >= 0)` | m/s or knots |
| `wind_direction`| `double precision`| YES | `CHECK (0 <= dir <= 360)` | Degrees |
| `current_speed` | `double precision`| YES | `CHECK (speed >= 0)` | m/s or knots |
| `current_direction`| `double precision`| YES | `CHECK (0 <= dir <= 360)` | Degrees |
| `source` | `text` | NO | `'mock'` | e.g. `'NOAA_GFS_CMEMS'` |
| `metadata` | `jsonb` | YES | `'{}'::jsonb` | Sea temperature, wave height |

---

## 3. Backend API Mapping to DB Queries

| Backend API Endpoint | Target DB Tables | Recommended SQL Query Pattern |
| :--- | :--- | :--- |
| **`GET /api/spills/{spill_id}`** | `spills`, `satellite_images` | `SELECT s.*, img.image_url, img.satellite FROM spills s LEFT JOIN satellite_images img ON s.source_image_id = img.id WHERE s.spill_code = :spill_id OR s.id = :spill_id` |
| **`GET /api/spills/{spill_id}/vessels`** | `vessels`, `vessel_positions`, `attribution_scores` | `SELECT v.*, lp.last_lat, lp.last_lon, lp.last_speed, lp.last_course FROM vessels v JOIN attribution_scores a ON v.mmsi = a.mmsi JOIN spills s ON a.spill_id = s.id LEFT JOIN (SELECT DISTINCT ON (mmsi) * FROM vessel_positions ORDER BY mmsi, timestamp DESC) lp ON v.mmsi = lp.mmsi WHERE s.spill_code = :spill_id ORDER BY a.rank ASC` |
| **`GET /api/spills/{spill_id}/drift`** | `spill_drift_points`, `spills` | `SELECT sdp.* FROM spill_drift_points sdp JOIN spills s ON sdp.spill_id = s.id WHERE s.spill_code = :spill_id ORDER BY sdp.sequence_no ASC` |
| **`GET /api/spills/{spill_id}/attribution`** | `attribution_scores`, `vessels`, `spills` | `SELECT a.rank, a.final_score, a.spatial_score, a.temporal_score, a.trajectory_score, a.behaviour_score, a.environment_score, a.evidence, v.mmsi, v.name, v.vessel_type, v.flag FROM attribution_scores a JOIN vessels v ON a.mmsi = v.mmsi JOIN spills s ON a.spill_id = s.id WHERE s.spill_code = :spill_id ORDER BY a.rank ASC` |
| **`GET /api/vessels/{mmsi}`** | `vessels`, `vessel_positions` | `SELECT * FROM vessels WHERE mmsi = :mmsi;` followed by `SELECT * FROM vessel_positions WHERE mmsi = :mmsi ORDER BY timestamp ASC;` |

---

## 4. Demo Data Summary (SP-001)

| Table | Count | Key Identifiers |
| :--- | :--- | :--- |
| `spills` | 1 | `SP-001` (ID: `f47ac10b-58cc-4372-a567-0e02b2c3d479`) |
| `satellite_images` | 1 | Sentinel-1A SAR scene (ID: `a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d`) |
| `vessels` | 3 | `VESSEL ALPHA` (211234567), `VESSEL BRAVO` (355987654), `VESSEL CHARLIE` (412876543) |
| `vessel_positions` | 19 | Full trajectory tracks showing speed drop for Alpha at 01:15 UTC |
| `spill_drift_points` | 7 | Sequence 1 (Origin @ 01:15) $\rightarrow$ Sequences 2-4 (Hindcast/Observed) $\rightarrow$ Sequences 5-7 (Forecast) |
| `attribution_scores` | 3 | Rank 1: Alpha (91.20), Rank 2: Bravo (42.00), Rank 3: Charlie (13.80) with full JSONB evidence |
| `weather_ocean_data` | 4 | Wind (12-14.5 kn NW) and Surface Currents (0.45-0.55 kn SE) |
