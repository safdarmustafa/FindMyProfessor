import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

from app.main import app  # noqa: E402
from app.gmail import oauth as gmail_oauth  # noqa: E402


@pytest.fixture(autouse=True)
def _gmail_oauth_test_mode():
    """
    Gmail OAuth state is now persisted via Supabase (see
    migrations/20260910_gmail_oauth_states.sql) rather than an in-memory
    dict. Autouse so every test gets the in-memory test-mode override by
    default — without this, any test that happens to exercise
    /gmail/connect, /gmail/callback, or oauth.create_state/consume_state
    directly would silently attempt a real database call.
    """
    gmail_oauth.clear()
    yield
    gmail_oauth.disable_test_mode()


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
