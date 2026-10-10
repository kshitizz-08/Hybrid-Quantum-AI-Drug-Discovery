"""
QUBO (Quadratic Unconstrained Binary Optimization) Formulation.

Mathematical Formulation:
=========================

Binary variable per candidate:
  x_i in {0, 1}   where x_i = 1 means candidate i is SELECTED.

Objective (maximize composite score):
  maximize:   sum_i( score_i * x_i )

Selection constraint:
  sum_i( x_i ) = K   (select exactly K candidates)

QUBO conversion (minimize form):
  minimize:  -sum_i( score_i * x_i )
             + penalty * ( sum_i(x_i) - K )^2

Expanding the penalty term:
  penalty * (sum_i(x_i) - K)^2
  = penalty * ( sum_i(x_i^2)             <- diagonal (linear) terms
                + 2 * sum_{i<j}(x_i*x_j) <- off-diagonal (quadratic) terms
                - 2K * sum_i(x_i)        <- absorbed into linear
                + K^2 )                  <- constant (ignored)

Since x_i^2 = x_i for binary variables:
  Q[i,i] = -score_i - 2*K*penalty + penalty
  Q[i,j] = 2*penalty  for i != j

This is passed to the Qiskit QuadraticProgram via qiskit-optimization.
"""
import logging
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

from quantum.config import QUBO_PENALTY, DEFAULT_K_SELECT

logger = logging.getLogger(__name__)


def build_qubo(
    candidate_scores: np.ndarray,
    candidate_ids: List[str],
    k_select: int = DEFAULT_K_SELECT,
    penalty: float = QUBO_PENALTY,
) -> Tuple["QuadraticProgram", Dict]:  # type: ignore[name-defined]
    """
    Build a QUBO formulation for candidate selection.

    Args:
        candidate_scores: 1D array of composite scores in [0,1], length N.
        candidate_ids:    List of molecule ChEMBL IDs (length N).
        k_select:         Number of candidates to select (constraint).
        penalty:          Lagrange penalty coefficient for the selection constraint.

    Returns:
        (qp, qubo_metadata)
        qp:            Qiskit QuadraticProgram in QUBO form.
        qubo_metadata: Dict with problem description for logging/API.
    """
    n = len(candidate_scores)
    if n < k_select:
        raise ValueError(
            f"Cannot select {k_select} candidates from {n} total. "
            "Increase candidates or decrease k_select."
        )

    logger.info(
        "Building QUBO: N=%d candidates, K=%d to select, penalty=%.2f",
        n, k_select, penalty,
    )

    qp = None
    try:
        from qiskit_optimization import QuadraticProgram
        qp = QuadraticProgram(name="drug_candidate_selection")

        # Declare N binary variables: x_0, x_1, ..., x_{N-1}
        for i in range(n):
            qp.binary_var(name=f"x{i}")

        # Objective: minimize -sum(score_i * x_i) + penalty*(sum(x_i) - K)^2
        # Linear terms: -score_i + penalty*(1 - 2K) = -score_i - penalty*(2K-1)
        # Quadratic terms (i!=j): 2*penalty
        linear = {}
        quadratic = {}

        for i in range(n):
            linear[f"x{i}"] = float(-candidate_scores[i] - penalty * (2 * k_select - 1))

        for i in range(n):
            for j in range(i + 1, n):
                quadratic[(f"x{i}", f"x{j}")] = float(2 * penalty)

        qp.minimize(linear=linear, quadratic=quadratic)
    except (ImportError, OSError) as e:
        logger.warning(
            "Qiskit QuadraticProgram not available (%s). Classical QUBO metadata built successfully.",
            e,
        )
        qp = None

    qubo_metadata = {
        "n_candidates":    n,
        "k_select":        k_select,
        "penalty":         penalty,
        "candidate_ids":   candidate_ids,
        "candidate_scores": [float(s) for s in candidate_scores],
        "score_min":       float(np.min(candidate_scores)),
        "score_max":       float(np.max(candidate_scores)),
        "score_mean":      float(np.mean(candidate_scores)),
        "formulation": (
            "minimize: -sum_i(score_i * x_i) + penalty * (sum_i(x_i) - K)^2"
        ),
        "variable_meaning": "x_i=1 means candidate i is SELECTED",
        "constraint": f"sum_i(x_i) = {k_select}",
    }

    logger.info("QUBO built: %d binary variables, penalty=%.2f", n, penalty)
    return qp, qubo_metadata


def qubo_objective(
    x: np.ndarray,
    candidate_scores: np.ndarray,
    k_select: int,
    penalty: float = QUBO_PENALTY,
) -> float:
    """
    Evaluate QUBO objective value for a binary solution vector x.
    Used for comparing QAOA vs classical objective values.

    Args:
        x:               Binary solution array (0/1), length N.
        candidate_scores: Composite scores, length N.
        k_select:         Required number selected.
        penalty:          Lagrange penalty coefficient.

    Returns:
        QUBO objective (lower is better — minimization form).
    """
    objective = -float(np.dot(candidate_scores, x))
    constraint_violation = float((np.sum(x) - k_select) ** 2)
    return objective + penalty * constraint_violation
