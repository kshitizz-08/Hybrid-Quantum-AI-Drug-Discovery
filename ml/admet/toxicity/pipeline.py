"""
Toxicity Prediction Pipeline — Tox21 NR-AR Endpoint.

Dataset:
  Name:     Tox21 (MoleculeNet distribution)
  Source:   https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/tox21.csv.gz
  Endpoint: NR-AR (Nuclear Receptor — Androgen Receptor)
  Labels:   Binary — 0 = inactive (non-toxic), 1 = active (toxic)
  Size:     7,831 molecules total; NR-AR has 309 toxic / 6,956 non-toxic.
  Note:     Significant class imbalance — model uses class_weight='balanced'.

Features:
  Same 8 RDKit physicochemical descriptors as EGFR model:
  MW, LogP, TPSA, HBD, HBA, RotBonds, RingCount, FractionCsp3
  Plus Morgan fingerprints (radius=2, 2048 bits) stacked as additional features.
  This is a SEPARATE training task from the EGFR pIC50 model.
  The EGFR dataset is NOT used here.

Evaluation metrics (due to class imbalance):
  Accuracy, Precision, Recall, F1, ROC-AUC.
  ROC-AUC is the primary metric.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
)
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)


def load_and_inspect_tox21(path: Path, endpoint: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load Tox21 dataset and inspect the chosen endpoint.

    Returns:
        (df_raw, inspection_report)
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Tox21 dataset not found at {path}. "
            "Download from: https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/tox21.csv.gz"
        )

    df = pd.read_csv(path)
    report = {
        "source": "Tox21 — MoleculeNet",
        "file": path.name,
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "columns": list(df.columns),
        "smiles_present": int(df["smiles"].notna().sum()),
        "smiles_missing": int(df["smiles"].isna().sum()),
        "chosen_endpoint": endpoint,
        "endpoint_description": "Nuclear Receptor — Androgen Receptor (NR-AR)",
        "label_type": "binary (0=inactive, 1=active/toxic)",
        "endpoint_stats": {
            "total": int(len(df)),
            "toxic": int((df[endpoint] == 1).sum()),
            "non_toxic": int((df[endpoint] == 0).sum()),
            "missing": int(df[endpoint].isna().sum()),
        },
        "all_endpoints": [c for c in df.columns if c not in ["smiles", "mol_id"]],
    }
    return df, report


def extract_rdkit_features(smiles_list: list) -> Tuple[np.ndarray, list]:
    """
    Extract 8 RDKit descriptors + 2048-bit Morgan fingerprint for each SMILES.
    Returns (feature_matrix, valid_indices).
    """
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors, rdFingerprintGenerator

    rows = []
    valid_idx = []

    fp_gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)

    for i, smi in enumerate(smiles_list):
        if not isinstance(smi, str) or not smi.strip():
            continue
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue

        descriptors = [
            Descriptors.MolWt(mol),
            Descriptors.MolLogP(mol),
            Descriptors.TPSA(mol),
            rdMolDescriptors.CalcNumHBD(mol),
            rdMolDescriptors.CalcNumHBA(mol),
            rdMolDescriptors.CalcNumRotatableBonds(mol),
            rdMolDescriptors.CalcNumRings(mol),
            rdMolDescriptors.CalcFractionCSP3(mol),
        ]
        fp = fp_gen.GetFingerprintAsNumPy(mol).astype(np.float32)
        rows.append(np.concatenate([descriptors, fp]))
        valid_idx.append(i)

    if not rows:
        raise RuntimeError("No valid molecules found in Tox21 dataset.")

    return np.array(rows, dtype=np.float32), valid_idx


def train_toxicity_model(
    tox21_path: Path,
    endpoint: str,
    model_path: Path,
    scaler_path: Path,
    results_path: Path,
    random_seed: int = 42,
    hyperparams: dict = None,
) -> Dict[str, Any]:
    """
    Full toxicity model training pipeline.
    Returns evaluation metrics (all computed from real data).
    """
    from ml.admet.config import TOX_RF_HYPERPARAMS, TOX_TRAIN_RATIO, TOX_TEST_RATIO

    if hyperparams is None:
        hyperparams = TOX_RF_HYPERPARAMS

    logger.info("Loading Tox21 dataset: %s (endpoint=%s)", tox21_path, endpoint)
    df, inspection = load_and_inspect_tox21(tox21_path, endpoint)

    # Filter to rows with non-missing labels for chosen endpoint
    df_labeled = df[df[endpoint].notna()].copy()
    df_labeled[endpoint] = df_labeled[endpoint].astype(int)

    logger.info(
        "Labeled rows for %s: %d (%d toxic, %d non-toxic)",
        endpoint,
        len(df_labeled),
        int((df_labeled[endpoint] == 1).sum()),
        int((df_labeled[endpoint] == 0).sum()),
    )

    # Extract RDKit features
    logger.info("Extracting RDKit + Morgan features for %d molecules...", len(df_labeled))
    smiles_list = df_labeled["smiles"].tolist()
    X, valid_idx = extract_rdkit_features(smiles_list)
    df_valid = df_labeled.iloc[valid_idx].reset_index(drop=True)
    y = df_valid[endpoint].values
    n_features = X.shape[1]

    logger.info("Feature matrix: %s (8 descriptors + 2048 Morgan bits)", X.shape)
    logger.info("Invalid SMILES (RDKit): %d", len(df_labeled) - len(valid_idx))

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TOX_TEST_RATIO, random_state=random_seed, stratify=y
    )

    # Scale features
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)
    joblib.dump(scaler, scaler_path)

    # Train Random Forest
    logger.info("Training Random Forest Classifier (class_weight=balanced)...")
    clf = RandomForestClassifier(**hyperparams)
    clf.fit(X_train_sc, y_train)
    joblib.dump(clf, model_path)

    # Evaluate
    y_pred  = clf.predict(X_test_sc)
    y_proba = clf.predict_proba(X_test_sc)[:, 1]

    acc       = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall    = float(recall_score(y_test, y_pred, zero_division=0))
    f1        = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc   = float(roc_auc_score(y_test, y_proba))
    cm        = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "accuracy":  acc,
        "precision": precision,
        "recall":    recall,
        "F1":        f1,
        "ROC_AUC":   roc_auc,
        "confusion_matrix": cm,
        "n_test_samples": int(len(y_test)),
        "n_train_samples": int(len(y_train)),
    }

    results = {
        "metadata": {
            "dataset": tox21_path.name,
            "source": "Tox21 — MoleculeNet",
            "endpoint": endpoint,
            "label_type": "binary (0=inactive, 1=active/toxic)",
            "random_seed": random_seed,
            "n_features": n_features,
            "feature_description": "8 RDKit descriptors + 2048 Morgan fingerprints (ECFP4, radius=2)",
            "train_ratio": TOX_TRAIN_RATIO,
            "test_ratio": TOX_TEST_RATIO,
            "hyperparameters": hyperparams,
            "model_file": model_path.name,
        },
        "inspection": inspection,
        "metrics": metrics,
    }

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(
        "Toxicity model trained: Accuracy=%.4f | Precision=%.4f | Recall=%.4f | F1=%.4f | ROC-AUC=%.4f",
        acc, precision, recall, f1, roc_auc,
    )
    return results
