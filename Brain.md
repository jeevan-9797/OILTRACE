# OILTRACE — AI PROJECT BRAIN

> SIH Internal Hackathon Project
> Problem Statement: Marine Oil Spill Detection + Vessel Attribution
> Team: 6 CSE students
> Development time: 8 days
> Status: Prototype / Hackathon MVP

---

# 1. PROJECT GOAL

Build an intelligent automated system that:

1. Detects marine oil spills from satellite imagery.
2. Characterises the detected spill.
3. Calculates geometric properties such as area, centroid, perimeter and shape.
4. Estimates spill origin and time where feasible.
5. Uses oceanographic and meteorological data to hindcast/forecast slick movement.
6. Retrieves historical AIS vessel traffic around the estimated origin/time window.
7. Filters irrelevant vessels.
8. Scores potential responsible vessels using spatial, temporal, trajectory and behavioural evidence.
9. Displays the complete investigation through an interactive GIS dashboard.

IMPORTANT:
The system identifies the vessel with the highest attribution likelihood.
It does NOT claim legal certainty that a vessel caused the spill.

---

# 2. PROJECT NAME

OILTRACE

Full name:

AI-Powered Oil Spill Detection, Drift Prediction & Vessel Attribution System

Core idea:

Satellite + AI + Ocean Data + AIS + Attribution + GIS

---

# 3. CORE PIPELINE

Satellite Image
    ↓
Preprocessing
    ↓
Oil Spill Detection / Segmentation
    ↓
Spill Characterisation
    ↓
Estimated Spill Location + Time
    ↓
Wind / Ocean Current / Meteorological Data
    ↓
Slick Hindcast
    ↓
Estimated Origin
    ↓
AIS Historical Vessel Data
    ↓
Spatial Filtering
    ↓
Temporal Filtering
    ↓
Trajectory Analysis
    ↓
Behavioural Analysis
    ↓
Vessel Attribution Score
    ↓
Ranked Suspect Vessels
    ↓
GIS Dashboard

---

# 4. SYSTEM ARCHITECTURE

                    OILTRACE

             ┌───────────────────┐
             │ Satellite Imagery │
             │ Sentinel-1 / EO   │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ AI / ML Pipeline  │
             │ Oil Spill Model   │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ Spill Analysis    │
             │ Geometry / Stats  │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ Drift Engine      │
             │ Wind + Currents   │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ AIS Processing    │
             │ Vessel Tracking   │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ Attribution       │
             │ Scoring Engine    │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ FastAPI Backend   │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ PostgreSQL /      │
             │ Supabase          │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ React / Next.js   │
             │ GIS Dashboard     │
             └───────────────────┘

---

# 5. TEAM ROLES

## MEMBER 1 — FRONTEND LEAD

Technology:
- React / Next.js
- JavaScript / TypeScript
- Leaflet / Mapbox

Responsibilities:
- Main dashboard
- Interactive map
- Satellite overlay
- Spill polygon
- Spill centroid
- Vessel markers
- Vessel trajectories
- Drift path
- Attribution ranking
- Timeline
- Charts
- API integration

Consumes backend APIs.
Does not implement ML logic.

---

## MEMBER 2 — BACKEND / API LEAD

Technology:
- Python
- FastAPI
- Pydantic
- Supabase client
- PostgreSQL

Responsibilities:
- FastAPI application
- API routes
- Pydantic schemas
- Service layer
- AI integration
- AIS integration
- Database integration
- Error handling
- API validation
- Frontend/backend integration
- API documentation

Current owner:
Backend developer

IMPORTANT:
Do not put ML, AIS or database logic directly inside route files.

Preferred architecture:

Route
  ↓
Service
  ↓
ML / AIS / Database

---

## MEMBER 3 — AI / ML LEAD

Responsibilities:
- Oil spill detection
- Image preprocessing
- Segmentation / classification
- Look-alike rejection
- Spill confidence
- Spill geometry
- Model evaluation
- Inference pipeline

Expected model output:

{
  "detected": true,
  "confidence": 0.96,
  "area_km2": 12.4,
  "centroid": {
    "latitude": 12.345,
    "longitude": 74.567
  },
  "polygon": []
}

Do not expose model internals to frontend.

Backend calls ML service/function.

---

## MEMBER 4 — DATA / DATABASE LEAD

Technology:
- PostgreSQL
- Supabase
- SQL
- Python ETL

