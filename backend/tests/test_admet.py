"""
Tests for ADMET screening — dataset loading, predictions, scoring, API endpoints.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.conftest import register_and_login, auth_headers, USER_A


# ── Unit Tests — Scoring Formula ─────────────────────────────

def test_composite_score_high_quality():
    """High pIC50, low toxicity, good solubility -> high composite score."""
    from ml.admet.scoring import compute_composite_score
    scores = compute_composite_score(
        picso=10.0, tox_prob=0.0, log_sol=0.0, lipinski_pass=True
    )
    assert scores["composite_score"] > 0.55  # 0.4*1.0 + 0.2*1.0 + 0.1*1.0 - 0.3*0.0 = 0.70, capped correctly
    assert scores["bioactivity_norm"] > 0.8
    assert scores["toxicity_risk_norm"] == 0.0
    assert scores["drug_likeness_norm"] == 1.0


def test_composite_score_toxic_molecule():
    """High toxicity -> score should be penalised."""
    from ml.admet.scoring import compute_composite_score
    s_safe  = compute_composite_score(picso=8.0, tox_prob=0.0, log_sol=-3.0, lipinski_pass=True)
    s_toxic = compute_composite_score(picso=8.0, tox_prob=1.0, log_sol=-3.0, lipinski_pass=True)
    assert s_safe["composite_score"] > s_toxic["composite_score"]


def test_composite_score_clipped_to_0_1():
    """Composite score must always be in [0, 1]."""
    from ml.admet.scoring import compute_composite_score
    for _ in range(20):
        picso  = np.random.uniform(3, 12)
        tox    = np.random.uniform(0, 1)
        log_s  = np.random.uniform(-12, 2)
        lip    = bool(np.random.randint(2))
        s = compute_composite_score(picso, tox, log_s, lip)
        assert 0.0 <= s["composite_score"] <= 1.0, f"Score out of range: {s}"


def test_picso_normalization():
    """pIC50 normalization: 4.0 -> 0.0, 11.0 -> 1.0."""
    from ml.admet.scoring import normalize_bioactivity
    assert normalize_bioactivity(4.0) == pytest.approx(0.0)
    assert normalize_bioactivity(11.0) == pytest.approx(1.0)
    assert 0.0 < normalize_bioactivity(7.5) < 1.0


def test_lipinski_filter():
    """filter_candidates with require_lipinski=True only returns Lipinski-pass molecules."""
    from ml.admet.scoring import filter_candidates
    df = pd.DataFrame({
        "predicted_pIC50": [8.0, 7.5, 7.0],
        "tox_probability": [0.1, 0.2, 0.1],
        "predicted_log_solubility": [-3.0, -4.0, -2.0],
        "lipinski_pass": [True, False, True],
        "composite_score": [0.7, 0.6, 0.65],
    })
    result = filter_candidates(df, require_lipinski=True, top_n_before_filter=0)
    assert all(result["lipinski_pass"] == True)


def test_filter_by_min_pic50():
    """Only molecules >= min_pic50 survive."""
    from ml.admet.scoring import filter_candidates
    df = pd.DataFrame({
        "predicted_pIC50": [9.0, 7.0, 5.0],
        "tox_probability": [0.1, 0.2, 0.1],
        "predicted_log_solubility": [-3.0, -4.0, -2.0],
        "lipinski_pass": [True, True, True],
        "composite_score": [0.8, 0.6, 0.4],
    })
    result = filter_candidates(df, min_pic50=7.5, top_n_before_filter=0)
    assert len(result) == 1
    assert result.iloc[0]["predicted_pIC50"] == 9.0


def test_filter_by_tox_risk():
    """Molecules with tox_probability > max_tox_risk are removed."""
    from ml.admet.scoring import filter_candidates
    df = pd.DataFrame({
        "predicted_pIC50": [8.0, 8.0, 8.0],
        "tox_probability": [0.1, 0.6, 0.9],
        "predicted_log_solubility": [-3.0, -3.0, -3.0],
        "lipinski_pass": [True, True, True],
        "composite_score": [0.8, 0.5, 0.2],
    })
    result = filter_candidates(df, max_tox_risk=0.5, top_n_before_filter=0)
    assert len(result) == 1
    assert result.iloc[0]["tox_probability"] == 0.1


# ── Unit Tests — RDKit Features ──────────────────────────────

def test_solubility_feature_extraction():
    """Valid SMILES produce valid 8-element feature vectors."""
    from ml.admet.solubility.pipeline import extract_rdkit_features
    smiles = ["CCO", "c1ccccc1", "CC(=O)O"]
    X, valid_idx = extract_rdkit_features(smiles)
    assert len(valid_idx) == 3
    assert X.shape == (3, 8)
    assert not np.any(np.isnan(X))


def test_invalid_smiles_in_feature_extraction():
    """Invalid SMILES is skipped during feature extraction (not crashing)."""
    from ml.admet.solubility.pipeline import extract_rdkit_features
    smiles = ["CCO", "INVALID_SMILES_XYZ", "c1ccccc1"]
    X, valid_idx = extract_rdkit_features(smiles)
    assert len(valid_idx) == 2  # Only 2 valid
    assert X.shape[0] == 2


def test_tox_feature_extraction_has_fp_bits():
    """Toxicity feature extraction produces 8 + 2048 = 2056 features."""
    from ml.admet.toxicity.pipeline import extract_rdkit_features as tox_extract
    smiles = ["CCO", "c1ccccc1"]
    X, valid_idx = tox_extract(smiles)
    assert X.shape == (2, 2056)


# ── Unit Tests — Dataset Inspection ─────────────────────────

def test_tox21_dataset_exists():
    """Tox21.csv must be present in data/raw/."""
    from ml.admet.config import TOX21_PATH
    assert TOX21_PATH.exists(), f"Tox21 not found at {TOX21_PATH}"


def test_esol_dataset_exists():
    """delaney-processed.csv must be present in data/raw/."""
    from ml.admet.config import ESOL_PATH
    assert ESOL_PATH.exists(), f"ESOL not found at {ESOL_PATH}"


def test_tox21_inspection():
    """Tox21 inspection produces valid stats for NR-AR endpoint."""
    from ml.admet.config import TOX21_PATH, TOX21_TARGET_ENDPOINT
    from ml.admet.toxicity.pipeline import load_and_inspect_tox21
    df, report = load_and_inspect_tox21(TOX21_PATH, TOX21_TARGET_ENDPOINT)
    assert report["total_rows"] == 7831
    assert report["endpoint_stats"]["toxic"] == 309
    assert report["endpoint_stats"]["non_toxic"] == 6956
    assert "NR-AR" in report["all_endpoints"]


def test_esol_inspection():
    """ESOL inspection produces valid stats."""
    from ml.admet.config import ESOL_PATH
    from ml.admet.solubility.pipeline import load_and_inspect_esol
    df, report = load_and_inspect_esol(ESOL_PATH)
    assert report["total_rows"] == 1128
    assert report["missing_target"] == 0


# ── API Tests ───────────────────────────────────────────────

def test_admet_model_info_endpoint(client: TestClient):
    """GET /admet/models returns toxicity and solubility model metadata."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "ADMET API Test"},
                      headers=auth_headers(token))
    assert exp.status_code == 201
    exp_id = exp.json()["id"]

    resp = client.get(f"/api/experiments/{exp_id}/admet/models",
                      headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "toxicity_model" in data
    assert "solubility_model" in data


def test_admet_run_and_get(client: TestClient):
    """POST /admet then GET /admet returns filtered candidates."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "ADMET Run Test"},
                      headers=auth_headers(token))
    assert exp.status_code == 201
    exp_id = exp.json()["id"]

    run_resp = client.post(f"/api/experiments/{exp_id}/admet?top_n_input=50",
                           headers=auth_headers(token))
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["total_screened"] == 50

    get_resp = client.get(f"/api/experiments/{exp_id}/admet?limit=10",
                          headers=auth_headers(token))
    assert get_resp.status_code == 200
    mol_data = get_resp.json()
    assert mol_data["returned"] == 10
    mol = mol_data["molecules"][0]
    assert "tox_probability" in mol
    assert "predicted_log_solubility" in mol
    assert "composite_score" in mol
    assert "tox_label" in mol
    assert mol["tox_label"] in ["Safe", "Toxic Risk", "Unavailable"]


def test_admet_filter_by_tox_risk_api(client: TestClient):
    """GET /admet with max_tox_risk=0.0 should return only non-toxic molecules."""
    token = register_and_login(client, USER_A)
    exp = client.post("/api/experiments", json={"name": "ADMET Filter Test"},
                      headers=auth_headers(token))
    exp_id = exp.json()["id"]
    client.post(f"/api/experiments/{exp_id}/admet?top_n_input=50",
                headers=auth_headers(token))

    resp = client.get(f"/api/experiments/{exp_id}/admet?max_tox_risk=0.0&limit=100",
                      headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    # All returned molecules should have 0 tox probability (none may pass — that's OK)
    for mol in data["molecules"]:
        if mol["tox_probability"] is not None:
            assert mol["tox_probability"] <= 0.0
