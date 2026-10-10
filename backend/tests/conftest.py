"""
pytest fixtures for Hybrid Quantum-AI Drug Discovery Platform tests.

Uses an in-memory SQLite database for each test session.
All tables are created fresh and torn down after each test session.
"""
import sys
from pathlib import Path

# Add project root to sys.path so 'ml' module can be found
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.services.target_service import seed_egfr_target

# ── In-memory SQLite test database ───────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_drug_discovery.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override the production DB dependency with the test DB."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create tables once before all tests, drop after."""
    Base.metadata.create_all(bind=test_engine)
    # Seed EGFR target
    db = TestingSessionLocal()
    try:
        seed_egfr_target(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def client(setup_test_database):
    """FastAPI test client with test DB override."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Reusable helpers ──────────────────────────────────────────

USER_A = {"email": "usera@test.com", "username": "usera", "password": "password123", "full_name": "User A"}
USER_B = {"email": "userb@test.com", "username": "userb", "password": "password123", "full_name": "User B"}


def register_and_login(client: TestClient, user_data: dict) -> str:
    """Register a user and return the JWT access token."""
    # Try register (might already exist from a prior test in session)
    client.post("/api/auth/register", json=user_data)
    resp = client.post("/api/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Return Authorization header dict from a JWT token."""
    return {"Authorization": f"Bearer {token}"}
