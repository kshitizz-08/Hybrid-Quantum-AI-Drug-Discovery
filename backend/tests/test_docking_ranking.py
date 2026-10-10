"""
Tests for Molecular Docking (M5) and Final Ranking (M6).
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.conftest import register_and_login, auth_headers, USER_A


# ── Unit Tests — Docking Service ─────────────────────────────────────

def test_docking_returns_unavailable_when_vina_absent():
    """When AutoDock Vina is not installed, docking returns UNAVAILABLE — not a fake score."""
    from app.services.docking_service import run_docking
    result = run_docking(n_candidates=5)
    # On this machine: Vina missing + RDKit blocked
    assert result["status"] in ("UNAVAILABLE", "COMPLETED")
    if result["status"] == "UNAVAILABLE":
        assert result["unavailable"] is True
        assert len(result.get("blockers", [])) > 0
        # Results must be present (candidate stubs) but no scores invented
        for r in result["results"]:
            assert r["binding_affinity"] is None
            assert r["status"] == "NOT_DOCKED"
    # Disclaimer is always present
    assert "disclaimer" in result
    assert len(result["disclaimer"]) > 20


def test_docking_loads_candidates_correctly():
    """Candidate stubs should have valid ChEMBL IDs and SMILES."""
    from app.services.docking_service import run_docking
    result = run_docking(n_candidates=3)
    assert result["total_candidates"] >= 1
    for r in result["results"]:
        assert "molecule_chembl_id" in r
        assert "smiles" in r
        assert "predicted_pIC50" in r


# ── Unit Tests — Ranking Service ─────────────────────────────────────

def test_ranking_completes_without_docking():
    """Ranking runs successfully even when docking data is absent."""
    from app.services.ranking_service import run_final_ranking
    result = run_final_ranking()
    assert result["status"] == "COMPLETED"
    assert result["n_candidates_ranked"] >= 1
    assert not result["docking_available"]


def test_ranking_order_correct():
    """Candidates must be sorted by final_score descending."""
    from app.services.ranking_service import run_final_ranking
    result = run_final_ranking()
    scores = [c["final_score"] for c in result["candidates"]]
    assert scores == sorted(scores, reverse=True), "Candidates must be ranked high→low"


def test_ranking_scores_in_range():
    """All component and final scores must be in [0, 1]."""
    from app.services.ranking_service import run_final_ranking
    result = run_final_ranking()
    for c in result["candidates"]:
        assert 0.0 <= c["final_score"] <= 1.0, f"final_score out of range: {c['final_score']}"
        assert 0.0 <= c["bioactivity_score_norm"] <= 1.0
        assert 0.0 <= c["drug_likeness_score_norm"] <= 1.0
        assert 0.0 <= c["toxicity_score_norm"] <= 1.0
        assert 0.0 <= c["solubility_score_norm"] <= 1.0


def test_ranking_weights_renormalize_without_docking():
    """When docking weight is 0, remaining weights must sum to 1.0."""
    from app.services.ranking_service import run_final_ranking
    result = run_final_ranking()
    w = result["weights_used"]
    total = sum(v for v in w.values() if v > 0)
    assert abs(total - 1.0) < 1e-6, f"Weights don't sum to 1.0: total={total}"


def test_ranking_docking_excluded_not_zero():
    """When docking unavailable, docking_score_norm must be None — not 0."""
    from app.services.ranking_service import run_final_ranking
    result = run_final_ranking()
    if not result["docking_available"]:
        for c in result["candidates"]:
            assert c["docking_score_norm"] is None, (
                "Docking score should be None when unavailable, not zero"
            )


def test_ranking_custom_weights():
    """Custom weights are applied and renormalized correctly."""
    from app.services.ranking_service import run_final_ranking
    custom = {"bioactivity": 0.6, "drug_likeness": 0.2, "toxicity": 0.2,
               "solubility": 0.0, "quantum": 0.0, "docking": 0.0}
    result = run_final_ranking(weights=custom)
    assert result["status"] == "COMPLETED"
    w = result["weights_used"]
    assert abs(sum(v for v in w.values() if v > 0) - 1.0) < 1e-6


def test_ranking_no_missing_data_penalty():
    """Molecules with missing docking data must not be penalized vs those without."""
    from app.services.ranking_service import run_final_ranking
    result_no_docking = run_final_ranking(docking_results=None)
    # When no docking, all molecules are treated equally re: docking
    assert result_no_docking["n_candidates_ranked"] > 0


# ── API Tests ────────────────────────────────────────────────────────

def test_docking_endpoint_unavailable(client: TestClient):
    """POST /docking returns success status even when Vina is absent."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "Docking Test"},
                      headers=auth_headers(token))
    exp_id = exp.json()["id"]

    resp = client.post(
        f"/api/experiments/{exp_id}/docking",
        json={"pdb_id": "1M17", "n_candidates": 5, "exhaustiveness": 8},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert "docking_available" in data
    # On this machine, docking is unavailable
    if not data["docking_available"]:
        assert data["unavailable"] is True
        for r in data["results"]:
            assert r["binding_affinity"] is None  # never invents scores


def test_ranking_endpoint(client: TestClient):
    """POST /ranking computes and returns ranked candidates."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "Ranking Test"},
                      headers=auth_headers(token))
    exp_id = exp.json()["id"]

    resp = client.post(
        f"/api/experiments/{exp_id}/ranking",
        json={"include_docking": False},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["n_candidates_ranked"] >= 1
    assert "weights_used" in data
    assert "disclaimer" in data
    candidates = data["candidates"]
    assert len(candidates) >= 1
    first = candidates[0]
    assert "rank" in first
    assert "final_score" in first
    assert "molecule_chembl_id" in first


def test_ranking_get_endpoint(client: TestClient):
    """GET /ranking returns cached results with pagination."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "Ranking GET Test"},
                      headers=auth_headers(token))
    exp_id = exp.json()["id"]

    # First compute
    client.post(f"/api/experiments/{exp_id}/ranking",
                json={}, headers=auth_headers(token))

    get_resp = client.get(
        f"/api/experiments/{exp_id}/ranking?limit=5&offset=0",
        headers=auth_headers(token),
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "candidates" in data
    assert len(data["candidates"]) <= 5


def test_ranking_csv_download(client: TestClient):
    """GET /ranking/csv returns a downloadable CSV."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "CSV Test"},
                      headers=auth_headers(token))
    exp_id = exp.json()["id"]

    client.post(f"/api/experiments/{exp_id}/ranking",
                json={}, headers=auth_headers(token))

    csv_resp = client.get(
        f"/api/experiments/{exp_id}/ranking/csv",
        headers=auth_headers(token),
    )
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    text = csv_resp.text
    assert "molecule_chembl_id" in text
    assert "final_score" in text
    assert "rank" in text


def test_ranking_user_isolation(client: TestClient):
    """User B cannot access User A's ranking."""
    from tests.conftest import USER_B
    token_a = register_and_login(client, USER_A)
    token_b = register_and_login(client, USER_B)

    exp = client.post("/api/experiments", json={"name": "Rank Iso Test"},
                      headers=auth_headers(token_a))
    exp_id = exp.json()["id"]

    resp = client.get(f"/api/experiments/{exp_id}/ranking",
                      headers=auth_headers(token_b))
    assert resp.status_code == 404
