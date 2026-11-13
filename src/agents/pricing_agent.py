"""A07 Pricing Strategist — checks each product's margin and proposes prices.
Uses the calculator flows' math (Amazon/Flipkart); the decision (proposal) is the agent's.
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
        if not products: return {"evaluations": [], "note": "No product data — sync/import the catalog first"}
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
                    "PRICE_CHANGE", f"{p['name']}: margin {margin}% is below the {self.controls.min_margin_pct}% floor — raise the price or cut cost, keep ads off for it",
                    change_pct=8, predicted="Bring margin to a safe level")
            elif verdict == "THIN":
                ev["note"] = "Thin margin — limited ads on HERO keywords only, careful rank push"
            out.append(ev)
        return {"evaluations": out, "note": f"{len(out)} products checked"}
