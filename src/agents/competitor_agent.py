"""A02 Competitor Intelligence Agent — snapshot comparison.
Catching price changes since the last snapshot and gap analysis — that is the daily job.
Snapshot data comes from connectors/observations; the agent's brain (analysis) lives here.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from keyword_competitor import competitor_gap

class CompetitorAgent(BaseAgent):
    id = "A02"; name = "Competitor Intelligence"
    def detect_price_moves(self, previous: dict, current: dict) -> list:
        """previous/current: {competitor_sku: price_per_kg}. A 5%+ change = an attack or an opportunity."""
        moves = []
        for sku, price in current.items():
            old = previous.get(sku)
            if old:
                change = (price - old) / old * 100
                if change <= -5:
                    moves.append({"sku": sku, "change_pct": round(change, 1), "type": "PRICE_ATTACK",
                                  "action": "Send to A07: create a coupon/price response proposal"})
                    self.file_proposal("ALERT", f"Competitor attack: price dropped {change:.0f}% on {sku} — a response is needed")
                elif change >= 5:
                    moves.append({"sku": sku, "change_pct": round(change, 1), "type": "PRICE_UP",
                                  "action": "Opportunity: the competitor got pricier — hold your price, ads can go up a little"})
        return moves
    def gap_report(self, yours: dict, comp: dict) -> dict:
        return competitor_gap(yours["price_per_kg"], comp["price_per_kg"],
                              yours["rating"], comp["rating"], yours["reviews"], comp["reviews"])
