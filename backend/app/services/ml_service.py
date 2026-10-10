"""
ML Service — Loads trained models and generates predictions / metrics.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import joblib
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_models_dir() -> Path:
    """Return resolved path to the models directory."""
    path = Path(settings.models_path).resolve()
    if not path.exists():
        # Fallback relative to project root
        path = Path(__file__).resolve().parent.parent.parent.parent / "models"
    return path


def get_processed_dir() -> Path:
    """Return resolved path to processed data directory."""
    path = Path(settings.data_processed_path).resolve()
    if not path.exists():
        path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
    return path


def load_model_results() -> Dict[str, Any]:
    """Load evaluation metrics and metadata from training_results.json."""
    results_path = get_models_dir() / "training_results.json"
    if not results_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trained model metrics not found. Models must be trained first.",
        )
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading model results: {str(exc)}",
        )


def load_model(model_name: str = "RandomForest"):
    """Load joblib model artifact (RandomForest or XGBoost)."""
    models_dir = get_models_dir()
    if model_name.lower() in ["randomforest", "rf", "random_forest"]:
        filename = "egfr_random_forest.joblib"
    elif model_name.lower() in ["xgboost", "xgb"]:
        filename = "egfr_xgboost.joblib"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported model name: '{model_name}'. Choose 'RandomForest' or 'XGBoost'.",
        )

    model_path = models_dir / filename
    if not model_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model artifact '{filename}' not found. Please run model training first.",
        )
    try:
        return joblib.load(model_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading model artifact: {str(exc)}",
        )


def load_scaler():
    """Load StandardScaler artifact."""
    scaler_path = get_models_dir() / "egfr_descriptor_scaler.joblib"
    if not scaler_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Descriptor scaler artifact not found.",
        )
    return joblib.load(scaler_path)


def predict_for_processed_dataset(model_name: str = "RandomForest") -> List[Dict[str, Any]]:
    """
    Run predictions for all preprocessed molecules in EGFR_ML_dataset.csv.
    Returns list of molecule dictionaries with actual and predicted pIC50.
    """
    dataset_path = get_processed_dir() / "EGFR_ML_dataset.csv"
    if not dataset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed dataset EGFR_ML_dataset.csv not found. Run preprocessing first.",
        )

    df = pd.read_csv(dataset_path)
    model = load_model(model_name)
    scaler = load_scaler()

    descriptor_cols = [
        "molecular_weight", "logP", "TPSA", "HBD",
        "HBA", "rotatable_bonds", "ring_count", "fraction_csp3"
    ]
    X = df[descriptor_cols].values
    X_scaled = scaler.transform(X)

    preds = model.predict(X_scaled)
    df["predicted_pIC50"] = np.round(preds, 3)
    df["pIC50"] = np.round(df["pIC50"], 3)

    # Compute a normalized computational bioactivity score (0 - 100)
    # pIC50 range typically 3.0 to 12.0
    df["bioactivity_score"] = np.clip(
        np.round(((df["predicted_pIC50"] - 3.0) / 7.0) * 100, 1), 0, 100
    )

    results = df.to_dict(orient="records")
    return results
