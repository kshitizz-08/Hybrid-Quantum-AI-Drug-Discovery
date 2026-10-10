"""
Receptor Preparation & Active Site Loading — EGFR Crystal Structure (1M17).
"""
import os
import urllib.request
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np

from docking.config import (
    DEFAULT_PDB_ID, DEFAULT_RECEPTOR_PATH, PDB_DOWNLOAD_URL,
    GRID_CENTER_X, GRID_CENTER_Y, GRID_CENTER_Z,
    GRID_SIZE_X, GRID_SIZE_Y, GRID_SIZE_Z,
)

logger = logging.getLogger(__name__)


def ensure_receptor_pdb(pdb_path: Path = DEFAULT_RECEPTOR_PATH) -> Path:
    """Download EGFR receptor PDB (1M17) if not already present."""
    if not pdb_path.exists():
        pdb_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading EGFR crystal structure PDB (%s) from RCSB...", DEFAULT_PDB_ID)
        try:
            urllib.request.urlretrieve(PDB_DOWNLOAD_URL, pdb_path)
            logger.info("Downloaded receptor PDB (%d bytes) to %s", pdb_path.stat().st_size, pdb_path)
        except Exception as e:
            logger.error("Failed to download PDB: %s", e)
            raise FileNotFoundError(f"Could not retrieve EGFR PDB 1M17: {e}")
    return pdb_path


def parse_receptor_active_site(
    pdb_path: Path = DEFAULT_RECEPTOR_PATH,
    box_center: Tuple[float, float, float] = (GRID_CENTER_X, GRID_CENTER_Y, GRID_CENTER_Z),
    box_size: Tuple[float, float, float] = (GRID_SIZE_X, GRID_SIZE_Y, GRID_SIZE_Z),
) -> Dict[str, Any]:
    """
    Parse receptor ATOM records from PDB and extract binding pocket residues
    within the active site grid box.
    """
    ensure_receptor_pdb(pdb_path)

    cx, cy, cz = box_center
    sx, sy, sz = box_size
    half_x, half_y, half_z = sx / 2.0, sy / 2.0, sz / 2.0

    atom_coords = []
    residues = set()

    with open(pdb_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("ATOM  "):
                try:
                    res_name = line[17:20].strip()
                    res_num  = line[22:26].strip()
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])

                    # Check if atom falls within binding pocket box
                    if (abs(x - cx) <= half_x and
                        abs(y - cy) <= half_y and
                        abs(z - cz) <= half_z):
                        atom_coords.append([x, y, z])
                        residues.add(f"{res_name}{res_num}")
                except Exception:
                    continue

    coords_arr = np.array(atom_coords) if atom_coords else np.empty((0, 3))

    return {
        "pdb_id":         DEFAULT_PDB_ID,
        "file_path":      str(pdb_path),
        "total_atoms_in_box": len(atom_coords),
        "residues_in_pocket": sorted(list(residues)),
        "pocket_centroid":  coords_arr.mean(axis=0).tolist() if len(coords_arr) > 0 else list(box_center),
        "grid_box": {
            "center": list(box_center),
            "size":   list(box_size),
        },
    }
