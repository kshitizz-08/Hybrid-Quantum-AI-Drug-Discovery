"""
RDKit Molecular Feature Extraction.

Computes physicochemical descriptors and Morgan fingerprints for each molecule.

Descriptors computed:
  - Molecular Weight       (MolWt)
  - LogP                   (MolLogP — Wildman-Crippen)
  - Topological Polar SA   (TPSA)
  - H-Bond Donors          (NumHDonors)
  - H-Bond Acceptors       (NumHAcceptors)
  - Rotatable Bonds        (NumRotatableBonds)
  - Ring Count             (RingCount)
  - Fraction Csp3          (FractionCSP3)

Fingerprint:
  - Morgan (ECFP4 equivalent): radius=2, nBits=2048
    Reference: Rogers & Hahn, J. Chem. Inf. Model., 2010

All values are computed by RDKit from the SMILES string.
No values are invented or approximated.
"""
import logging
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy import of RDKit components so that the module can be imported
# even if RDKit is not installed (for type-checking contexts).
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
    from rdkit.Chem import rdFingerprintGenerator
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logger.error("RDKit is not installed. Feature extraction will not work.")


def _check_rdkit() -> None:
    if not RDKIT_AVAILABLE:
        raise RuntimeError(
            "RDKit is required for feature extraction. "
            "Install with: pip install rdkit"
        )


