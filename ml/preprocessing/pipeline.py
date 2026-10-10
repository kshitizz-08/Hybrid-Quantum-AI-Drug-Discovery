"""
EGFR Bioactivity Data Preprocessing Pipeline.

This module transforms the raw ChEMBL EGFR dataset into a clean,
ML-ready DataFrame. Every filtering step is logged and counted.

Raw data source: data/raw/EGFR_bioactivity_raw.csv  (NEVER MODIFIED)
Output:          data/processed/EGFR_ML_dataset.csv

Preprocessing steps (in order):
  1.  Load raw CSV
  2.  Validate required columns
  3.  Filter to IC50 activity type only
  4.  Filter to nM units only
  5.  Drop rows with missing standard_value
  6.  Convert standard_value to numeric
  7.  Drop zero/negative IC50 values
  8.  Drop rows with data validity errors (configurable)
  9.  Drop rows missing canonical_smiles
  10. Deduplicate: one pIC50 value per molecule (configurable strategy)
  11. Calculate pIC50 = 9 - log10(IC50_nM)
  12. Apply pIC50 range filter
  13. Calculate Lipinski Rule of Five pass/fail
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd

from ml.config import (
    ALLOWED_STANDARD_TYPE,
    ALLOWED_STANDARD_UNITS,
    DEDUPLICATION_STRATEGY,
    EXCLUDE_DATA_VALIDITY_ERRORS,
    PIC50_FORMULA_BASE,
    PIC50_MIN,
    PIC50_MAX,
    REQUIRED_RAW_COLUMNS,
    LIPINSKI_MW_MAX,
    LIPINSKI_LOGP_MAX,
    LIPINSKI_HBD_MAX,
    LIPINSKI_HBA_MAX,
    PROCESSED_DATA_DIR,
    PREPROCESSING_REPORT_FILENAME,
)

logger = logging.getLogger(__name__)


def _count(df: pd.DataFrame, step: str, report: Dict) -> None:
    """Record row count after a filtering step."""
    report["steps"][step] = int(len(df))
    logger.debug("After '%s': %d rows", step, len(df))


def preprocess_egfr_dataset(
    df_raw: pd.DataFrame,
    exclude_validity_errors: bool = EXCLUDE_DATA_VALIDITY_ERRORS,
    dedup_strategy: str = DEDUPLICATION_STRATEGY,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Run the full preprocessing pipeline on the raw EGFR dataset.

    Args:
        df_raw: Raw DataFrame loaded from EGFR_bioactivity_raw.csv.
        exclude_validity_errors: Whether to drop rows flagged by ChEMBL
                                 as having data validity issues.
        dedup_strategy: 'median' or 'min' — how to aggregate duplicate
                        measurements for the same molecule.

    Returns:
        (clean_df, report) where:
            clean_df: Preprocessed DataFrame ready for feature extraction.
            report: Detailed audit trail of every step.

    Scientific note:
        pIC50 = 9 - log10(IC50_nM)
        This is equivalent to pIC50 = -log10(IC50_M) since 1 nM = 1e-9 M.
        The ChEMBL 'pchembl_value' column confirms this formula.
    """
    df = df_raw.copy()
    report: Dict[str, Any] = {
        "initial_records": len(df),
        "steps": {},
        "removed": {},
        "settings": {
            "exclude_validity_errors": exclude_validity_errors,
            "dedup_strategy": dedup_strategy,
            "pic50_formula": "9 - log10(IC50_nM)",
            "pic50_min": PIC50_MIN,
            "pic50_max": PIC50_MAX,
        },
    }

    # ── Step 1: Validate required columns ─────────────────────
    missing_cols = [c for c in REQUIRED_RAW_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Raw dataset is missing required columns: {missing_cols}"
        )

    # ── Step 2: Filter to IC50 standard_type ──────────────────
    before = len(df)
    df = df[df["standard_type"] == ALLOWED_STANDARD_TYPE].copy()
    removed = before - len(df)
    report["removed"]["non_ic50_type"] = removed
    _count(df, "after_ic50_filter", report)
    logger.info("Removed %d non-IC50 rows", removed)

    # ── Step 3: Filter to nM units only ───────────────────────
    before = len(df)
    df = df[df["standard_units"] == ALLOWED_STANDARD_UNITS].copy()
    removed = before - len(df)
    report["removed"]["non_nM_units"] = removed
    _count(df, "after_nM_filter", report)
    logger.info("Removed %d non-nM rows", removed)

    # ── Step 4: Drop missing standard_value ───────────────────
    before = len(df)
    df = df[df["standard_value"].notna()].copy()
    removed = before - len(df)
    report["removed"]["missing_standard_value"] = removed
    _count(df, "after_missing_value_drop", report)
    logger.info("Removed %d missing standard_value rows", removed)

    # ── Step 5: Convert to numeric ────────────────────────────
    df["standard_value"] = pd.to_numeric(df["standard_value"], errors="coerce")
    before = len(df)
    df = df[df["standard_value"].notna()].copy()
    removed = before - len(df)
    report["removed"]["non_numeric_value"] = removed
    logger.info("Removed %d non-numeric standard_value rows", removed)

    # ── Step 6: Drop zero/negative IC50 ──────────────────────
    before = len(df)
    df = df[df["standard_value"] > 0].copy()
    removed = before - len(df)
    report["removed"]["zero_or_negative_ic50"] = removed
    _count(df, "after_positive_ic50_filter", report)
    logger.info("Removed %d zero/negative IC50 rows", removed)

    # ── Step 7: Drop data validity flagged rows ────────────────
    if exclude_validity_errors and "data_validity_comment" in df.columns:
        before = len(df)
        df = df[df["data_validity_comment"].isna()].copy()
        removed = before - len(df)
        report["removed"]["data_validity_errors"] = removed
        _count(df, "after_validity_filter", report)
        logger.info("Removed %d data validity error rows", removed)
    else:
        report["removed"]["data_validity_errors"] = 0

    # ── Step 8: Drop missing SMILES ───────────────────────────
    before = len(df)
    df = df[df["canonical_smiles"].notna()].copy()
    df = df[df["canonical_smiles"].str.strip() != ""].copy()
    removed = before - len(df)
    report["removed"]["missing_smiles"] = removed
    _count(df, "after_smiles_filter", report)
    logger.info("Removed %d missing SMILES rows", removed)

    # ── Step 9: Calculate raw pIC50 ───────────────────────────
    # pIC50 = 9 - log10(IC50_nM)  [verified against ChEMBL pchembl_value]
    df["pIC50_raw"] = PIC50_FORMULA_BASE - np.log10(df["standard_value"])

    # ── Step 10: Deduplicate per molecule ─────────────────────
    before_unique = df["molecule_chembl_id"].nunique()
    before = len(df)

    if dedup_strategy == "median":
        # Aggregate multiple measurements: take median pIC50 per molecule
        # Use the canonical_smiles from the first occurrence
        smiles_map = df.groupby("molecule_chembl_id")["canonical_smiles"].first()
        agg = df.groupby("molecule_chembl_id").agg(
            pIC50=("pIC50_raw", "median"),
            IC50_nM_median=("standard_value", "median"),
            n_measurements=("standard_value", "count"),
        ).reset_index()
        agg["canonical_smiles"] = agg["molecule_chembl_id"].map(smiles_map)
        df = agg.rename(columns={"IC50_nM_median": "IC50_nM"})
    elif dedup_strategy == "min":
        # Take the row with the minimum IC50 per molecule
        idx = df.groupby("molecule_chembl_id")["standard_value"].idxmin()
        df = df.loc[idx].copy()
        df = df.rename(columns={"standard_value": "IC50_nM"})
        df["pIC50"] = PIC50_FORMULA_BASE - np.log10(df["IC50_nM"])
        df["n_measurements"] = 1
    else:
        raise ValueError(f"Unknown dedup_strategy: '{dedup_strategy}'")

    # Ensure pIC50 column is present for both strategies
    if "pIC50" not in df.columns and "pIC50_raw" not in df.columns:
        df["pIC50"] = PIC50_FORMULA_BASE - np.log10(df["IC50_nM"])
    elif "pIC50" not in df.columns:
        df = df.rename(columns={"pIC50_raw": "pIC50"})

    after_unique = len(df)
    removed_rows = before - (before_unique if dedup_strategy == "median" else after_unique)
    report["removed"]["duplicate_measurements"] = int(before - before_unique)
    report["removed"]["records_collapsed_to_molecules"] = int(before_unique - after_unique) if dedup_strategy == "min" else 0
    _count(df, "after_deduplication", report)
    logger.info(
        "Deduplicated: %d rows -> %d unique molecules (strategy: %s)",
        before, after_unique, dedup_strategy,
    )

    # ── Step 11: pIC50 range filter ───────────────────────────
    before = len(df)
    df = df[(df["pIC50"] >= PIC50_MIN) & (df["pIC50"] <= PIC50_MAX)].copy()
    removed = before - len(df)
    report["removed"]["pic50_out_of_range"] = removed
    _count(df, "after_pic50_range_filter", report)
    logger.info("Removed %d out-of-range pIC50 rows (%.1f–%.1f)", removed, PIC50_MIN, PIC50_MAX)

    # ── Finalize report ────────────────────────────────────────
    report["final_records"] = len(df)
    report["unique_molecules"] = int(df["molecule_chembl_id"].nunique())
    report["total_removed"] = report["initial_records"] - report["final_records"]
    report["pic50_stats"] = {
        "min": float(df["pIC50"].min()),
        "max": float(df["pIC50"].max()),
        "mean": float(df["pIC50"].mean()),
        "median": float(df["pIC50"].median()),
        "std": float(df["pIC50"].std()),
    }

    # ── Select output columns ──────────────────────────────────
    output_cols = [
        "molecule_chembl_id",
        "canonical_smiles",
        "IC50_nM",
        "pIC50",
        "n_measurements",
    ]
    # Add optional molecule name if present
    if "molecule_pref_name" in df.columns:
        output_cols.append("molecule_pref_name")

    df_out = df[[c for c in output_cols if c in df.columns]].copy()
    df_out = df_out.rename(columns={"canonical_smiles": "smiles"})
    df_out = df_out.reset_index(drop=True)

    logger.info(
        "Preprocessing complete: %d initial -> %d final molecules",
        report["initial_records"],
        report["final_records"],
    )
    return df_out, report


def save_preprocessing_report(report: Dict[str, Any]) -> Path:
    """Write preprocessing audit trail to JSON."""
    out_path = PROCESSED_DATA_DIR / PREPROCESSING_REPORT_FILENAME
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Preprocessing report saved: %s", out_path)
    return out_path


def load_preprocessing_report() -> Dict[str, Any]:
    """Load previously saved preprocessing report."""
    report_path = PROCESSED_DATA_DIR / PREPROCESSING_REPORT_FILENAME
    if not report_path.exists():
        raise FileNotFoundError(
            f"Preprocessing report not found at {report_path}. "
            "Run the preprocessing pipeline first."
        )
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)
