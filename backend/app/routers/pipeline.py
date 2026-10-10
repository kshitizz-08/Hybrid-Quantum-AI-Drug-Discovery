"""
Pipeline & ML Router — Preprocessing, Model Metrics, and Predictions.
"""
import logging
import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.experiment_service import get_experiment
from app.services.dataset_service import load_raw_dataset
from app.services.ml_service import (
    load_model_results,
    predict_for_processed_dataset,
    get_processed_dir,
)
from app.schemas.pipeline import (
    PreprocessingReportResponse,
    ModelComparisonResponse,
    PredictionListResponse,
    MoleculePredictionItem,
)
from app.models.base import ExperimentStatus, JobStatus

# Import ML pipeline functions
from ml.preprocessing.pipeline import preprocess_egfr_dataset, save_preprocessing_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/experiments", tags=["pipeline"])


@router.post("/{experiment_id}/preprocess", response_model=PreprocessingReportResponse)
def run_preprocessing(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run data preprocessing for an experiment.
    Reads the raw EGFR bioactivity dataset, filters non-IC50 / non-nM rows,
    calculates pIC50, deduplicates molecules, and updates experiment stats.
    """
    exp = get_experiment(db, experiment_id, current_user.id)

    try:
        exp.preprocess_status = JobStatus.RUNNING
        db.commit()

        # Load raw dataset
        df_raw = load_raw_dataset()

        # Run preprocessing
        df_clean, report = preprocess_egfr_dataset(df_raw)

        # Save report file
        save_preprocessing_report(report)

        # Update experiment record in database
        exp.preprocess_status = JobStatus.COMPLETED
        exp.raw_record_count = report["initial_records"]
        exp.processed_record_count = report["final_records"]
        exp.preprocessing_report = report
        exp.status = ExperimentStatus.RUNNING
        db.commit()
        db.refresh(exp)

        return PreprocessingReportResponse(**report)

    except Exception as exc:
        exp.preprocess_status = JobStatus.FAILED
        db.commit()
        logger.exception("Preprocessing failed for experiment %d", experiment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preprocessing failed: {str(exc)}",
        )


@router.get("/{experiment_id}/preprocess-report", response_model=PreprocessingReportResponse)
def get_preprocessing_report(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get preprocessing report audit trail for an experiment."""
    exp = get_experiment(db, experiment_id, current_user.id)
    if not exp.preprocessing_report:
        # Fall back to file if present
        report_path = get_processed_dir() / "EGFR_preprocessing_report.json"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                return PreprocessingReportResponse(**json.load(f))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preprocessing report not found. Run preprocessing first.",
        )
    return PreprocessingReportResponse(**exp.preprocessing_report)


@router.get("/{experiment_id}/model-metrics", response_model=ModelComparisonResponse)
def get_model_metrics(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get evaluation metrics (MAE, RMSE, R²) for trained Random Forest and XGBoost models.
    All metrics are computed on the held-out test set.
    """
    get_experiment(db, experiment_id, current_user.id)
    results = load_model_results()
    return ModelComparisonResponse(**results)


@router.post("/{experiment_id}/predict")
def run_predictions(
    experiment_id: int,
    model_name: str = Query("RandomForest", description="Model to use: 'RandomForest' or 'XGBoost'"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run AI predictions on preprocessed molecules using the trained model.
    Updates experiment status to COMPLETED for AI screening.
    """
    exp = get_experiment(db, experiment_id, current_user.id)

    try:
        exp.screen_status = JobStatus.RUNNING
        db.commit()

        predictions = predict_for_processed_dataset(model_name)

        exp.screen_status = JobStatus.COMPLETED
        db.commit()

        return {
            "status": "success",
            "message": f"Generated predictions for {len(predictions)} molecules using {model_name}.",
            "total_molecules": len(predictions),
            "model_used": model_name,
        }

    except Exception as exc:
        exp.screen_status = JobStatus.FAILED
        db.commit()
        logger.exception("Prediction failed for experiment %d", experiment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(exc)}",
        )


@router.get("/{experiment_id}/predictions", response_model=PredictionListResponse)
def get_predictions(
    experiment_id: int,
    model_name: str = Query("RandomForest", description="Model used: 'RandomForest' or 'XGBoost'"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    min_pIC50: Optional[float] = Query(None, description="Filter by minimum predicted pIC50"),
    search: Optional[str] = Query(None, description="Search by ChEMBL ID or SMILES"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get predicted bioactivity scores and RDKit descriptors for candidate molecules.
    Supports sorting, filtering, and pagination.
    """
    get_experiment(db, experiment_id, current_user.id)

    raw_preds = predict_for_processed_dataset(model_name)

    # Filtering
    filtered = raw_preds
    if min_pIC50 is not None:
        filtered = [m for m in filtered if m["predicted_pIC50"] >= min_pIC50]

    if search:
        s_lower = search.strip().lower()
        filtered = [
            m for m in filtered
            if s_lower in m["molecule_chembl_id"].lower() or s_lower in m["smiles"].lower()
        ]

    # Sort descending by predicted_pIC50
    filtered = sorted(filtered, key=lambda x: x["predicted_pIC50"], reverse=True)

    paginated = filtered[offset : offset + limit]

    items = [MoleculePredictionItem(**m) for m in paginated]

    return PredictionListResponse(
        total_molecules=len(filtered),
        model_used=model_name,
        predictions=items,
    )
