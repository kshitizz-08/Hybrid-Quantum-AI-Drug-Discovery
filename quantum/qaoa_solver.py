"""
QAOA Solver — Quantum Approximate Optimization Algorithm.

Backend: qiskit.primitives.StatevectorSampler (statevector-based simulator).
         No real quantum hardware required.

IMPORTANT DISCLAIMER:
  This implementation uses QAOA as a research demonstration.
  Results are labeled "Simulated — StatevectorSampler (Qiskit)".
  This system does NOT claim quantum advantage over classical methods.
  Language: "QAOA-based candidate optimization" — not "quantum speedup".

API Compatibility:
  qiskit >= 2.5.2
  qiskit-algorithms == 0.4.0
  qiskit-optimization == 0.7.0

  Uses StatevectorSampler (qiskit.primitives) which is compatible with
  qiskit-algorithms QAOA. AerSimulator SamplerV2 is NOT compatible with
  this version of qiskit-algorithms due to circuit instruction naming.
"""
import logging
import time
from typing import Dict, Any, List, Tuple

import numpy as np

from quantum.config import (
    QAOA_REPS, QAOA_SHOTS, QAOA_SEED, QAOA_BACKEND, QAOA_OPTIMIZER,
    DEFAULT_K_SELECT, DISCLAIMER,
)
from quantum.qubo import build_qubo, qubo_objective

logger = logging.getLogger(__name__)


def run_qaoa(
    candidate_scores: np.ndarray,
    candidate_ids: List[str],
    k_select: int = DEFAULT_K_SELECT,
    reps: int = QAOA_REPS,
    seed: int = QAOA_SEED,
    max_iter: int = 60,
) -> Dict[str, Any]:
    """
    Run QAOA on a drug candidate selection QUBO problem.

    Args:
        candidate_scores: Normalized composite scores [0,1], length N.
        candidate_ids:    ChEMBL IDs for each candidate.
        k_select:         Number of candidates to select.
        reps:             QAOA repetitions (p parameter).
        seed:             Random seed.
        max_iter:         Max COBYLA optimizer iterations.

    Returns:
        Dict with selected candidates, objective value, runtime, circuit info.
    """
    from qiskit.primitives import StatevectorSampler
    from qiskit_algorithms import QAOA
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit_optimization.algorithms import MinimumEigenOptimizer

    n = len(candidate_scores)
    logger.info(
        "Starting QAOA: N=%d candidates, K=%d to select, reps=%d, seed=%d",
        n, k_select, reps, seed,
    )

    if n > 30:
        raise ValueError(
            f"QAOA with N={n} qubits is impractical on a statevector simulator. "
            "Reduce n_candidates to <= 30."
        )

    # Build QUBO
    qp, qubo_meta = build_qubo(candidate_scores, candidate_ids, k_select)

    # Set up QAOA with elementary gate ansatz (rz, rzz, rx, h)
    # Decomposing PauliEvolutionGate prevents SciPy expm memory errors on N >= 15
    from qiskit_optimization.converters import QuadraticProgramToQubo
    from qiskit.circuit.library import QAOAAnsatz

    conv = QuadraticProgramToQubo()
    qubo_qp = conv.convert(qp)
    operator, _ = qubo_qp.to_ising()

    raw_ansatz = QAOAAnsatz(cost_operator=operator, reps=reps)
    ansatz = raw_ansatz.decompose().decompose()

    sampler = StatevectorSampler(seed=seed)
    optimizer = COBYLA(maxiter=max_iter)

    # Initial point: alternating beta/gamma for reps layers
    initial_point = np.zeros(2 * reps)
    initial_point[:reps]  = 0.5   # gamma (cost layer angles)
    initial_point[reps:]  = 0.5   # beta  (mixer layer angles)

    from qiskit_algorithms import SamplingVQE

    vqe = SamplingVQE(
        sampler=sampler,
        ansatz=ansatz,
        optimizer=optimizer,
        initial_point=initial_point,
    )
    eigen_optimizer = MinimumEigenOptimizer(vqe)

    t_start = time.time()
    result = eigen_optimizer.solve(qp)
    elapsed = time.time() - t_start

    x_solution = np.array(result.x, dtype=int)
    fval = float(result.fval)

    # Compute QUBO objective for the returned solution (should match fval)
    qubo_obj = qubo_objective(x_solution, candidate_scores, k_select)

    selected_indices = [i for i, v in enumerate(x_solution) if v == 1]
    selected_ids = [candidate_ids[i] for i in selected_indices]
    selected_scores = [float(candidate_scores[i]) for i in selected_indices]
    n_selected = int(np.sum(x_solution))

    # Get approximate circuit depth info
    try:
        from qiskit.circuit.library import QAOAAnsatz
        from qiskit_optimization.converters import QuadraticProgramToQubo
        from qiskit.quantum_info import SparsePauliOp
        conv = QuadraticProgramToQubo()
        qubo_qp = conv.convert(qp)
        circuit_info = {
            "n_qubits": n,
            "qaoa_reps": reps,
            "estimated_depth": reps * (n + n * (n - 1) // 2 + n) + 1,
        }
    except Exception:
        circuit_info = {"n_qubits": n, "qaoa_reps": reps}

    output = {
        "algorithm": "QAOA",
        "backend": "StatevectorSampler (qiskit.primitives — Simulated)",
        "simulator": True,
        "n_candidates": n,
        "k_select": k_select,
        "qaoa_reps": reps,
        "optimizer": "COBYLA",
        "max_iter": max_iter,
        "seed": seed,
        "solution": x_solution.tolist(),
        "qaoa_objective_value": round(fval, 6),
        "qubo_objective_value": round(qubo_obj, 6),
        "n_selected": n_selected,
        "selected_indices": selected_indices,
        "selected_ids": selected_ids,
        "selected_scores": selected_scores,
        "runtime_seconds": round(elapsed, 4),
        "status": "COMPLETED" if n_selected == k_select else "CONSTRAINT_VIOLATION",
        "constraint_satisfied": n_selected == k_select,
        "qubo_metadata": qubo_meta,
        "circuit_info": circuit_info,
        "disclaimer": DISCLAIMER,
    }

    logger.info(
        "QAOA complete: selected=%d/%d, objective=%.4f, time=%.2fs, constraint_ok=%s",
        n_selected, k_select, fval, elapsed, n_selected == k_select,
    )
    return output
