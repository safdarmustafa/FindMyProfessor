import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

from app.main import app  # noqa: E402


PROFILE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PROFESSOR_ID = "11111111-1111-1111-1111-111111111111"
DRAFT_ID = "draft-test-1"


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def auth_headers():
    return {"X-Profile-Id": PROFILE_ID}


@pytest.fixture
def ids():
    return {
        "profile_id": PROFILE_ID,
        "professor_id": PROFESSOR_ID,
        "draft_id": DRAFT_ID,
        "university_id": str(uuid4()),
        "department_id": str(uuid4()),
        "lab_id": str(uuid4()),
        "area_id": str(uuid4()),
    }
