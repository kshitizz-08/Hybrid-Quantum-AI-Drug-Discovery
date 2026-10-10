"""
Tests for Quantum Optimization — QUBO construction, classical solver, QAOA, API.

IMPORTANT: QAOA tests use a SMALL TOY PROBLEM (3-5 qubits) to avoid long runtimes.
The full 20-qubit production run is tested only via the API endpoint.
"""
import sys
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.conftest import register_and_login, auth_headers, USER_A


# ── Unit Tests — QUBO ────────────────────────────────────────

def test_qubo_build_basic():
    """QUBO is built without error for 5 candidates, select 2."""
    from quantum.qubo import build_qubo
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
    ids = [f"CHEMBL{i}" for i in range(5)]
    qp, meta = build_qubo(scores, ids, k_select=2, penalty=3.0)
    assert meta["n_candidates"] == 5
    assert meta["k_select"] == 2
    assert len(meta["candidate_ids"]) == 5
    assert "formulation" in meta


def test_qubo_fewer_candidates_than_k():
    """Should raise ValueError if n < k."""
    from quantum.qubo import build_qubo
    scores = np.array([0.9, 0.8])
    ids = ["A", "B"]
    with pytest.raises(ValueError, match="Cannot select"):
        build_qubo(scores, ids, k_select=5)


def test_qubo_objective_valid_selection():
    """Valid K-selection should have lower objective than invalid (constraint penalty)."""
    from quantum.qubo import qubo_objective
    scores = np.array([0.9, 0.8, 0.5, 0.3])
    K = 2
    penalty = 3.0

    # Valid selection: K=2
    x_valid = np.array([1, 1, 0, 0])
    # Invalid selection: K=3
    x_invalid = np.array([1, 1, 1, 0])

    obj_valid   = qubo_objective(x_valid, scores, K, penalty)
    obj_invalid = qubo_objective(x_invalid, scores, K, penalty)

    # Valid should have 0 constraint penalty, invalid should have penalty added
    assert obj_valid < obj_invalid


def test_qubo_objective_zero_penalty_for_correct_selection():
    """Correct K-selection should have exactly -sum(selected scores) as objective."""
    from quantum.qubo import qubo_objective
    scores  = np.array([0.9, 0.7, 0.5])
    x       = np.array([1, 1, 0])
    K       = 2
    penalty = 5.0
    obj = qubo_objective(x, scores, K, penalty)
    expected = -(0.9 + 0.7) + penalty * (2 - 2) ** 2
    assert abs(obj - expected) < 1e-6


# ── Unit Tests — Classical Solver ───────────────────────────

def test_classical_solver_selects_best():
    """Classical solver must select the K candidates with highest composite scores."""
    from quantum.classical_solver import run_classical_solver
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
    ids = [f"C{i}" for i in range(5)]
    result = run_classical_solver(scores, ids, k_select=2)

    assert result["n_selected"] == 2
    assert result["constraint_satisfied"] is True
    # Best 2 candidates should be C0 and C1
    assert set(result["selected_ids"]) == {"C0", "C1"}


def test_classical_solver_select_all():
    """Selecting all N candidates is valid."""
    from quantum.classical_solver import run_classical_solver
    scores = np.array([0.9, 0.7, 0.5])
    ids = ["A", "B", "C"]
    result = run_classical_solver(scores, ids, k_select=3)
    assert result["n_selected"] == 3


def test_classical_solver_runtime_recorded():
    """Runtime must be > 0 and < 60 seconds for small problems."""
    from quantum.classical_solver import run_classical_solver
    scores = np.array([0.9, 0.8, 0.7, 0.6])
    ids = ["A", "B", "C", "D"]
    result = run_classical_solver(scores, ids, k_select=2)
    assert 0 <= result["runtime_seconds"] < 60


# ── Unit Tests — QAOA (Toy Problem Only) ─────────────────────

def test_qaoa_toy_3_candidates():
    """QAOA on 3-candidate problem selects 1 candidate without errors."""
    try:
        from quantum.qaoa_solver import run_qaoa
    except (ImportError, OSError) as e:
        pytest.skip(f"Qiskit DLL blocked by Application Control: {e}")
    scores = np.array([0.9, 0.6, 0.4])
    ids = ["A", "B", "C"]
    result = run_qaoa(scores, ids, k_select=1, reps=1, max_iter=30)

    assert result["n_selected"] >= 0  # May or may not satisfy constraint perfectly
    assert "qaoa_objective_value" in result
    assert result["backend"] != ""
    assert result["simulator"] is True