Responsibilities:
- Database schema
- Supabase setup
- Satellite metadata storage
- Spill records
- Vessel records
- AIS positions
- Drift paths
- Attribution scores
- Data cleaning
- ETL pipelines

Must coordinate database schema with Backend Lead.

Do not change API field names without agreement with Backend Lead.

---

## MEMBER 5 — UI/UX DESIGN LEAD

Responsibilities:
- UI/UX design
- Dashboard layout
- Map layout
- Cards
- Charts
- Colours
- Typography
- Loading states
- Error states
- Animations
- Presentation visuals

Works closely with Frontend Lead.

Not only responsible for PPT.

---

## MEMBER 6 — RESEARCH / PITCH / DOMAIN LEAD

Responsibilities:
- Oil spill domain research
- SAR research
- AIS research
- Oceanographic data research
- Dataset research
- Scientific validation
- Results interpretation
- Documentation
- PPT
- Demo script
- Pitch
- Impact analysis

Works closely with AI and Attribution.

---

# 6. TECHNOLOGY STACK

## Backend

Python
FastAPI
Pydantic
Uvicorn

## AI

Python
PyTorch / TensorFlow as required
OpenCV
Rasterio
NumPy
Pandas
GeoPandas
Scikit-learn as required

Use the simplest model that achieves good results within the hackathon deadline.

Do NOT over-engineer.

## Database

PostgreSQL
Supabase

## Frontend

Next.js / React
TypeScript if team is comfortable
Leaflet or Mapbox

## Geospatial

GeoPandas
Shapely
Rasterio
Leaflet / Mapbox

## Data

Sentinel-1 SAR
EO imagery where useful
AIS historical data
Wind data
Ocean current data
Meteorological data

---

# 7. REPOSITORY STRUCTURE

Root:

oiltrace/

├── brain.md
├── README.md
├── .gitignore
│
├── Backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       ├── spills.py
│   │   │       ├── vessels.py
│   │   │       ├── attribution.py
│   │   │       └── drift.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── spill.py
│   │   │   ├── vessel.py
│   │   │   └── attribution.py
│   │   │
│   │   ├── services/
│   │   │   ├── spill_service.py
│   │   │   ├── vessel_service.py
│   │   │   └── attribution_service.py
│   │   │
│   │   └── core/
│   │       ├── config.py
│   │       └── database.py
│   │
│   ├── requirements.txt
│   ├── .env
│   └── API_CONTRACT.md
│
├── ML/
│   ├── models/
│   ├── preprocessing/
│   ├── inference/
│   └── notebooks/
│
├── Data/
│   ├── raw/
│   ├── processed/
│   └── sample/
│
├── Frontend/
│
└── docs/

IMPORTANT:
Do not commit:
- venv/
- .env
- huge datasets
- model weights unless specifically required

---

# 8. BACKEND ARCHITECTURE

Frontend
    ↓
FastAPI Router
    ↓
Pydantic Validation
    ↓
Service Layer
    ↓
┌──────────────┬──────────────┬──────────────┐
│              │              │
ML Service   AIS Service   Database Service
│              │              │
└──────────────┴──────────────┴──────────────┘
                    ↓
                Response
                    ↓
                Frontend

IMPORTANT:
Routes should remain thin.

BAD:

route
  → 200 lines of ML/database/AIS code

GOOD:

route
  → service
  → result

---

# 9. API CONTRACT

## Health

GET /health

Response:

{
  "status": "healthy"
}

---

## Oil Spill Detection

POST /api/spills/detect

Input:
- Satellite image

Output:

{
  "spill_id": "SP-001",
  "detected": true,
  "confidence": 0.96,
  "area_km2": 12.4,
  "centroid": {
    "latitude": 12.345,
    "longitude": 74.567
  },
  "polygon": []
}

---

## Spill Details

GET /api/spills/{spill_id}

Returns:
- spill ID
- confidence
- area
- centroid
- polygon
- estimated time

---

## Spill Drift

GET /api/spills/{spill_id}/drift

Returns:

{
  "spill_id": "SP-001",
  "origin": {},
  "historical_path": [],
  "predicted_path": []
}

---

## Nearby Vessels

GET /api/spills/{spill_id}/vessels

Returns:

{
  "vessels": [
    {
      "mmsi": "123456789",
      "name": "VESSEL ALPHA",
      "latitude": 12.345,
      "longitude": 74.567,
      "speed": 12.4,
      "heading": 183,
      "timestamp": "..."
    }
  ]
}

