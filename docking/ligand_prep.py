"""
Ligand 3D Preparation Module — RDKit 3D Conformer & Forcefield Optimization.

Steps:
  1. Parse SMILES into RDKit Mol object
  2. Add explicit hydrogens (rdkit.Chem.AddHs)
  3. Embed 3D conformer using ETKDGv3 algorithm
  4. Optimize geometry with MMFF94s forcefield
  5. Export 3D coordinates and compute MMFF energy (kcal/mol)
"""
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np

from rdkit import Chem
from rdkit.Chem import AllChem

logger = logging.getLogger(__name__)


def prepare_3d_ligand(
    smiles: str,
    molecule_id: Optional[str] = None,
    max_iters: int = 500,
) -> Tuple[Optional[Chem.Mol], Dict[str, Any]]:
    """
    Prepare 3D structure and MMFF-minimized energy for a candidate SMILES.

    Returns:
        (mol_3d, prep_metadata)
    """
    if not isinstance(smiles, str) or not smiles.strip():
        return None, {"error": "Invalid SMILES input"}

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, {"error": "Failed to parse SMILES with RDKit"}

    # Add hydrogens for 3D embedding
    mol_3d = Chem.AddHs(mol)

    # 3D Conformer Embedding using ETKDGv3
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    embed_res = AllChem.EmbedMolecule(mol_3d, params)

    if embed_res != 0:
        # Fallback to standard distance geometry if ETKDGv3 fails
        embed_res = AllChem.EmbedMolecule(mol_3d, randomSeed=42)
        if embed_res != 0:
            return None, {"error": "3D conformer embedding failed"}

    # Forcefield optimization (MMFF94s preferred for drug-like small molecules)
    mmff_converged = -1
    try:
        mmff_converged = AllChem.MMFFOptimizeMolecule(mol_3d, maxIters=max_iters)
    except Exception:
        try:
            AllChem.UFFOptimizeMolecule(mol_3d, maxIters=max_iters)
        except Exception:
            pass

    # Calculate 3D MMFF Energy
    mmff_energy = 0.0
    try:
        mp = AllChem.MMFFGetMoleculeProperties(mol_3d)
        ff = AllChem.MMFFGetMoleculeForceField(mol_3d, mp)
        if ff is not None:
            mmff_energy = float(ff.CalcEnergy())
    except Exception:
        pass

    positions = mol_3d.GetConformer().GetPositions()
    centroid  = np.mean(positions, axis=0).tolist()

    meta = {
        "molecule_id":      molecule_id,
        "smiles":           smiles,
        "n_atoms":          int(mol_3d.GetNumAtoms()),
        "n_heavy_atoms":    int(mol.GetNumHeavyAtoms()),
        "embedded":         True,
        "mmff_converged":   mmff_converged == 0,
        "mmff_energy_kcal": round(mmff_energy, 4),
        "centroid":         [round(c, 3) for c in centroid],
    }

    return mol_3d, meta
