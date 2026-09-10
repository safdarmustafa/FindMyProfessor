import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routers import cv, departments, gmail, labs, matching, outreach, professors, profile, universities
from app.supabase_client import supabase

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Known production frontend origin, kept as a safety-net default alongside
# FRONTEND_URL so a misconfigured/missing Render env var can't silently
# break the deployed SPA. Not a secret — the same URL is already public in
# frontend/.env.production and OAuth redirect handling (app/routers/gmail.py).
_PRODUCTION_FRONTEND_ORIGIN = "https://findmyprofessor.online"
_DEV_FRONTEND_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def _cors_allowed_origins() -> list[str]:
    """
    Explicit origin allow-list instead of "*".

    "*" combined with allow_credentials=True lets ANY website's JavaScript
    make authenticated cross-origin calls against this API (e.g. probing
    endpoints with a guessed X-Profile-Id) and read the response — CORS is
    the browser's only barrier here since auth is header-based, not cookie
    based. Restrict it to our own frontend origins: the configured
    FRONTEND_URL, the known production origin, and local dev servers.
    """
    origins = {_PRODUCTION_FRONTEND_ORIGIN, *_DEV_FRONTEND_ORIGINS}
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if frontend_url:
        origins.add(frontend_url)
    extra = os.getenv("CORS_EXTRA_ORIGINS", "")
    for origin in extra.split(","):
        origin = origin.strip().rstrip("/")
        if origin:
            origins.add(origin)
    return sorted(origins)


app = FastAPI(
    title="FindMyProfessor API",
    description="Research discovery and outreach platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(universities.router)
app.include_router(departments.router)
app.include_router(labs.router)
app.include_router(professors.router)
app.include_router(cv.router)
app.include_router(profile.router)
app.include_router(matching.router)
app.include_router(outreach.router)
app.include_router(gmail.router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# API root — JSON only. The React SPA owns all product page routes.
# Legacy HTML pages (login, onboarding, matches, outreach/*, etc.) have been
# removed from FastAPI. The React frontend at localhost:5173 renders them.
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return JSONResponse({
        "message": "FindMyProfessor API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    })


@app.get("/health")
def health_check():
    try:
        supabase.table("universities").select("id").limit(1).execute()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc

    return {
        "status": "healthy",
        "database": "connected",
        "universities_table": "accessible",
    }
