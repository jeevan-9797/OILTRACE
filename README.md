# OILTRACE

## AI-Powered Oil Spill Detection, Drift Prediction & Vessel Attribution

OILTRACE is an AI-driven oil-spill investigation platform that combines satellite imagery, computer vision, geospatial analysis, environmental data, and AIS vessel information to detect suspected oil spills, predict their movement, and rank vessels that may be associated with the spill.

> **Formal project title:** OILTRACE: An AI-Driven Platform for Satellite-Based Oil Spill Detection, Drift Forecasting and Responsible Vessel Attribution

---

## 1. Problem

Detecting an oil spill is only the first step. Investigators also need to determine:

- Where the spill occurred
- How large it is
- Where it may drift
- Which vessels were operating nearby
- Which vessel is the strongest candidate
- What evidence supports that ranking

OILTRACE brings these stages into one investigation workflow.

---

## 2. Solution

```text
Sentinel-1 SAR / DARTIS
          |
          v
   YOLO + PyTorch
   Spill Detection
          |
          v
 Georeferencing
 Area + Centroid
          |
          v
 Drift Prediction
 Wind / Ocean Data
          |
          v
    AIS Matching
          |
          v
Attribution Engine
          |
          v
Ranked Vessels
+ Evidence
          |
          v
React + TypeScript
Investigation Dashboard
```

---

## 3. Key Features

### AI Oil-Spill Detection
- Segmentation-based detection using Ultralytics YOLO and PyTorch.
- Returns detection confidence and spill-region information.

### Satellite Georeferencing
- Uses DARTIS image metadata.
- Calculates geographic spill centroid and affected area.

### Drift Prediction
- Generates historical and predicted spill movement paths.
- Uses available environmental/ocean information.

### AIS Vessel Investigation
- Retrieves vessel identities and AIS positions.
- Compares vessel movement with the spill and predicted drift.

### Explainable Attribution
Candidate vessels are ranked using:
- Spatial proximity
- Temporal proximity
- Trajectory proximity
- Vessel behaviour
- Environmental compatibility

### Investigation Dashboard
Displays:
- Spill polygon
- Centroid
- Historical and predicted drift
- Vessel markers
- Ranked suspect vessels
- Attribution evidence
- Detection time
- Confidence and spill details

---

## 4. Technical Architecture

```text
                  DATA SOURCES
        +-----------+-----------+-----------+
        |           |           |           |
   Sentinel-1    DARTIS        AIS      Environment
      SAR       Metadata     Vessels    Wind/Ocean
        |           |           |           |
        +-----------+-----------+-----------+
                    |
                    v
             +-------------+
             |   FastAPI   |
             |   Backend   |
             +-------------+
                    |
          +---------+---------+
          |                   |
          v                   v
    YOLO + PyTorch      Geospatial Logic
    Spill Detection     Centroid / Area
          |                   |
          +---------+---------+
                    |
                    v
             Drift Prediction
                    |
                    v
              AIS Correlation
                    |
                    v
             Attribution Engine
                    |
                    v
             Supabase / PostgreSQL
                    |
                    v
           React + TypeScript
                + D3.js
```

---

## 5. Technology Stack

| Area | Technology | Purpose |
|---|---|---|
| Frontend | React | Investigation dashboard |
| Language | TypeScript | Type-safe frontend |
| Visualization | D3.js | Investigation/data visualization |
| Backend | Python | Core processing |
| API | FastAPI | REST API |
| Validation | Pydantic | API validation |
| Server | Uvicorn | ASGI server |
| AI/ML | Ultralytics YOLO | Oil-spill segmentation/detection |
| ML Framework | PyTorch | Model inference |
| Database | Supabase / PostgreSQL | Application and investigation data |
| Satellite | Sentinel-1 SAR | Primary satellite imagery |
| Metadata | DARTIS | Image dimensions and geographic corners |
| Vessel Data | AIS | Vessel positions and identities |
| Environment | Weather/Ocean data | Drift and environmental analysis |

---

## 6. Workflow

### Step 1 — Upload
The investigator uploads a supported satellite image.

### Step 2 — Metadata Lookup
The backend identifies the image in the DARTIS metadata dataset and obtains its geographic corners and dimensions.

### Step 3 — AI Detection
The YOLO segmentation model detects suspected oil-spill regions.

### Step 4 — Georeferencing
Detected regions are converted into geographic information and used to calculate spill centroid and area.

### Step 5 — Drift Prediction
Environmental/ocean information is used to generate historical/predicted spill movement.

### Step 6 — AIS Correlation
Vessel positions are compared with the spill location and predicted trajectory.

### Step 7 — Attribution
Candidate vessels receive evidence-based component scores.

### Step 8 — Investigation Result
The frontend displays the ranked vessels and supporting evidence.

---

## 7. Attribution Scoring

