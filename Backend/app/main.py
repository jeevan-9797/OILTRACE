from fastapi import FastAPI

from app.api.routes.spills import router as spills_router
from app.api.routes.attribution import router as attribution_router
from app.api.routes.vessels import router as vessels_router
from app.api.routes.drift import router as drift_router
app = FastAPI(
    title="OILTRACE API",
    description="AI-powered oil spill detection and vessel attribution system",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "project": "OILTRACE",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


app.include_router(spills_router) 
app.include_router(vessels_router)
app.include_router(attribution_router)
app.include_router(drift_router)