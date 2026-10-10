"""
Tests for Experiment API endpoints.

Covers:
  - Create experiment (authenticated)
  - Create experiment with target
  - List experiments (user sees only own)
  - Get single experiment (own = 200, other = 404)
  - Update experiment
  - Delete experiment
  - User isolation: User A cannot access User B's experiment
  - Dashboard stats return real counts
  - Unauthenticated access returns 403
"""
import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_and_login, auth_headers, USER_A, USER_B


def test_create_experiment_success(client: TestClient):
    """An authenticated user can create an experiment."""
    token = register_and_login(client, USER_A)
    resp = client.post("/api/experiments", json={
        "name": "EGFR Bioactivity Screening",
        "description": "Initial screening of EGFR bioactivity dataset",
    }, headers=auth_headers(token))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "EGFR Bioactivity Screening"
    assert data["status"] == "PENDING"
    assert data["preprocess_status"] == "PENDING"
    assert data["screen_status"] == "PENDING"
    assert data["quantum_status"] == "PENDING"
    assert data["docking_status"] == "PENDING"
    assert "id" in data
    assert "created_at" in data


def test_create_experiment_with_target(client: TestClient):
    """Creating an experiment with a valid target_id links it correctly."""
    token = register_and_login(client, USER_A)
    # Get EGFR target ID
    targets = client.get("/api/targets").json()
    egfr_id = next(t["id"] for t in targets if t["chembl_id"] == "CHEMBL203")

    resp = client.post("/api/experiments", json={
        "name": "EGFR Target Linked Experiment",
        "target_id": egfr_id,
    }, headers=auth_headers(token))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["target_id"] == egfr_id
    assert data["target"]["chembl_id"] == "CHEMBL203"


def test_create_experiment_with_invalid_target(client: TestClient):
    """Creating an experiment with a non-existent target_id returns 404."""
    token = register_and_login(client, USER_A)
    resp = client.post("/api/experiments", json={
        "name": "Bad Target Experiment",
        "target_id": 99999,
    }, headers=auth_headers(token))
    assert resp.status_code == 404, resp.text


def test_create_experiment_name_too_short(client: TestClient):
    """Experiment name shorter than 3 characters returns 422."""
    token = register_and_login(client, USER_A)
    resp = client.post("/api/experiments", json={
        "name": "AB",
    }, headers=auth_headers(token))
    assert resp.status_code == 422, resp.text


def test_list_experiments_returns_only_own(client: TestClient):
    """A user can only see their own experiments."""
    token_a = register_and_login(client, USER_A)
    token_b = register_and_login(client, USER_B)

    # User B creates an experiment
    client.post("/api/experiments", json={
        "name": "User B Private Experiment"
    }, headers=auth_headers(token_b))

    # User A lists experiments — should not see User B's experiment
    resp_a = client.get("/api/experiments", headers=auth_headers(token_a))
    assert resp_a.status_code == 200, resp_a.text
    names = [e["name"] for e in resp_a.json()]
    assert "User B Private Experiment" not in names


