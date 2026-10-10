"""Pydantic schemas for Molecular Docking endpoints."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DockingGridBox(BaseModel):
    center: List[float] = Field([22.0, 0.5, 52.5], description="Binding box center [x, y, z] in Angstroms")
    size:   List[float] = Field([20.0, 20.0, 20.0], description="Binding box size [x, y, z] in Angstroms")


class DockingRunRequest(BaseModel):
    pdb_id:         str  = Field("1M17", description="PDB structure ID for target receptor")
    exhaustiveness: int  = Field(8, ge=1, le=64, description="AutoDock Vina exhaustiveness parameter")
    n_candidates:   int  = Field(15, ge=1, le=50, description="Number of top candidates to dock")
    grid_box:       Optional[DockingGridBox] = None


class DockingResultDetail(BaseModel):
    docking_rank:       int
    molecule_chembl_id: str
    smiles:             str
    predicted_pIC50:    float
    binding_affinity:   Optional[float]  # kcal/mol
    best_pose_rmsd_lb:  Optional[float]
    best_pose_rmsd_ub:  Optional[float]
    n_poses_returned:   Optional[int]
    status:             str
    mmff_energy_kcal:   Optional[float]


class DockingRunResponse(BaseModel):
    experiment_id:    int
    docking_run_id:   int
    status:           str
    receptor_pdb_id:  str
    total_docked:     int
    n_successful:     int
    n_failed:         int
    best_affinity:    Optional[float]
    avg_affinity:     Optional[float]
    runtime_seconds:  float
    grid_box:         Dict[str, Any]
    active_residues:  List[str]
    results:          List[DockingResultDetail]
    disclaimer:       str
