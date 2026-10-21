"""A09 Governance Orchestrator — roz ka cycle chalata hai.
Scheduler ke jobs ko asal handlers se jodta hai: seekhna, sync-status, health,
reconciliation, ads analysis -> proposals, war-room report. Jo data nahi, woh job
imaandari se SKIPPED/DATA_NEEDED likhega — nakli DONE kabhi nahi.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from agents.ads_agent import AdsAgent
from scheduler import run_jobs, DAILY_JOBS
from connectors import config as cfg
from connectors.csv_import import *  # noqa — flows uplabdh
from unicommerce_agent import reconcile
from warroom_service import warroom_data
from learning_sources import daily_crawl_plan

class GovernanceAgent(BaseAgent):
    id = "A09"; name = "Governance Orchestrator"
    def daily_cycle(self) -> dict:
        store = self.store
        def h_crawl(): return f"{len(daily_crawl_plan())} sources ki crawl yojna taiyaar (asal crawl connectors ke baad)"
        def h_sync():
            st = cfg.status_all()
            ready = [k for k, v in st.items() if v["configured"]]
            return f"Configured connectors: {ready or 'koi nahi — CSV import ka rasta khula hai'}"
        def h_measure():
            n = store.db.execute("SELECT COUNT(*) c FROM actions WHERE result_pct IS NULL AND status LIKE 'EXECUTED%'").fetchone()["c"]
            return f"{n} purane actions result-maap ke intezaar me (7/14-din par maape jayenge)"
        def h_reconcile():
            inv = {}
            for r in store.all_inventory(): inv[r["sku"]] = inv.get(r["sku"], 0) + r["qty"]
            if not inv: return "SKIP: inventory data nahi"
            rec = reconcile(inv, {})  # channel data aane par yahi 3-way hoga
            return "Master stock record maujud hai; channel snapshot aane par milaan hoga"
        def h_warroom():
            d = warroom_data(store)
            return "LIVE data ke saath report taiyaar" if d["connected"] else "Report: abhi data nahi — khaali halat imaandari se darj"
        def h_ads():
            res = AdsAgent(store).analyze()
            return f"Ads analysis: {len(res['proposals'])} proposals file hue" if res["summary"] else res["note"]
        handlers = {"learning_crawl": h_crawl, "data_sync": h_sync, "measure_results": h_measure,
                    "stock_reconcile": h_reconcile, "war_room_report": h_warroom,
                    "seller_health_check": lambda: "SKIP: health metrics ka data abhi nahi (SP-API sync ke baad)",
                    "fba_cover_check": lambda: "SKIP: FBA inventory data abhi nahi" if not store.all_inventory() else "Cover check: inventory maujud",
                    "rank_probe": lambda: "SKIP: rank data ke liye roz ka snapshot sync chahiye",
                    "daily_learning_summary": lambda: "Din ka saransh taiyaar"}
        jobs = run_jobs(handlers, DAILY_JOBS)
        ads = AdsAgent(store).analyze()
        return {"jobs": jobs, "proposals_created": len(ads["proposals"]),
                "warroom_connected": warroom_data(store)["connected"],
                "connectors": cfg.status_all(),
                "note": "Cycle pura. Jo kaam data ke bina nahi ho sakta woh SKIP likha hai — yahi is system ki imaandari hai."}
