"""NutriScale OS — the whole daily cycle in one command.
Chalana:  python3 src/run_cycle.py
The report is printed to the terminal; proposals are filed in the DB
(visible in the dashboard Approval Inbox).
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
        print(f"\n📅 Season today: {season['season']} — {season['note']}")
        rep = GovernanceAgent(store).daily_cycle()
        print("\n⏰ Daily jobs (scheduler):")
        for j in rep["jobs"]:
            out = j.get("output", j["status"])
            print(f"  {j['time']}  {j['job']:<24} {out[:90]}")
        print(f"\n📥 Aaj bane proposals: {rep['proposals_created']}")
        print(f"🔌 Connectors: " + ", ".join(
            f"{k}={'✔' if v['configured'] else '✘'}" for k, v in rep["connectors"].items()))
        print(f"📊 War Room data: {'🟢 LIVE' if rep['warroom_connected'] else '⚪ no data yet (needs a CSV upload or API keys)'}")
        waiting = store.db.execute("SELECT COUNT(*) c FROM actions WHERE status LIKE 'WAITING%'").fetchone()["c"]
        print(f"✋ Approvals waiting for your decision: {waiting}")
        print("\n" + rep["note"])
    finally:
        store.close()

if __name__ == "__main__":
    main()
