"""
Pydantic schemas for Pipeline & ML prediction endpoints.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class PreprocessingReportResponse(BaseModel):
    initial_records: int
    final_records: int
    unique_molecules: int
    total_removed: int
    removed: Dict[str, int]
    pic50_stats: Dict[str, float]
    settings: Dict[str, Any]


class MoleculePredictionItem(BaseModel):
    molecule_chembl_id: str
    smiles: str
    IC50_nM: float
    pIC50: float
    predicted_pIC50: float
    bioactivity_score: float
    molecular_weight: float
    logP: float
    TPSA: float
    HBD: int
    HBA: int
    rotatable_bonds: int
    ring_count: int
    fraction_csp3: float
    lipinski_pass: bool


class ModelPerformanceMetrics(BaseModel):
    MAE: Optional[float] = None
    RMSE: Optional[float] = None
    R2: Optional[float] = None
    n_test_samples: Optional[int] = None


class ModelDetailSchema(BaseModel):
    hyperparameters: Dict[str, Any]
    model_file: Optional[str]
    test_metrics: ModelPerformanceMetrics
    training_time_seconds: Optional[float] = None


class ModelComparisonResponse(BaseModel):
    metadata: Dict[str, Any]
    dataset_stats: Dict[str, Any]
    models: Dict[str, ModelDetailSchema]
    best_model_by_r2: str


class PredictionListResponse(BaseModel):
    total_molecules: int
    model_used: str
    predictions: List[MoleculePredictionItem]
