from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.database import supabase

router = APIRouter(
    prefix="/api",
    tags=["Health"]
)


@router.get("/health")
def health_check():

    try:
        result = (
            supabase
            .table("spills")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )