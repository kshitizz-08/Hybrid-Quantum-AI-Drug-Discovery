"""
Tests for the Targets API.

Covers:
  - GET /api/targets returns list (includes seeded EGFR)
  - GET /api/targets/{id} returns a single target
  - GET /api/targets/{id} with invalid ID returns 404
  - POST /api/targets (authenticated) creates a target
  - POST /api/targets with duplicate ChEMBL ID returns 409
  - POST /api/targets without authentication returns 403
"""
import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_and_login, auth_headers


def test_list_targets_includes_egfr(client: TestClient):
    """GET /api/targets should include the seeded EGFR target."""
    resp = client.get("/api/targets")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    chembl_ids = [t["chembl_id"] for t in data]
    assert "CHEMBL203" in chembl_ids


def test_get_target_by_id(client: TestClient):
    """GET /api/targets/{id} returns the correct target."""
    # Get the list first to find the EGFR ID
    targets = client.get("/api/targets").json()
    egfr = next(t for t in targets if t["chembl_id"] == "CHEMBL203")
    egfr_id = egfr["id"]

    resp = client.get(f"/api/targets/{egfr_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chembl_id"] == "CHEMBL203"
    assert data["uniprot_id"] == "P00533"
    assert data["organism"] == "Homo sapiens"


def test_get_target_not_found(client: TestClient):
    """GET /api/targets/99999 returns 404."""
    resp = client.get("/api/targets/99999")
    assert resp.status_code == 404, resp.text


def test_create_target_authenticated(client: TestClient):
    """An authenticated user can create a new target."""
    token = register_and_login(client, {
        "email": "target_creator@test.com",
        "username": "targetcreator",
        "password": "password123",
    })
    resp = client.post("/api/targets", json={
        "name": "KRAS Proto-Oncogene",
        "chembl_id": "CHEMBL2093872",
        "uniprot_id": "P01116",
        "organism": "Homo sapiens",
        "target_type": "Single Protein",
        "description": "Test target for KRAS",
    }, headers=auth_headers(token))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["chembl_id"] == "CHEMBL2093872"
    assert data["name"] == "KRAS Proto-Oncogene"
    assert "id" in data


def test_create_target_duplicate_chembl_id(client: TestClient):
    """Creating a target with a duplicate ChEMBL ID returns 409."""
    token = register_and_login(client, {
        "email": "dup_target@test.com",
        "username": "duptarget",
        "password": "password123",
    })
    # Try creating EGFR again (already seeded)
    resp = client.post("/api/targets", json={
        "name": "EGFR Duplicate",
        "chembl_id": "CHEMBL203",
    }, headers=auth_headers(token))
    assert resp.status_code == 409, resp.text
    assert "already exists" in resp.json()["detail"].lower()


def test_create_target_unauthenticated(client: TestClient):
    """Creating a target without a token returns 403."""
    resp = client.post("/api/targets", json={
        "name": "No Auth Target",
        "chembl_id": "CHEMBL9999",
    })
    assert resp.status_code == 403, resp.text


def test_egfr_target_has_correct_fields(client: TestClient):
    """Verify the seeded EGFR target has the correct scientific metadata."""
    targets = client.get("/api/targets").json()
    egfr = next((t for t in targets if t["chembl_id"] == "CHEMBL203"), None)
    assert egfr is not None, "EGFR target must be seeded"
    assert "Epidermal Growth Factor Receptor" in egfr["name"]
    assert egfr["uniprot_id"] == "P00533"
    assert egfr["organism"] == "Homo sapiens"
    assert egfr["target_type"] == "Single Protein"
