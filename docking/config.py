"""
Molecular Docking Configuration — Milestone 5.

Receptor Structure:
  PDB ID: 1M17 (Human EGFR Kinase Domain in Complex with Erlotinib/Tarceva)
  Resolution: 2.60 Å
  Source: RCSB Protein Data Bank (https://files.rcsb.org/download/1M17.pdb)

Binding Pocket Grid Box (centered on Tarceva binding site):
  Center X:  22.0 Å
  Center Y:   0.5 Å
  Center Z:  52.5 Å
  Size X:    20.0 Å
  Size Y:    20.0 Å
  Size Z:    20.0 Å

Docking Parameters:
  Exhaustiveness: 8
  Max Poses: 9
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DOCKING_DIR     = PROJECT_ROOT / "docking"
RECEPTORS_DIR   = DOCKING_DIR / "receptors"
DOCK_MODELS_DIR = DOCKING_DIR / "output"

RECEPTORS_DIR.mkdir(parents=True, exist_ok=True)
DOCK_MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── EGFR Receptor Structure ────────────────────────────────────
DEFAULT_PDB_ID = "1M17"
DEFAULT_RECEPTOR_PATH = RECEPTORS_DIR / f"{DEFAULT_PDB_ID}.pdb"
PDB_DOWNLOAD_URL = f"https://files.rcsb.org/download/{DEFAULT_PDB_ID}.pdb"

# ── Binding Box (Active Site Kinase Domain) ───────────────────
GRID_CENTER_X = 22.0
GRID_CENTER_Y =  0.5
GRID_CENTER_Z = 52.5

GRID_SIZE_X = 20.0
GRID_SIZE_Y = 20.0
GRID_SIZE_Z = 20.0

DEFAULT_EXHAUSTIVENESS = 8
DEFAULT_N_POSES        = 9

# ── Reference Binding Energy Benchmarks ───────────────────────
# Known experimental binding energies for comparison
BENCHMARKS = {
    "Erlotinib (Tarceva)": {"pdb_id": "1M17", "exp_affinity": -9.2},  # kcal/mol
    "Gefitinib (Iressa)":  {"pdb_id": "2ITN", "exp_affinity": -8.8},  # kcal/mol
    "Osimertinib (Tagrisso)":{"pdb_id": "3W2S", "exp_affinity": -9.8}, # kcal/mol
}
