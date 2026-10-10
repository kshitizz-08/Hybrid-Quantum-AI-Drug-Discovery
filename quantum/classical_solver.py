"""
Classical Baseline Solver for QUBO Comparison.

Solves the SAME QUBO problem as QAOA using exact brute-force enumeration.
Guarantees the optimal solution for small N (N <= 25 practical).

Purpose: Provide a fair classical comparison baseline for QAOA results.
         Both solvers receive the SAME:
           - QUBO formulation
           - Candidate scores
           - k_select constraint
           - Penalty coefficient

The comparison shows QAOA objective vs classical optimal objective
on identical problem instances. No quantum advantage is claimed.
"""
import logging
import time
from typing import Dict, Any, List
from itertools import combinations

import numpy as np

from quantum.config import DEFAULT_K_SELECT, DISCLAIMER
from quantum.qubo import build_qubo, qubo_objective

logger = logging.getLogger(__name__)


def run_classical_solver(
    candidate_scores: np.ndarray,
    candidate_ids: List[str],
    k_select: int = DEFAULT_K_SELECT,
) -> Dict[str, Any]:
    """
    Exact classical brute-force QUBO solver.

    For each possible combination of K candidates from N, evaluates
    the QUBO objective and returns the globally optimal solution.

    Complexity: O(C(N, K)) — feasible for N <= 25.

    Args:
        candidate_scores: Normalized composite scores [0,1], length N.
        candidate_ids:    ChEMBL IDs for each candidate.
        k_select:         Number of candidates to select.

    Returns:
        Dict with selected candidates, optimal objective, runtime, method info.
    """
    n = len(candidate_scores)
    logger.info(
        "Starting classical exact solver: N=%d, K=%d, combinations=C(%d,%d)=%d",
        n, k_select, n, k_select,
        len(list(combinations(range(n), k_select))),
    )

    # Build QUBO for metadata
    _, qubo_meta = build_qubo(candidate_scores, candidate_ids, k_select)

    t_start = time.time()

    best_obj = float("inf")
    best_x   = None

    # Enumerate all valid K-selections
    for combo in combinations(range(n), k_select):
        x = np.zeros(n, dtype=int)
        for idx in combo:
            x[idx] = 1
        obj = qubo_objective(x, candidate_scores, k_select)
        if obj < best_obj:
            best_obj = obj
            best_x   = x.copy()

    elapsed = time.time() - t_start

    if best_x is None:
        raise RuntimeError("Classical solver found no valid solution.")

    selected_indices = [i for i, v in enumerate(best_x) if v == 1]
    selected_ids     = [candidate_ids[i] for i in selected_indices]
    selected_scores  = [float(candidate_scores[i]) for i in selected_indices]
    n_combinations   = 1
    for i in range(n - k_select + 1, n + 1):
        n_combinations *= i
    for i in range(1, k_select + 1):
        n_combinations //= i

    output = {
        "algorithm": "Classical Exact (Brute-Force Enumeration)",
        "backend": "CPU (Python itertools.combinations)",
        "simulator": False,
        "n_candidates": n,
        "k_select": k_select,
        "n_combinations_evaluated": n_combinations,
        "solution": best_x.tolist(),
        "classical_objective_value": round(best_obj, 6),
        "qubo_objective_value": round(best_obj, 6),
        "n_selected": int(np.sum(best_x)),
        "selected_indices": selected_indices,
        "selected_ids": selected_ids,
        "selected_scores": selected_scores,
        "runtime_seconds": round(elapsed, 4),
        "status": "OPTIMAL",
        "constraint_satisfied": True,
        "qubo_metadata": qubo_meta,
        "note": (
            "Brute-force classical solver guarantees global optimum for small N. "
            "Used as baseline comparison for QAOA output on the identical QUBO."
        ),
        "disclaimer": DISCLAIMER,
    }

    logger.info(
        "Classical solver complete: selected=%d, objective=%.4f, time=%.4fs",
        len(selected_indices), best_obj, elapsed,
    )
    return output
