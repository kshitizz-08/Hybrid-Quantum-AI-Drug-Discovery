"""
Tests for Pipeline, Preprocessing, RDKit features, and ML Prediction APIs.
"""
import pytest
from fastapi.testclient import TestClient
import numpy as np
import pandas as pd

from tests.conftest import register_and_login, auth_headers, USER_A
from ml.preprocessing.pipeline import preprocess_egfr_dataset
from ml.features.rdkit_features import compute_descriptors_for_smiles, check_lipinski


def test_pic50_calculation_formula():
    """Verify pIC50 formula: 9 - log10(IC50_nM)."""
    # IC50 = 100 nM -> pIC50 = 7.0
    ic50 = 100.0
    pic50 = 9 - np.log10(ic50)
    assert round(pic50, 2) == 7.00

    # IC50 = 1 nM -> pIC50 = 9.0
    assert round(9 - np.log10(1.0), 2) == 9.00


def test_preprocessing_pipeline_logic():
    """Test preprocessing pipeline on synthetic sample DataFrame."""
    sample_df = pd.DataFrame([
        {
            "molecule_chembl_id": "CHEMBL1",
            "canonical_smiles": "CC",
            "standard_type": "IC50",
            "standard_value": 10.0,
            "standard_units": "nM",
        },
        {
            "molecule_chembl_id": "CHEMBL2",
            "canonical_smiles": "CCC",
            "standard_type": "Ki",  # Should be filtered out
            "standard_value": 50.0,
            "standard_units": "nM",
        },
        {
            "molecule_chembl_id": "CHEMBL3",
            "canonical_smiles": "CCCC",
            "standard_type": "IC50",
            "standard_value": 100.0,
            "standard_units": "uM",  # Non-nM, should be filtered out
        },
    ])

    clean_df, report = preprocess_egfr_dataset(sample_df)
    assert report["initial_records"] == 3
    assert len(clean_df) == 1
    assert clean_df.iloc[0]["molecule_chembl_id"] == "CHEMBL1"
    assert round(clean_df.iloc[0]["pIC50"], 2) == 8.00  # 9 - log10(10) = 8


def test_rdkit_descriptor_extraction():
    """Verify RDKit descriptor calculation for Ethanol (CCO)."""
    desc = compute_descriptors_for_smiles("CCO", "ETHANOL")
    assert desc is not None
    assert desc["molecular_weight"] > 40
    assert "logP" in desc
    assert "TPSA" in desc
    assert desc["HBD"] == 1
    assert desc["HBA"] == 1


def test_rdkit_invalid_smiles_returns_none():
    """Invalid SMILES string should return None without throwing."""
    desc = compute_descriptors_for_smiles("INVALID_SMILES_STRING_123")
    assert desc is None


def test_lipinski_rule_pass():
    """A small drug-like molecule should pass Lipinski Rule of Five."""
    desc = {
        "molecular_weight": 350.0,
        "logP": 2.5,
        "HBD": 2,
        "HBA": 4,
    }
    assert check_lipinski(desc) is True


def test_pipeline_api_flow(client: TestClient):
    """Test full API pipeline flow: create exp -> preprocess -> metrics -> predict -> get predictions."""
    token = register_and_login(client, USER_A)

    # 1. Create experiment
    create_resp = client.post("/api/experiments", json={
        "name": "Pipeline Integration Test"
    }, headers=auth_headers(token))
    assert create_resp.status_code == 201, create_resp.text
    exp_id = create_resp.json()["id"]

    # 2. Trigger preprocessing endpoint
    prep_resp = client.post(f"/api/experiments/{exp_id}/preprocess", headers=auth_headers(token))
    assert prep_resp.status_code == 200, prep_resp.text
    prep_data = prep_resp.json()
    assert prep_data["initial_records"] > 10000
    assert prep_data["final_records"] > 5000

    # 3. Get preprocessing report
    report_resp = client.get(f"/api/experiments/{exp_id}/preprocess-report", headers=auth_headers(token))
    assert report_resp.status_code == 200, report_resp.text

    # 4. Get model metrics comparison
    metrics_resp = client.get(f"/api/experiments/{exp_id}/model-metrics", headers=auth_headers(token))
    assert metrics_resp.status_code == 200, metrics_resp.text
    metrics_data = metrics_resp.json()
    assert "RandomForest" in metrics_data["models"]
    assert "XGBoost" in metrics_data["models"]
    rf_mae = metrics_data["models"]["RandomForest"]["test_metrics"]["MAE"]
    assert rf_mae is not None and rf_mae > 0

    # 5. Run prediction
    pred_run_resp = client.post(f"/api/experiments/{exp_id}/predict?model_name=RandomForest", headers=auth_headers(token))
    assert pred_run_resp.status_code == 200, pred_run_resp.text

    # 6. Fetch candidate predictions
    get_preds_resp = client.get(f"/api/experiments/{exp_id}/predictions?limit=10", headers=auth_headers(token))
    assert get_preds_resp.status_code == 200, get_preds_resp.text
    preds_data = get_preds_resp.json()
    assert preds_data["total_molecules"] > 5000
    assert len(preds_data["predictions"]) == 10
    top_mol = preds_data["predictions"][0]
    assert "predicted_pIC50" in top_mol
    assert "smiles" in top_mol
    assert "lipinski_pass" in top_mol
