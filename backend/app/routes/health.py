"""Health check endpoint."""

import time

from fastapi import APIRouter

router = APIRouter(tags=["System"])

_start_time = time.monotonic()


@router.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "resume-tailor",
        "version": "1.0.0",
        "uptime_seconds": round(time.monotonic() - _start_time),
    }
