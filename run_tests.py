"""Saare test suites ek command me:  python3 run_tests.py"""
import subprocess, glob, sys, os
files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "tests", "test_*.py")))
fail = 0
for f in files:
    r = subprocess.run([sys.executable, f], capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    print(f"{'✔' if r.returncode == 0 else '✘'} {os.path.basename(f)}: {last}")
    if r.returncode != 0:
        fail = 1; print(r.stdout[-1500:]); print(r.stderr[-1500:])
print("\nSAB PASS ✔" if not fail else "\nKUCH FAIL HAI ✘")
sys.exit(fail)