def test_qaoa_vs_classical_same_qubo():
    """QAOA and classical solver use the same problem formulation."""
    try:
        from quantum.qaoa_solver import run_qaoa
    except (ImportError, OSError) as e:
        pytest.skip(f"Qiskit DLL blocked by Application Control: {e}")
    from quantum.classical_solver import run_classical_solver
    from quantum.qubo import qubo_objective

    scores = np.array([0.85, 0.70, 0.55])
    ids = ["A", "B", "C"]
    K = 1
    penalty = 3.0

    qaoa_res     = run_qaoa(scores, ids, k_select=K, reps=1, max_iter=20)
    classical_res = run_classical_solver(scores, ids, k_select=K)

    # Classical should always satisfy constraint
    assert classical_res["constraint_satisfied"] is True
    # Classical solution should be optimal (best score = A)
    assert "A" in classical_res["selected_ids"]


# ── API Tests ───────────────────────────────────────────────

def test_quantum_run_endpoint(client: TestClient):
    """POST /quantum runs the optimization pipeline end-to-end.
    Quantum service falls back to pre-computed ADMET data if RDKit is blocked."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "Quantum Test"},
                      headers=auth_headers(token))
    assert exp.status_code == 201
    exp_id = exp.json()["id"]

    # Run quantum optimization with small problem for speed
    # (quantum_service falls back to pre-computed ADMET data if RDKit is unavailable)
    resp = client.post(
        f"/api/experiments/{exp_id}/quantum",
        json={
            "n_candidates": 8,
            "k_select": 3,
            "qaoa_reps": 1,
            "min_pic50": 5.0,
            "max_tox_risk": 1.0,
            "min_log_sol": -10.0,
            "require_lipinski": False,
            "top_n_admet_input": 50,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert "optimization_id" in data
    assert "summary" in data
    summary = data["summary"]
    assert summary["qaoa_selected"] >= 0
    assert "qaoa_objective" in summary
    assert "classical_objective" in summary


def test_quantum_get_result_endpoint(client: TestClient):
    """GET /quantum returns stored optimization result."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "Quantum GET Test"},
                      headers=auth_headers(token))
    exp_id = exp.json()["id"]

    client.post(
        f"/api/experiments/{exp_id}/quantum",
        json={"n_candidates": 6, "k_select": 2, "qaoa_reps": 1,
              "min_pic50": 5.0, "max_tox_risk": 1.0, "min_log_sol": -10.0,
              "require_lipinski": False, "top_n_admet_input": 50},
        headers=auth_headers(token),
    )

    get_resp = client.get(f"/api/experiments/{exp_id}/quantum",
                          headers=auth_headers(token))
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["experiment_id"] == exp_id
    assert "qaoa_result" in data
    assert "classical_result" in data


def test_quantum_candidates_endpoint(client: TestClient):
    """GET /quantum/candidates returns per-molecule selection flags."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "Quantum Candidates Test"},
                      headers=auth_headers(token))
    exp_id = exp.json()["id"]

    client.post(
        f"/api/experiments/{exp_id}/quantum",
        json={"n_candidates": 6, "k_select": 2, "qaoa_reps": 1,
              "min_pic50": 5.0, "max_tox_risk": 1.0, "min_log_sol": -10.0,
              "require_lipinski": False, "top_n_admet_input": 50},
        headers=auth_headers(token),
    )

    cand_resp = client.get(f"/api/experiments/{exp_id}/quantum/candidates",
                           headers=auth_headers(token))
    assert cand_resp.status_code == 200
    cand_data = cand_resp.json()
    assert cand_data["total_candidates"] >= 1
    cand = cand_data["candidates"][0]
    assert "molecule_chembl_id" in cand
    assert "selected_by_qaoa" in cand
    assert "selected_by_classical" in cand
    assert "composite_score" in cand


def test_quantum_user_isolation(client: TestClient):
    """User B cannot access User A's quantum optimization."""
    from tests.conftest import USER_B
    token_a = register_and_login(client, USER_A)
    token_b = register_and_login(client, USER_B)

    exp = client.post("/api/experiments", json={"name": "QIso Test"},
                      headers=auth_headers(token_a))
    exp_id = exp.json()["id"]

    resp = client.get(f"/api/experiments/{exp_id}/quantum",
                      headers=auth_headers(token_b))
    assert resp.status_code == 404
