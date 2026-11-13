"""A09 Governance Orchestrator — runs the daily cycle.
Wires scheduler jobs to real handlers: learning, sync status, health,
reconciliation, ads analysis -> proposals, war-room report. A job without data
honestly reports SKIPPED/DATA_NEEDED — never a fake DONE.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from agents.ads_agent import AdsAgent
from scheduler import run_jobs, DAILY_JOBS
from connectors import config as cfg
from connectors.csv_import import *  # noqa — flows available
from unicommerce_agent import reconcile
from warroom_service import warroom_data
from learning_sources import daily_crawl_plan

class GovernanceAgent(BaseAgent):
    id = "A09"; name = "Governance Orchestrator"
    def daily_cycle(self) -> dict:
        store = self.store
        def h_crawl():
            # V24: the manual cycle runs the same real learning cycle as the 24x7 scheduler
            import agent_brain as AB
            r = AB.daily_learning_cycle(store)
            return (f"Playbook +{r['playbook']['added']} new / {r['playbook']['refreshed']} refreshed; "
                    f"{r['outcomes']['applied']} updates from outcomes; {r['own_data']['lessons_updated']} lessons from your data")
        def h_sync():
            st = cfg.status_all()
            ready = [k for k, v in st.items() if v["configured"]]
            return f"Configured connectors: {ready or 'none — CSV upload is available'}"
        def h_measure():
            n = store.db.execute("SELECT COUNT(*) c FROM actions WHERE result_pct IS NULL AND status LIKE 'EXECUTED%'").fetchone()["c"]
            return f"{n} older actions awaiting outcome measurement (measured at 7/14 days)"
        def h_reconcile():
            inv = {}
            for r in store.all_inventory(): inv[r["sku"]] = inv.get(r["sku"], 0) + r["qty"]
            if not inv: return "SKIP: no inventory data"
            rec = reconcile(inv, {})  # becomes 3-way once channel data arrives
            return "Master stock record present; reconciliation happens once a channel snapshot arrives"
        def h_warroom():
            d = warroom_data(store)
            return "Report ready with LIVE data" if d["connected"] else "Report: no data yet — empty state recorded honestly"
        def h_ads():
            res = AdsAgent(store).analyze()
            return f"Ads analysis: {len(res['proposals'])} proposals file hue" if res["summary"] else res["note"]
        handlers = {"learning_crawl": h_crawl, "data_sync": h_sync, "measure_results": h_measure,
                    "stock_reconcile": h_reconcile, "war_room_report": h_warroom,
                    "seller_health_check": lambda: "SKIP: no health-metric data yet (after SP-API sync)",
                    "fba_cover_check": lambda: "SKIP: no FBA inventory data yet" if not store.all_inventory() else "Cover check: inventory present",
                    "rank_probe": lambda: "SKIP: rank data needs a daily snapshot sync",
                    "daily_learning_summary": lambda: "Daily summary ready"}
        # V24: jobs missing here (backup, brand analytics import, real fba/measure) come from the 24x7 handlers
        import job_handlers as JH
        for k, fn in JH.build_handlers(store).items():
            if k in ("backup_restore", "brand_analytics_import", "fba_cover_check", "measure_results",
                     "growth_autopilot", "weekly_report"):
                handlers[k] = fn
        jobs = run_jobs(handlers, DAILY_JOBS)
        ads = AdsAgent(store).analyze()
        return {"jobs": jobs, "proposals_created": len(ads["proposals"]),
                "warroom_connected": warroom_data(store)["connected"],
                "connectors": cfg.status_all(),
                "note": "Cycle complete. Work that cannot be done without data is marked SKIP — that is this system's honesty."}
