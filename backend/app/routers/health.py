"""Health check router — GET /api/health"""
import platform
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, check_db_connection
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])
settings = get_settings()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Platform health check endpoint.
    Returns application status, version, and database connectivity.
    """
    db_connected = check_db_connection()

    return {
        "status": "ok" if db_connected else "degraded",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": {
            "connected": db_connected,
            "url_type": settings.database_url.split("://")[0],
        },
        "python_version": platform.python_version(),
        "debug_mode": settings.debug,
    }


@router.get("/")
def root():
    """Root endpoint — confirms backend is running."""
    return {
        "message": "Hybrid Quantum-AI Drug Discovery Platform — Backend API",
        "docs": "/docs",
        "health": "/api/health",
        "version": settings.app_version,
    }