---

## Vessel Attribution

GET /api/spills/{spill_id}/attribution

Returns:

{
  "spill_id": "SP-001",
  "candidates": [
    {
      "mmsi": "123456789",
      "vessel_name": "VESSEL ALPHA",
      "spatial_score": 94,
      "temporal_score": 96,
      "trajectory_score": 91,
      "behaviour_score": 83,
      "final_score": 91.4
    }
  ]
}

---

## Vessel Details

GET /api/vessels/{mmsi}

Returns:
- MMSI
- vessel name
- historical positions
- trajectory
- attribution information

---

# 10. ATTRIBUTION LOGIC

The system should NOT simply select the nearest vessel.

Candidate scoring should consider:

1. Spatial proximity
2. Temporal correlation
3. Trajectory intersection
4. Heading consistency
5. Vessel behaviour/anomaly
6. Environmental consistency where feasible

Initial prototype weighting:

Spatial proximity: 30%
Temporal correlation: 25%
Trajectory: 20%
Behaviour: 15%
Other/environmental evidence: 10%

Formula can be changed after validation.

Output:
ranked candidates.

Never claim legal certainty.

Use language:

"highest attribution likelihood"

NOT:

"proved culprit"

---

# 11. SPILL ANALYSIS

For each detected spill calculate where possible:

- area
- perimeter
- centroid
- bounding box
- orientation
- shape
- confidence
- timestamp
- estimated age

Optional:
- slick width
- slick length
- compactness
- estimated volume if scientifically justified

Do not invent scientific measurements.

---

# 12. DRIFT ENGINE

Goal:

Estimate where the spill came from and where it may move.

Inputs:
- detected spill location
- timestamp
- wind
- ocean current
- wave/oceanographic information where available

Outputs:

Historical / hindcast path:
t-6h
t-3h
t0

Predicted path:
t+3h
t+6h
t+12h

For hackathon MVP, a simplified drift model is acceptable if clearly documented.

Do not present a simplified model as a fully accurate physical ocean model.

---

# 13. AIS PROCESSING

AIS fields needed:

- MMSI
- vessel name
- timestamp
- latitude
- longitude
- speed
- heading
- course
- vessel type if available
- IMO if available

Pipeline:

Raw AIS
  ↓
Cleaning
  ↓
Invalid coordinate removal
  ↓
Timestamp normalization
  ↓
Spatial filtering
  ↓
Temporal filtering
  ↓
Trajectory reconstruction
  ↓
Candidate vessels

---

# 14. DATABASE CONCEPT

Expected tables:

spills
vessels
vessel_positions
spill_drift
attribution_scores

Possible relationships:

spill
  ↓
spill_drift

spill
  ↓
attribution_scores
  ↓
vessel

vessel
  ↓
vessel_positions

Actual schema is controlled by Data/DB Lead.

Backend must follow final agreed schema.

---

# 15. FRONTEND REQUIREMENTS

Dashboard should show:

## Main map

- Satellite image
- Spill polygon
- Spill centroid
- Historical drift
- Predicted drift
- Vessel positions
- Vessel trajectories
- Suspect vessel

## Spill panel

- Spill ID
- Confidence
- Area
- Estimated age/time
- Location

## Attribution panel

Top suspects:

1. Vessel A — 91.4%
2. Vessel B — 77.5%
3. Vessel C — 72.0%

Clicking a vessel should show evidence.

---

# 16. DEMO FLOW

The final demo should follow:

1. Select satellite image.
2. Run oil spill detection.
3. Display detected spill.
4. Show confidence and geometry.
5. Show estimated spill time.
6. Run drift reconstruction.
7. Show probable origin.
8. Load historical AIS traffic.
9. Filter irrelevant vessels.
10. Display candidate vessels.
11. Calculate attribution scores.
12. Rank suspects.
13. Select top vessel.
14. Show evidence for ranking.
15. Show future predicted drift.

The key WOW moment:

Satellite
→ Spill
→ Origin
→ Vessel traffic
→ Suspect ranking
→ Evidence

---

# 17. MVP PRIORITY

## MUST HAVE

- Oil spill detection
- Spill segmentation
- Spill geometry
- AIS vessel positions
- Vessel trajectory
- Spatial filtering
- Temporal filtering
- Vessel ranking
- Interactive map
- API integration

## SHOULD HAVE

- Hindcast
- Forecast
- Wind/current integration
- Behavioural anomaly
- Spill age estimation

## BONUS

- SAR + EO fusion
- Advanced physics model
- Uncertainty estimation
- Multiple simultaneous spills
- Automated report generation
- Real-time data

Do NOT work on BONUS until MUST HAVE is functional.

---

# 18. 8-DAY DEVELOPMENT PLAN

DAY 1
Backend foundation
- FastAPI
- Uvicorn
- Swagger
- Git branch
- API contract

DAY 2
Mock APIs
- spill
- vessels
- drift
- attribution

DAY 3
Database integration
- API error handling
- Supabase
- PostgreSQL
- database service

DAY 4
AI integration
- oil spill model
- inference API
- spill geometry

DAY 5
AIS integration
- AIS cleaning
- vessel trajectories
- spatial/temporal filtering

DAY 6
Attribution
- scoring
- ranking
- evidence
- drift integration

DAY 7
Full integration
- frontend
- backend
- AI
- AIS
- database
- testing

DAY 8
Freeze
- bug fixes
- demo
- PPT
- pitch
- final testing

---

# 19. GIT RULES

Branches:

main
backend
frontend
ml
data
design
research

Do not directly modify main.

Each person works on their branch.

Pull before starting work.

Commit small logical changes.

Commit message examples:

feat: add vessel API
fix: handle missing spill
feat: integrate attribution service
docs: update API contract

Use Pull Requests to merge into main.

---

# 20. AI CODING TOOL RULES

AI tools allowed:
- Cursor
- Antigravity
- ChatGPT
- Claude
- Gemini
- GitHub Copilot
- other coding assistants

AI should be used for:
- boilerplate
- debugging
- refactoring
- tests
- documentation
- code review
- implementation assistance

AI MUST NOT:
- rewrite the whole project unnecessarily
- change architecture without approval
- rename API fields randomly
- add unnecessary frameworks
- create duplicate functionality
- expose secrets
- modify unrelated files

Before major changes:
1. Read brain.md.
2. Inspect existing code.
3. Explain proposed change.
4. Modify only required files.
5. Do not break API contract.
6. Run tests.

---

# 21. BACKEND AI INSTRUCTION

When modifying Backend:

- Read brain.md first.
- Respect existing architecture.
- Keep FastAPI routes thin.
- Use Pydantic schemas.
- Put business logic in services.
- Keep database logic in database/service layer.
- Never hardcode secrets.
- Use .env.
- Don't change API contracts without discussion.
- Don't delete working mock APIs until replacement works.
- Don't add authentication unless required.
- Don't over-engineer.

---

# 22. CURRENT BACKEND STATUS

Completed:

[x] FastAPI setup
[x] Uvicorn
[x] Swagger
[x] /health
[x] Git backend branch
[x] .gitignore
[x] API_CONTRACT.md
[x] Mock spill API
[x] Mock vessel API
[x] Mock attribution API
[x] Mock drift API
[x] Proper 404 handling

Current task:

[ ] Database integration
[ ] Real AI integration
[ ] Real AIS integration
[ ] Attribution service
[ ] Full frontend integration

---

# 23. CURRENT MOCK DATA

Spill ID:

SP-001

Mock spill:

confidence = 0.96
area = 12.4 km²
centroid = 12.345, 74.567

Mock vessels:

123456789 — VESSEL ALPHA
234567890 — VESSEL BRAVO
345678901 — VESSEL CHARLIE

Mock attribution:

VESSEL ALPHA = 91.4%
VESSEL BRAVO = 77.5%
VESSEL CHARLIE = 72.0%

These are ONLY demo/mock values.

Never present mock values as real-world results.

---

# 24. IMPORTANT DEVELOPMENT PRINCIPLES

1. Working MVP > complicated architecture.
2. Demo reliability > extra features.
3. Never fake scientific accuracy.
4. Clearly label mock/demo data.
5. Keep modules independent.
6. Use stable API contracts.
7. Don't duplicate code.
8. Don't commit secrets.
9. Don't commit huge datasets.
10. Every feature must support the SIH problem statement.

---

# 25. FINAL SUCCESS CRITERIA

The project is successful if a judge can see:

Satellite image
→ AI detects oil
→ Spill geometry
→ Spill movement
→ Probable origin
→ AIS vessel traffic
→ Filtering
→ Suspect ranking
→ Explainable evidence
→ Interactive map

within a few minutes.

The system must look like one integrated product, not separate demos.