The current weighted model is:

```text
Final Score =
    Spatial Proximity      × 25%
  + Temporal Proximity     × 20%
  + Trajectory Proximity   × 25%
  + Behaviour              × 10%
  + Environment            × 20%
```

This allows multiple independent signals to contribute to vessel ranking.

The score is an investigation confidence/ranking signal, **not legal proof of responsibility**.

---

## 8. API Overview

### Detect spill

```http
POST /api/spills/detect
```

Accepts an uploaded image and runs the detection pipeline.

Typical response fields include:

```json
{
  "image": "example.jpg",
  "satellite_image_id": "...",
  "image_width": 640,
  "image_height": 640,
  "detections": [],
  "spills_created": 0,
  "drift": [],
  "attribution": [],
  "detected_at": "..."
}
```

### Get attribution

```http
GET /api/spills/{spill_id}/attribution
```

Returns attribution information and candidate vessels for a spill.

Swagger documentation is available at `/docs` when the FastAPI backend is running.

---

## 9. Project Structure

```text
OILTRACE/
├── Backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   └── main.py
│   ├── data/
│   │   └── image_geospatial_metadata.csv
│   └── runs/
│       └── segment/
│           └── train-2/
│               └── weights/
│                   └── best.pt
├── src/
│   └── App.tsx
├── DEMO/
│   └── fixture_ais_nc0009.sql
├── package.json
└── README.md
```

---

## 10. Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Git
- Supabase/PostgreSQL project
- Required environment variables

### Backend

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### Frontend

From the project root:

```powershell
npm install
npm run dev
```

Open the development URL shown by Vite.

---

## 11. Environment Variables

Never commit secrets.

Typical backend configuration includes:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

Use the exact variable names required by the current backend configuration.

---

## 12. Demo AIS Fixture

The repository contains:

```text
DEMO/fixture_ais_nc0009.sql
```

The fixture provides geographically and temporally aligned AIS positions for the demonstration scenario.

It uses the existing demo vessel identities:

- **VESSEL ALPHA** — strongest candidate
- **VESSEL BRAVO** — secondary candidate
- **VESSEL CHARLIE** — lower-ranked candidate

The fixture is for controlled demonstration/testing and should only be inserted when the required vessel records exist.

---

## 13. Deployment

### Frontend
The frontend can be deployed to a web platform such as Vercel.

### Backend
The FastAPI backend can be deployed as a web service such as Render.

Verify during deployment:

1. Correct repository and branch
2. Correct backend root directory
3. Correct FastAPI start command
4. Required environment variables
5. Production CORS origin
6. YOLO model weights available to the service

---

## 14. Performance

The most computationally expensive stage of the current pipeline is YOLO inference on CPU.

The model is loaded once and reused by the backend process, but CPU inference can still take significant time.

Potential production optimizations include:

- Smaller inference size/model
- GPU acceleration
- Model quantization
- Asynchronous/background processing
- Caching repeated processing
- More powerful deployment resources

Accuracy should always be validated after performance changes.

---

## 15. Limitations

- AIS quality and availability affect vessel attribution.
- Attribution requires suitable spatial and temporal AIS coverage.
- The DARTIS CSV currently provides geographic image metadata but not per-image acquisition timestamps.
- Environmental data availability affects drift prediction.
- AI detections are probabilistic and require investigation/review.
- Attribution scores are ranking signals, not definitive proof of liability.
- CPU inference can introduce noticeable processing time.

---

## 16. Future Improvements

- Real-time AIS ingestion
- Larger historical vessel-track datasets
- GPU/model optimization
- Improved ocean/drift modelling
- Automated Sentinel-1 ingestion
- Multi-temporal satellite comparison
- Advanced vessel behaviour analysis
- Investigator case management
- Evidence/report export
- Better uncertainty estimation

---

## 17. Why OILTRACE?

Most oil-spill systems focus on detection.

OILTRACE connects the complete investigation chain:

```text
DETECT
  ↓
GEOREFERENCE
  ↓
PREDICT DRIFT
  ↓
MATCH AIS
  ↓
ATTRIBUTE VESSEL
  ↓
EXPLAIN EVIDENCE
```

This transforms satellite observations into an actionable, evidence-oriented vessel investigation workflow.

---

## 18. Team

**Project:** OILTRACE

**Formal Title:**  
OILTRACE: An AI-Driven Platform for Satellite-Based Oil Spill Detection, Drift Forecasting and Responsible Vessel Attribution

**Hackathon:** Smart India Hackathon

**Team:** Add team members and Team ID.

**Problem Statement ID:** Add official SIH Problem Statement ID.

---

## 19. Disclaimer

OILTRACE is a decision-support and investigation prototype. Detection and attribution outputs should be validated against authoritative satellite, AIS, environmental, and investigative evidence before use in enforcement, legal, or regulatory decisions.
