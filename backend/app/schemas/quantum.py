"""Pydantic schemas for Quantum Optimization endpoints."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QUBOMetadata(BaseModel):
    n_candidates:      int
    k_select:          int
    penalty:           float
    formulation:       str
    variable_meaning:  str
    constraint:        str
    candidate_ids:     List[str]
    candidate_scores:  List[float]
    score_min:         float
    score_max:         float
    score_mean:        float


class QuantumRunResult(BaseModel):
    algorithm:             str
    backend:               str
    simulator:             bool
    n_candidates:          int
    k_select:              int
    qaoa_objective_value:  Optional[float]
    qubo_objective_value:  float
    n_selected:            int
    selected_indices:      List[int]
    selected_ids:          List[str]
    selected_scores:       List[float]
    runtime_seconds:       float
    status:                str
    constraint_satisfied:  bool


class ClassicalRunResult(BaseModel):
    algorithm:                  str
    backend:                    str
    n_candidates:               int
    k_select:                   int
    n_combinations_evaluated:   int
    classical_objective_value:  float
    qubo_objective_value:       float
    n_selected:                 int
    selected_ids:               List[str]
    selected_scores:            List[float]
    runtime_seconds:            float
    status:                     str


class QuantumCandidateDetail(BaseModel):
    rank:                       int
    molecule_chembl_id:         str
    smiles:                     str
    predicted_pIC50:            float
    tox_probability:            Optional[float]
    predicted_log_solubility:   Optional[float]
    composite_score:            float
    bioactivity_norm:           float
    toxicity_risk_norm:         float
    solubility_norm:            float
    drug_likeness_norm:         float
    lipinski_pass:              bool
    molecular_weight:           float
    logP:                       float
    selected_by_qaoa:           bool
    selected_by_classical:      bool


class QuantumPipelineSummary(BaseModel):
    total_egfr_molecules:  int
    admet_input_count:     int
    after_filter_count:    int
    quantum_input_count:   int


class QuantumOptimizationResponse(BaseModel):
    experiment_id:          int
    status:                 str
    pipeline:               QuantumPipelineSummary
    filter_config:          Dict[str, Any]
    quantum_config:         Dict[str, Any]
    qaoa_result:            QuantumRunResult
    classical_result:       ClassicalRunResult
    qubo_metadata:          QUBOMetadata
    candidates:             List[QuantumCandidateDetail]
    total_runtime_seconds:  float
    disclaimer:             str


class QuantumRunRequest(BaseModel):
    n_candidates:      int   = Field(20,   ge=5, le=30, description="Candidates to enter QUBO (max 30 for simulator)")
    k_select:          int   = Field(5,    ge=1, le=20, description="Candidates to select")
    qaoa_reps:         int   = Field(2,    ge=1, le=5,  description="QAOA layers (p)")
    min_pic50:         float = Field(7.0,  description="Min predicted pIC50 filter")
    max_tox_risk:      float = Field(0.5,  description="Max toxicity probability")
    min_log_sol:       float = Field(-6.0, description="Min log solubility (mol/L)")
    require_lipinski:  bool  = Field(False)
    top_n_admet_input: int   = Field(100,  ge=20, le=500)