def compute_descriptors_for_smiles(
    smiles: str,
    molecule_id: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    """
    Compute all RDKit physicochemical descriptors for a single SMILES string.

    Args:
        smiles: Canonical SMILES string.
        molecule_id: Optional ID for logging purposes only.

    Returns:
        Dictionary of descriptor name → value, or None if SMILES is invalid.

    Note:
        Returns None for invalid SMILES. Never fabricates values.
    """
    _check_rdkit()

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        logger.warning(
            "RDKit could not parse SMILES for molecule %s: '%s...'",
            molecule_id or "unknown",
            smiles[:50] if smiles else "",
        )
        return None

    return {
        "molecular_weight": Descriptors.MolWt(mol),
        "logP":             Descriptors.MolLogP(mol),
        "TPSA":             Descriptors.TPSA(mol),
        "HBD":              rdMolDescriptors.CalcNumHBD(mol),
        "HBA":              rdMolDescriptors.CalcNumHBA(mol),
        "rotatable_bonds":  rdMolDescriptors.CalcNumRotatableBonds(mol),
        "ring_count":       rdMolDescriptors.CalcNumRings(mol),
        "fraction_csp3":    rdMolDescriptors.CalcFractionCSP3(mol),
    }


def compute_morgan_fingerprint(
    smiles: str,
    radius: int = 2,
    n_bits: int = 2048,
    molecule_id: Optional[str] = None,
) -> Optional[np.ndarray]:
    """
    Compute a Morgan fingerprint (ECFP4 equivalent) as a binary numpy array.

    Args:
        smiles: Canonical SMILES string.
        radius: Morgan radius (default=2, equivalent to ECFP4).
        n_bits: Number of fingerprint bits (default=2048).
        molecule_id: Optional ID for logging.

    Returns:
        numpy array of shape (n_bits,) with dtype uint8, or None if invalid.

    Reference:
        Rogers, D. & Hahn, M. (2010). Extended-Connectivity Fingerprints.
        J. Chem. Inf. Model., 50(5), 742–754. DOI: 10.1021/ci100050t
    """
    _check_rdkit()

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        logger.warning(
            "Could not generate fingerprint for molecule %s",
            molecule_id or "unknown",
        )
        return None

    gen = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
    fp = gen.GetFingerprintAsNumPy(mol)
    return fp.astype(np.uint8)


def compute_features_for_dataframe(
    df: pd.DataFrame,
    smiles_col: str = "smiles",
    id_col: str = "molecule_chembl_id",
    morgan_radius: int = 2,
    morgan_nbits: int = 2048,
) -> Tuple[pd.DataFrame, np.ndarray, List[str], Dict[str, Any]]:
    """
    Compute RDKit descriptors and Morgan fingerprints for all molecules in df.

    Args:
        df: DataFrame with SMILES and molecule IDs.
        smiles_col: Column name for SMILES.
        id_col: Column name for molecule IDs.
        morgan_radius: Morgan fingerprint radius.
        morgan_nbits: Morgan fingerprint bits.

    Returns:
        Tuple of:
          - descriptor_df: DataFrame with molecule IDs + 8 descriptor columns
          - fingerprint_matrix: np.ndarray (n_valid_mols × morgan_nbits)
          - valid_ids: List of molecule IDs with valid SMILES
          - stats: Dict with counts for valid, invalid, and descriptor stats
    """
    _check_rdkit()

    descriptor_rows = []
    fingerprints    = []
    valid_ids       = []
    invalid_ids     = []

    total = len(df)
    logger.info("Computing RDKit features for %d molecules...", total)

    for idx, row in df.iterrows():
        smiles  = row[smiles_col]
        mol_id  = row.get(id_col, f"mol_{idx}")

        if not isinstance(smiles, str) or not smiles.strip():
            invalid_ids.append(mol_id)
            continue

        desc = compute_descriptors_for_smiles(smiles, molecule_id=mol_id)
        fp   = compute_morgan_fingerprint(
            smiles, radius=morgan_radius, n_bits=morgan_nbits, molecule_id=mol_id
        )

        if desc is None or fp is None:
            invalid_ids.append(mol_id)
            continue

        desc[id_col] = mol_id
        descriptor_rows.append(desc)
        fingerprints.append(fp)
        valid_ids.append(mol_id)

        if (len(valid_ids)) % 500 == 0:
            logger.info("  Processed %d / %d molecules...", len(valid_ids), total)

    if not descriptor_rows:
        raise RuntimeError("No valid molecules found — RDKit feature extraction failed entirely.")

    descriptor_df = pd.DataFrame(descriptor_rows)
    # Put molecule ID first
    cols = [id_col] + [c for c in descriptor_df.columns if c != id_col]
    descriptor_df = descriptor_df[cols]

    fingerprint_matrix = np.array(fingerprints, dtype=np.uint8)

    stats = {
        "total_input":    total,
        "valid_molecules": len(valid_ids),
        "invalid_molecules": len(invalid_ids),
        "invalid_molecule_ids": invalid_ids[:50],  # cap at 50 for report
        "fingerprint_shape": list(fingerprint_matrix.shape),
        "morgan_radius": morgan_radius,
        "morgan_nbits": morgan_nbits,
        "descriptor_stats": {
            col: {
                "mean": float(descriptor_df[col].mean()),
                "std":  float(descriptor_df[col].std()),
                "min":  float(descriptor_df[col].min()),
                "max":  float(descriptor_df[col].max()),
            }
            for col in descriptor_df.columns
            if col != id_col
        },
    }

    logger.info(
        "Feature extraction complete: %d valid, %d invalid (RDKit parse failures)",
        len(valid_ids), len(invalid_ids),
    )

    return descriptor_df, fingerprint_matrix, valid_ids, stats


def check_lipinski(row: Dict[str, float]) -> bool:
    """
    Apply Lipinski Rule of Five to a descriptor dict.

    Rules:
      MW  ≤ 500
      LogP ≤ 5
      HBD  ≤ 5
      HBA  ≤ 10

    Returns True if the molecule passes all 4 rules.
    Reference: Lipinski et al., Adv. Drug. Deliv. Rev., 1997.
    """
    return (
        row.get("molecular_weight", 9999) <= 500 and
        row.get("logP", 9999) <= 5 and
        row.get("HBD", 9999) <= 5 and
        row.get("HBA", 9999) <= 10
    )
