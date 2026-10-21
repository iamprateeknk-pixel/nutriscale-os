"""NutriScale OS — Ek command me poora din ka cycle.
Chalana:  python3 src/run_cycle.py
Report terminal par saaf Hindi-English me aayegi; proposals DB me file ho jayenge
(backend ke /api/approvals par dikhenge).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store
from agents.governance import GovernanceAgent
from agents.market_agent import MarketAgent

def main():
    store = Store()
    try:
        print("=" * 62)
        print("🌰 NutriScale OS — Daily Cycle Report")
        print("=" * 62)
        season = MarketAgent(store).today_brief()
        print(f"\n📅 Aaj ka mausam: {season['season']} — {season['note']}")
        rep = GovernanceAgent(store).daily_cycle()
        print("\n⏰ Roz ke kaam (Scheduler):")
        for j in rep["jobs"]:
            out = j.get("output", j["status"])
            print(f"  {j['time']}  {j['job']:<24} {out[:90]}")
        print(f"\n📥 Aaj bane proposals: {rep['proposals_created']}")
        print(f"🔌 Connectors: " + ", ".join(
            f"{k}={'✔' if v['configured'] else '✘'}" for k, v in rep["connectors"].items()))
        print(f"📊 War Room data: {'🟢 LIVE' if rep['warroom_connected'] else '⚪ abhi data nahi (CSV import ya keys chahiye)'}")
        waiting = store.db.execute("SELECT COUNT(*) c FROM actions WHERE status LIKE 'WAITING%'").fetchone()["c"]
        print(f"✋ Tumhare faisle ka intezaar kar rahe approvals: {waiting}")
        print("\n" + rep["note"])
    finally:
        store.close()

if __name__ == "__main__":
    main()
