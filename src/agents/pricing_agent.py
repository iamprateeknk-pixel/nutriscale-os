"""A07 Pricing Strategist — har product ka margin parkhkar price ke proposals.
Calculator flows (Amazon/Flipkart) ka math istemal; faisla (proposal) agent ka.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from profit_calculator import SKU, contribution
from flipkart_calculator import flipkart_profit
from control_center import Controls

class PricingAgent(BaseAgent):
    id = "A07"; name = "Pricing Strategist"
    def __init__(self, store, controls: Controls = None):
        super().__init__(store); self.controls = controls or Controls()

    def evaluate_products(self) -> dict:
        products = self.store.all_products()
        if not products: return {"evaluations": [], "note": "Products data nahi — pehle catalog sync/import karo"}
        out = []
        for p in products:
            if p["platform"] == "Flipkart":
                r = flipkart_profit(p["price"], p["cost"] or 0)
                margin = r["margin_pct"]
            else:
                r = contribution(SKU(p["name"], p["price"], p["cost"] or 0))
                margin = r["margin_pct"]
            verdict = "HEALTHY" if margin >= 25 else "THIN" if margin >= self.controls.min_margin_pct else "LOSS_RISK"
            ev = {"sku": p["sku"], "name": p["name"], "platform": p["platform"],
                  "margin_pct": margin, "verdict": verdict}
            if verdict == "LOSS_RISK":
                ev["proposal"] = self.file_proposal(
                    "PRICE_CHANGE", f"{p['name']}: margin {margin}% floor {self.controls.min_margin_pct}% se kam — price badhao ya cost ghatao, ads is par band rakho",
                    change_pct=8, predicted="Margin surakshit star par laana")
            elif verdict == "THIN":
                ev["note"] = "Margin patla hai — sirf HERO keywords par simit ads, Rank-Push savdhani se"
            out.append(ev)
        return {"evaluations": out, "note": f"{len(out)} products parkhe gaye"}
