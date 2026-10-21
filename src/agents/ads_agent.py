"""A06 Ads Agent — DB ke asal search terms par Ads Engine chalata hai aur proposals file karta hai.
Data nahi hai to proposals NAHI banata — saaf bolta hai data chahiye.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from ads_engine import TermStats, decide
from control_center import Controls

class AdsAgent(BaseAgent):
    id = "A06"; name = "Ads Manager"
    def __init__(self, store, controls: Controls = None, target_roas: float = 4.0, target_cpa: float = 300.0):
        super().__init__(store); self.controls = controls or Controls()
        self.target_roas = target_roas; self.target_cpa = target_cpa

    def analyze(self) -> dict:
        rows = [dict(r) for r in self.store.db.execute("SELECT * FROM search_terms")]
        if not rows:
            return {"proposals": [], "summary": None,
                    "note": "Search-term data nahi hai — pehle Ads report import karo ya Ads API jodo. Bina data ke koi proposal nahi banega."}
        proposals, counts = [], {}
        total_spend = sum(r["spend"] for r in rows); total_sales = sum(r["sales"] for r in rows)
        for r in rows:
            d = decide(TermStats(r["term"], r["spend"], r["sales"], r["clicks"], 0, r["purchases"]),
                       self.target_roas, self.target_cpa)
            counts[d["action"]] = counts.get(d["action"], 0) + 1
            if d["action"] == "KILL_ADD_NEGATIVE":
                proposals.append(self.file_proposal("ADD_NEGATIVE", f"'{r['term']}' ko negative lagao — {d['reason']}"))
            elif d["action"] == "SCALE_BID_UP_20":
                proposals.append(self.file_proposal("BID_CHANGE", f"'{r['term']}' par bid +20% — {d['reason']}", change_pct=20))
            elif d["action"] == "BID_DOWN_20":
                proposals.append(self.file_proposal("BID_CHANGE", f"'{r['term']}' par bid -20% — {d['reason']}", change_pct=-20))
            elif d["action"] == "LISTING_PROBLEM":
                proposals.append(self.file_proposal("ALERT", f"'{r['term']}' — {d['reason']}"))
        return {"proposals": proposals,
                "summary": {"terms": len(rows), "total_spend": round(total_spend, 2),
                            "total_sales": round(total_sales, 2),
                            "blended_paid_roas": round(total_sales / total_spend, 2) if total_spend else 0,
                            "action_counts": counts},
                "note": "Negative wale Tier-0 me khud lagu ho gaye (EXECUTED_AUTO); bid wale tumhare approval ke intezaar me hain."}
