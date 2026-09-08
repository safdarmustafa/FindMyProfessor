from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return repo_root() / "data"


def university_dir() -> Path:
    return data_dir() / "universities"


def department_dir() -> Path:
    return data_dir() / "departments"


def lab_dir() -> Path:
    return data_dir() / "labs"


def professor_dir() -> Path:
    return data_dir() / "professors"


def opportunity_dir() -> Path:
    return data_dir() / "opportunities"


def research_area_dir() -> Path:
    return data_dir() / "research_areas"


def manifest_path() -> Path:
    return university_dir() / "manifest.json"
