from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import cv, departments, labs, matching, professors, profile, universities
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

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    return {
        "message": "FindMyProfessor API is running",
        "version": "0.1.0",
        "cv_onboarding": "/onboarding",
        "research_matches": "/matches",
    }


@app.get("/onboarding")
def cv_onboarding():
    page = STATIC_DIR / "cv_onboarding.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="Onboarding UI is not available.")
    return FileResponse(page)


@app.get("/matches")
def research_matches():
    page = STATIC_DIR / "matches.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="Research matches UI is not available.")
    return FileResponse(page)


@app.get("/matches/{professor_id}")
def research_match_professor(professor_id: UUID):
    page = STATIC_DIR / "professor_match.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="Professor match UI is not available.")
    return FileResponse(page)


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
