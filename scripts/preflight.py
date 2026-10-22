#!/usr/bin/env python3
"""Preflight + reconciliation CLI (V16): python3 scripts/preflight.py [--reconcile]
Keys aane se PEHLE aur BAAD — dono samay taiyaari ki sachchai ek nazar me."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
import pilot as P

def main():
    # V17 fix: backend ke saath EK hi DB path — db_store.DEFAULT_PATH (data/growth_os.db)
    from db_store import DEFAULT_PATH
    db_path = os.environ.get("NUTRISCALE_DB") or DEFAULT_PATH
    store = Store(db_path)
    pf = P.preflight(store.db)
    print("=" * 60)
    print("NUTRISCALE PREFLIGHT — pilot taiyaari")
    print("=" * 60)
    for c in pf["checks"]:
        print(f"  [{'✔' if c['ok'] else '✘'}] {c['check']:<32} {c['detail']}")
    print(f"\nPilot ke liye takneeki taiyaari: {'HAAN' if pf['ready_for_pilot'] else 'ABHI NAHI'}")
    if "--reconcile" in sys.argv:
        print("\n" + json.dumps(P.reconciliation_report(store), indent=1, ensure_ascii=False, default=str))
    store.close()

if __name__ == "__main__":
    main()
