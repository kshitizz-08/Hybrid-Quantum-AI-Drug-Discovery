"""
Quantum Optimization Configuration.

QAOA runs on AerSimulator (local statevector/shot-based simulator).
No real quantum hardware is required.

All results are labelled "Simulated — AerSimulator".
The system does NOT claim quantum advantage unless a controlled benchmark
demonstrates it. Language used: 'QAOA-based optimization'.
"""

# ── QAOA Hyperparameters ───────────────────────────────────────
QAOA_REPS    = 2         # Number of QAOA layers (p parameter)
QAOA_SHOTS   = 1024      # Number of measurement shots
QAOA_SEED    = 42        # Random seed for reproducibility
QAOA_BACKEND = "aer_simulator"  # Simulator backend name
QAOA_OPTIMIZER = "COBYLA"       # Classical optimizer for QAOA variational parameters

# ── QUBO Formulation Parameters ───────────────────────────────
# maximize: sum_i( score_i * x_i )
# subject to: sum_i( x_i ) = K (select exactly K candidates)
#
# Convert to minimization QUBO:
# minimize: -sum_i( score_i * x_i ) + penalty * (sum_i(x_i) - K)^2
#
# The penalty must be large enough to enforce the selection constraint.
# Rule of thumb: penalty > max(score_i) * N
QUBO_PENALTY = 5.0  # Lagrange penalty for constraint violation

# ── Problem size ───────────────────────────────────────────────
DEFAULT_N_CANDIDATES = 20   # Number of candidates entering QUBO
DEFAULT_K_SELECT     = 5    # Number of candidates to select

# ── Runtime limits ─────────────────────────────────────────────
# For unit tests, use a much smaller problem.
MAX_QUBITS_QAOA = 30  # Safety limit for simulator (>30 qubits = impractical)

# ── Results metadata ──────────────────────────────────────────
DISCLAIMER = (
    "ADMET predictions and quantum optimization results are computational outputs "
    "and do not constitute experimental or clinical validation. "
    "QAOA results do not establish quantum advantage unless supported by "
    "controlled benchmarking."
)