def test_get_own_experiment(client: TestClient):
    """A user can retrieve their own experiment by ID."""
    token = register_and_login(client, USER_A)
    create_resp = client.post("/api/experiments", json={
        "name": "Get Own Experiment Test"
    }, headers=auth_headers(token))
    exp_id = create_resp.json()["id"]

    resp = client.get(f"/api/experiments/{exp_id}", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == exp_id


def test_user_isolation_get(client: TestClient):
    """User A cannot access User B's experiment — returns 404."""
    token_a = register_and_login(client, USER_A)
    token_b = register_and_login(client, USER_B)

    # User B creates an experiment
    create_resp = client.post("/api/experiments", json={
        "name": "User B Secret Experiment"
    }, headers=auth_headers(token_b))
    exp_id = create_resp.json()["id"]

    # User A tries to access it — should get 404 (not 403, to avoid info leak)
    resp = client.get(f"/api/experiments/{exp_id}", headers=auth_headers(token_a))
    assert resp.status_code == 404, resp.text


def test_update_experiment(client: TestClient):
    """A user can update their own experiment's name and description."""
    token = register_and_login(client, USER_A)
    create_resp = client.post("/api/experiments", json={
        "name": "Original Name"
    }, headers=auth_headers(token))
    exp_id = create_resp.json()["id"]

    resp = client.patch(f"/api/experiments/{exp_id}", json={
        "name": "Updated Name",
        "description": "Updated description"
    }, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"


def test_update_experiment_user_isolation(client: TestClient):
    """User A cannot update User B's experiment."""
    token_a = register_and_login(client, USER_A)
    token_b = register_and_login(client, USER_B)

    create_resp = client.post("/api/experiments", json={
        "name": "User B's Experiment to Protect"
    }, headers=auth_headers(token_b))
    exp_id = create_resp.json()["id"]

    resp = client.patch(f"/api/experiments/{exp_id}", json={
        "name": "Hijacked Name"
    }, headers=auth_headers(token_a))
    assert resp.status_code == 404, resp.text


def test_delete_experiment(client: TestClient):
    """A user can delete their own experiment."""
    token = register_and_login(client, USER_A)
    create_resp = client.post("/api/experiments", json={
        "name": "Experiment to Delete"
    }, headers=auth_headers(token))
    exp_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/experiments/{exp_id}", headers=auth_headers(token))
    assert delete_resp.status_code == 204, delete_resp.text

    # Verify it's gone
    get_resp = client.get(f"/api/experiments/{exp_id}", headers=auth_headers(token))
    assert get_resp.status_code == 404, get_resp.text


def test_delete_experiment_user_isolation(client: TestClient):
    """User A cannot delete User B's experiment."""
    token_a = register_and_login(client, USER_A)
    token_b = register_and_login(client, USER_B)

    create_resp = client.post("/api/experiments", json={
        "name": "Protected Experiment"
    }, headers=auth_headers(token_b))
    exp_id = create_resp.json()["id"]

    resp = client.delete(f"/api/experiments/{exp_id}", headers=auth_headers(token_a))
    assert resp.status_code == 404, resp.text


def test_dashboard_stats_reflect_real_data(client: TestClient):
    """Dashboard stats count should reflect actual experiment count."""
    token = register_and_login(client, USER_A)

    # Get baseline count
    stats_before = client.get("/api/experiments/stats", headers=auth_headers(token)).json()
    before_total = stats_before["total_experiments"]

    # Create a new experiment
    client.post("/api/experiments", json={"name": "Stats Test Experiment"},
                headers=auth_headers(token))

    stats_after = client.get("/api/experiments/stats", headers=auth_headers(token)).json()
    after_total = stats_after["total_experiments"]

    assert after_total == before_total + 1


def test_dashboard_stats_user_isolation(client: TestClient):
    """User B's experiments do not appear in User A's stats."""
    token_a = register_and_login(client, USER_A)
    token_b = register_and_login(client, USER_B)

    stats_a_before = client.get("/api/experiments/stats", headers=auth_headers(token_a)).json()

    # User B creates experiments
    for i in range(3):
        client.post("/api/experiments", json={"name": f"User B Exp {i}"},
                    headers=auth_headers(token_b))

    stats_a_after = client.get("/api/experiments/stats", headers=auth_headers(token_a)).json()

    # User A's count should not have changed
    assert stats_a_after["total_experiments"] == stats_a_before["total_experiments"]


def test_experiments_unauthenticated(client: TestClient):
    """All experiment endpoints require authentication."""
    assert client.get("/api/experiments").status_code == 403
    assert client.post("/api/experiments", json={"name": "X"}).status_code == 403
    assert client.get("/api/experiments/1").status_code == 403
    assert client.get("/api/experiments/stats").status_code == 403
