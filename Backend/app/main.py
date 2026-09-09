from contextlib import asynccontextmanager
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.spills import router as spills_router
from app.api.routes.attribution import router as attribution_router
from app.api.routes.vessels import router as vessels_router
from app.api.routes.drift import router as drift_router
from app.api.routes.health import router as health_router
from app.api.routes import spill_details
from app.services.ai.inference import get_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("oiltrace.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lightweight weights loading at startup without expensive prediction forward-passes
    try:
        get_model()
        logger.info("[STARTUP] YOLO model weights loaded into memory successfully.")
    except Exception as e:
        logger.warning("[STARTUP] YOLO model pre-loading deferred: %s", e)
    yield


app = FastAPI(
    title="OILTRACE API",
    description="AI-powered oil spill detection and vessel attribution system",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
def root():
    return {
        "project": "OILTRACE",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# API routers
app.include_router(spills_router)
app.include_router(vessels_router)
app.include_router(drift_router)
app.include_router(attribution_router)
app.include_router(health_router)
app.include_router(spill_details.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://oil-trace-two.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
