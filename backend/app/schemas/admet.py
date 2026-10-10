"""Pydantic schemas for ADMET screening endpoints."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ToxicityModelMetrics(BaseModel):
    accuracy:  Optional[float]
    precision: Optional[float]
    recall:    Optional[float]
    F1:        Optional[float]
    ROC_AUC:   Optional[float]
    n_test_samples: Optional[int]


class SolubilityModelMetrics(BaseModel):
    MAE:  Optional[float]
    RMSE: Optional[float]
    R2:   Optional[float]
    n_test_samples: Optional[int]


class ADMETModelSummary(BaseModel):
    toxicity_model:   Optional[Dict[str, Any]]
    solubility_model: Optional[Dict[str, Any]]


class ADMETMoleculeResult(BaseModel):
    molecule_chembl_id:         str
    smiles:                     str
    predicted_pIC50:            float
    pIC50:                      Optional[float]
    tox_probability:            Optional[float]
    tox_prediction:             Optional[int]   # 0=safe, 1=toxic, -1=failed
    tox_label:                  str             # "Safe" | "Toxic Risk" | "Unavailable"
    predicted_log_solubility:   Optional[float]
    solubility_label:           str             # "Good" | "Moderate" | "Poor" | "Unavailable"
    composite_score:            float
    bioactivity_norm:           float
    toxicity_risk_norm:         float
    solubility_norm:            float
    drug_likeness_norm:         float
    lipinski_pass:              bool
    molecular_weight:           float
    logP:                       float
    TPSA:                       float
    HBD:                        int
    HBA:                        int


class ADMETScreeningResponse(BaseModel):
    experiment_id:            int
    total_screened:           int
    model_info:               Dict[str, str]
    filter_config:            Dict[str, Any]
    molecules:                List[ADMETMoleculeResult]
    disclaimer:               str = (
        "ADMET predictions and quantum optimization results are computational outputs "
        "and do not constitute experimental or clinical validation."
    )


class FilterConfig(BaseModel):
    min_pic50:        float = Field(7.0, description="Minimum predicted pIC50")
    max_tox_risk:     float = Field(0.5, description="Maximum toxicity probability (0-1)")
    min_log_sol:      float = Field(-6.0, description="Minimum log solubility (log10 mol/L)")
    require_lipinski: bool  = Field(False, description="Require Lipinski Rule of Five pass")
    top_n_input:      int   = Field(100, description="Top N by pIC50 to screen")
    limit:            int   = Field(50, description="Max candidates to return")
