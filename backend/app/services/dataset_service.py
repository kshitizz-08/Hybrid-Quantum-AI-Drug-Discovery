"""
Dataset service — safe loading and validation of bioactivity datasets.
"""
import logging
from pathlib import Path
import pandas as pd
from fastapi import HTTPException, status
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_raw_dataset_path(filename: str = "EGFR_bioactivity_raw.csv") -> Path:
    """Return resolved absolute path to a raw dataset file."""
    base_dir = Path(settings.data_raw_path).resolve()
    if not base_dir.is_absolute():
        # Fallback relative to project root
        base_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw"
    return base_dir / filename


def get_processed_dataset_path(filename: str = "EGFR_ML_dataset.csv") -> Path:
    """Return resolved absolute path to a processed dataset file."""
    base_dir = Path(settings.data_processed_path).resolve()
    if not base_dir.is_absolute():
        base_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
    return base_dir / filename


def validate_dataset_file(file_path: Path, required_columns: list = None) -> None:
    """
    Validate that the specified dataset file exists and contains required columns.
    Raises HTTPException(404 or 422) if invalid.
    """
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset file not found at path: {file_path.name}",
        )

    if required_columns:
        # Read header only for fast validation
        try:
            header_df = pd.read_csv(file_path, nrows=1)
            missing = [col for col in required_columns if col not in header_df.columns]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Dataset is missing required columns: {missing}",
                )
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise exc
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to read dataset header: {str(exc)}",
            )


def load_raw_dataset(filename: str = "EGFR_bioactivity_raw.csv") -> pd.DataFrame:
    """Load raw dataset into DataFrame safely."""
    path = get_raw_dataset_path(filename)
    validate_dataset_file(path)
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading dataset file: {str(exc)}",
        )
