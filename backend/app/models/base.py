"""
All SQLAlchemy ORM models for the Hybrid Quantum-AI Drug Discovery Platform.

Tables:
  users                 — Registered researcher accounts
  targets               — Biological targets (e.g., EGFR)
  experiments           — Drug discovery experiment runs
  molecules             — Screened molecular compounds
  predictions           — AI-predicted bioactivity results
  model_versions        — Trained ML model metadata
  quantum_optimizations — QAOA / classical optimization runs
  quantum_candidates    — Molecules selected by quantum optimizer
  docking_runs          — AutoDock Vina job records
  docking_results       — Per-ligand docking binding affinities
  final_rankings        — Aggregated final candidate scores
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Index, Integer, JSON, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


# ── Enumerations ──────────────────────────────────────────────

class ExperimentStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BioactivityClass(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    INTERMEDIATE = "intermediate"


# ── Users ─────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    experiments = relationship("Experiment", back_populates="owner", cascade="all, delete-orphan")


# ── Targets ───────────────────────────────────────────────────

class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    chembl_id = Column(String(50), unique=True, index=True, nullable=True)
    uniprot_id = Column(String(50), nullable=True)
    organism = Column(String(200), nullable=True)
    target_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    pdb_id = Column(String(10), nullable=True)  # For docking
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    experiments = relationship("Experiment", back_populates="target")


# ── Experiments ───────────────────────────────────────────────

class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.PENDING, nullable=False)

    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=True)

    # Dataset info
    dataset_path = Column(String(500), nullable=True)
    dataset_version = Column(String(50), nullable=True)
    raw_record_count = Column(Integer, nullable=True)
    processed_record_count = Column(Integer, nullable=True)

    # Pipeline stage tracking
    preprocess_status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    preprocess_job_id = Column(String(100), nullable=True)
    screen_status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    screen_job_id = Column(String(100), nullable=True)
    quantum_status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    quantum_job_id = Column(String(100), nullable=True)
    docking_status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    docking_job_id = Column(String(100), nullable=True)

    # Configuration (stored as JSON)
    config = Column(JSON, nullable=True)
    preprocessing_report = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="experiments")
    target = relationship("Target", back_populates="experiments")
    molecules = relationship("Molecule", back_populates="experiment", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="experiment", cascade="all, delete-orphan")
    quantum_optimizations = relationship("QuantumOptimization", back_populates="experiment", cascade="all, delete-orphan")
    docking_runs = relationship("DockingRun", back_populates="experiment", cascade="all, delete-orphan")
    final_rankings = relationship("FinalRanking", back_populates="experiment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_experiments_owner_id", "owner_id"),
        Index("ix_experiments_status", "status"),
    )


# ── Molecules ─────────────────────────────────────────────────

class Molecule(Base):
    __tablename__ = "molecules"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)

    # Identity
    chembl_id = Column(String(50), index=True, nullable=True)
    smiles = Column(Text, nullable=True)
    inchi = Column(Text, nullable=True)
    inchi_key = Column(String(100), index=True, nullable=True)

    # Experimental bioactivity
    standard_value = Column(Float, nullable=True)       # IC50 raw value
    standard_units = Column(String(20), nullable=True)  # e.g., nM
    pic50 = Column(Float, nullable=True)                # Calculated pIC50

    # Bioactivity class
    bioactivity_class = Column(Enum(BioactivityClass), nullable=True)

    # RDKit molecular descriptors (populated in Milestone 3)
    molecular_weight = Column(Float, nullable=True)
    logp = Column(Float, nullable=True)
    tpsa = Column(Float, nullable=True)
    hbd = Column(Integer, nullable=True)    # H-bond donors
    hba = Column(Integer, nullable=True)    # H-bond acceptors
    rotatable_bonds = Column(Integer, nullable=True)
    ring_count = Column(Integer, nullable=True)
    fraction_csp3 = Column(Float, nullable=True)
    morgan_fingerprint = Column(Text, nullable=True)  # Stored as bit string

    # Lipinski flags
    lipinski_mw_ok = Column(Boolean, nullable=True)
    lipinski_logp_ok = Column(Boolean, nullable=True)
    lipinski_hbd_ok = Column(Boolean, nullable=True)
    lipinski_hba_ok = Column(Boolean, nullable=True)
    lipinski_pass = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment", back_populates="molecules")
    predictions = relationship("Prediction", back_populates="molecule", cascade="all, delete-orphan")
    docking_results = relationship("DockingResult", back_populates="molecule")
    final_rankings = relationship("FinalRanking", back_populates="molecule")

    __table_args__ = (
        Index("ix_molecules_experiment_id", "experiment_id"),
    )


# ── ML Model Versions ─────────────────────────────────────────

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)     # e.g., "random_forest", "xgboost"
    version = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=True)        # Path to .pkl / .joblib file
    dataset_version = Column(String(50), nullable=True)
    training_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)            # Currently serving predictions

    # Metrics (never hardcoded — filled by actual training)
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    n_train = Column(Integer, nullable=True)
    n_test = Column(Integer, nullable=True)

    # Config / feature metadata
    features_used = Column(JSON, nullable=True)
    hyperparameters = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    predictions = relationship("Prediction", back_populates="model_version")

    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_model_name_version"),
    )


# ── AI Predictions ────────────────────────────────────────────

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    molecule_id = Column(Integer, ForeignKey("molecules.id", ondelete="CASCADE"), nullable=False)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True)

    # Results (from actual model inference — never hardcoded)
    predicted_pic50 = Column(Float, nullable=True)
    bioactivity_score = Column(Float, nullable=True)  # Normalized 0-1
    confidence = Column(Float, nullable=True)
    is_active_predicted = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment", back_populates="predictions")
    molecule = relationship("Molecule", back_populates="predictions")
    model_version = relationship("ModelVersion", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_experiment_id", "experiment_id"),
        Index("ix_predictions_molecule_id", "molecule_id"),
    )


# ── Quantum Optimization ──────────────────────────────────────

class QuantumOptimization(Base):
    __tablename__ = "quantum_optimizations"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)

    # Configuration
    n_candidates_input = Column(Integer, nullable=True)   # Top-N from AI
    n_candidates_selected = Column(Integer, nullable=True)
    qaoa_depth = Column(Integer, nullable=True)           # QAOA circuit depth (p)
    backend_type = Column(String(50), nullable=True)      # "simulator" or "hardware"
    backend_name = Column(String(100), nullable=True)

    # Weights for objective function
    bioactivity_weight = Column(Float, default=0.5)
    diversity_weight = Column(Float, default=0.3)
    drug_likeness_weight = Column(Float, default=0.2)

    # Results (filled by actual computation)
    classical_objective_value = Column(Float, nullable=True)
    qaoa_objective_value = Column(Float, nullable=True)
    classical_runtime_seconds = Column(Float, nullable=True)
    qaoa_runtime_seconds = Column(Float, nullable=True)
    qubo_matrix = Column(JSON, nullable=True)             # Serialized QUBO
    qaoa_result_raw = Column(JSON, nullable=True)         # Raw Qiskit result

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    experiment = relationship("Experiment", back_populates="quantum_optimizations")
    candidates = relationship("QuantumCandidate", back_populates="optimization", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_quantum_optimizations_experiment_id", "experiment_id"),
    )


class QuantumCandidate(Base):
    __tablename__ = "quantum_candidates"

    id = Column(Integer, primary_key=True, index=True)
    optimization_id = Column(Integer, ForeignKey("quantum_optimizations.id", ondelete="CASCADE"), nullable=False)
    molecule_id = Column(Integer, ForeignKey("molecules.id"), nullable=False)

    selected_by_classical = Column(Boolean, default=False)
    selected_by_qaoa = Column(Boolean, default=False)
    quantum_score = Column(Float, nullable=True)
    rank_in_optimization = Column(Integer, nullable=True)

    # Relationships
    optimization = relationship("QuantumOptimization", back_populates="candidates")
    molecule = relationship("Molecule")


# ── Molecular Docking ─────────────────────────────────────────

class DockingRun(Base):
    __tablename__ = "docking_runs"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)

    # Target protein
    pdb_id = Column(String(10), nullable=True)
    receptor_file_path = Column(String(500), nullable=True)

    # Docking box configuration
    center_x = Column(Float, nullable=True)
    center_y = Column(Float, nullable=True)
    center_z = Column(Float, nullable=True)
    size_x = Column(Float, nullable=True)
    size_y = Column(Float, nullable=True)
    size_z = Column(Float, nullable=True)
    exhaustiveness = Column(Integer, default=8)
    n_poses = Column(Integer, default=9)

    # AutoDock Vina version
    vina_version = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    experiment = relationship("Experiment", back_populates="docking_runs")
    results = relationship("DockingResult", back_populates="docking_run", cascade="all, delete-orphan")


class DockingResult(Base):
    __tablename__ = "docking_results"

    id = Column(Integer, primary_key=True, index=True)
    docking_run_id = Column(Integer, ForeignKey("docking_runs.id", ondelete="CASCADE"), nullable=False)
    molecule_id = Column(Integer, ForeignKey("molecules.id"), nullable=False)

    # Binding affinity (kcal/mol) — from AutoDock Vina, NOT invented
    binding_affinity = Column(Float, nullable=True)
    best_pose_rmsd_lb = Column(Float, nullable=True)
    best_pose_rmsd_ub = Column(Float, nullable=True)
    n_poses_returned = Column(Integer, nullable=True)

    # File path to docked pose (for 3D visualization)
    pose_file_path = Column(String(500), nullable=True)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    docking_run = relationship("DockingRun", back_populates="results")
    molecule = relationship("Molecule", back_populates="docking_results")

    __table_args__ = (
        Index("ix_docking_results_docking_run_id", "docking_run_id"),
        Index("ix_docking_results_molecule_id", "molecule_id"),
    )


# ── Final Rankings ────────────────────────────────────────────

class FinalRanking(Base):
    __tablename__ = "final_rankings"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    molecule_id = Column(Integer, ForeignKey("molecules.id"), nullable=False)

    rank = Column(Integer, nullable=True)

    # Component scores (all normalized 0-1)
    bioactivity_score_norm = Column(Float, nullable=True)
    drug_likeness_score_norm = Column(Float, nullable=True)
    toxicity_score_norm = Column(Float, nullable=True)    # None if model unavailable
    solubility_score_norm = Column(Float, nullable=True)  # None if model unavailable
    quantum_score_norm = Column(Float, nullable=True)
    docking_score_norm = Column(Float, nullable=True)

    # Weights applied (stored for reproducibility)
    weights_used = Column(JSON, nullable=True)

    # Final composite score
    final_score = Column(Float, nullable=True)

    # Ranking methodology description
    methodology_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment", back_populates="final_rankings")
    molecule = relationship("Molecule", back_populates="final_rankings")

    __table_args__ = (
        Index("ix_final_rankings_experiment_id", "experiment_id"),
        UniqueConstraint("experiment_id", "molecule_id", name="uq_final_ranking_exp_mol"),
    )
