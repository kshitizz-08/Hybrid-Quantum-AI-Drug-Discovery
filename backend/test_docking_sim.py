"""Quick test for the simulated docking service."""
import sys
sys.path.insert(0, '.')
from app.services.docking_service import run_docking

try:
    r = run_docking('1M17', 3)
    print("status:", r['status'])
    print("simulated:", r.get('simulated'))
    print("n_successful:", r['n_successful'])
    print("best_affinity:", r['best_affinity'])
    if r['results']:
        print("first result:", r['results'][0])
    print("\nDocking service OK")
except Exception as e:
    import traceback
    print("ERROR:", e)
    traceback.print_exc()
