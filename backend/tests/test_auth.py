"""
Tests for authentication endpoints.

Covers:
  - Successful registration
  - Duplicate email registration (409)
  - Successful login
  - Invalid login (401)
  - /me endpoint with valid token
  - /me endpoint with invalid token (401)
"""
import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    """A new user can register successfully."""
    resp = client.post("/api/auth/register", json={
        "email": "newuser@test.com",
        "username": "newuser",
        "password": "securepassword123",
        "full_name": "New User"
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@test.com"
    assert data["user"]["username"] == "newuser"
    # Verify password is NOT returned
    assert "password" not in data["user"]
    assert "hashed_password" not in data["user"]


def test_register_duplicate_email(client: TestClient):
    """Registering with an existing email returns 409 Conflict."""
    # First registration
    client.post("/api/auth/register", json={
        "email": "duplicate@test.com",
        "username": "original_user",
        "password": "password123",
    })
    # Second registration with same email
    resp = client.post("/api/auth/register", json={
        "email": "duplicate@test.com",
        "username": "different_user",
        "password": "password123",
    })
    assert resp.status_code == 409, resp.text
    assert "already exists" in resp.json()["detail"].lower()


def test_register_duplicate_username(client: TestClient):
    """Registering with an existing username returns 409 Conflict."""
    client.post("/api/auth/register", json={
        "email": "uname1@test.com",
        "username": "taken_username",
        "password": "password123",
    })
    resp = client.post("/api/auth/register", json={
        "email": "uname2@test.com",
        "username": "taken_username",
        "password": "password123",
    })
    assert resp.status_code == 409, resp.text


def test_register_weak_password(client: TestClient):
    """Password shorter than 8 characters returns 422."""
    resp = client.post("/api/auth/register", json={
        "email": "weakpw@test.com",
        "username": "weakpwuser",
        "password": "short",
    })
    assert resp.status_code == 422, resp.text


def test_login_success(client: TestClient):
    """A registered user can log in successfully."""
    client.post("/api/auth/register", json={
        "email": "login_test@test.com",
        "username": "logintest",
        "password": "password123",
    })
    resp = client.post("/api/auth/login", json={
        "email": "login_test@test.com",
        "password": "password123",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_test@test.com"


def test_login_wrong_password(client: TestClient):
    """Wrong password returns 401 Unauthorized."""
    client.post("/api/auth/register", json={
        "email": "wrongpw@test.com",
        "username": "wrongpwuser",
        "password": "correctpassword",
    })
    resp = client.post("/api/auth/login", json={
        "email": "wrongpw@test.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401, resp.text


def test_login_nonexistent_user(client: TestClient):
    """Login with a non-existent email returns 401."""
    resp = client.post("/api/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "anypassword",
    })
    assert resp.status_code == 401, resp.text


def test_me_with_valid_token(client: TestClient):
    """GET /api/auth/me returns the authenticated user's profile."""
    # Register and get token
    resp = client.post("/api/auth/register", json={
        "email": "me_test@test.com",
        "username": "metest",
        "password": "password123",
    })
    token = resp.json()["access_token"]
    # Use token to call /me
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200, me_resp.text
    assert me_resp.json()["email"] == "me_test@test.com"


def test_me_without_token(client: TestClient):
    """GET /api/auth/me without token returns 403."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 403, resp.text


def test_me_with_invalid_token(client: TestClient):
    """GET /api/auth/me with a bogus token returns 401."""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer totally_invalid_token"})
    assert resp.status_code == 401, resp.text
