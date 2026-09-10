from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routers import cv, departments, gmail, labs, matching, outreach, professors, profile, universities
from app.supabase_client import supabase

STATIC_DIR = Path(__file__).resolve().parent / "static"


app = FastAPI(
    title="FindMyProfessor API",
    description="Research discovery and outreach platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
