from fastapi import FastAPI

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