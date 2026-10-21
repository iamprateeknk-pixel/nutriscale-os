"""A02 Competitor Intelligence Agent — snapshots ka milaan.
Pichle snapshot se price badlav pakadna aur gap analysis — yahi roz ka kaam hai.
Snapshot data connector/scraping se aayega; agent ka dimaag (analysis) yahan hai.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from keyword_competitor import competitor_gap

class CompetitorAgent(BaseAgent):
    id = "A02"; name = "Competitor Intelligence"
    def detect_price_moves(self, previous: dict, current: dict) -> list:
        """previous/current: {competitor_sku: price_per_kg}. 5%+ badlav = hamla ya mauka."""
        moves = []
        for sku, price in current.items():
            old = previous.get(sku)
            if old:
                change = (price - old) / old * 100
                if change <= -5:
                    moves.append({"sku": sku, "change_pct": round(change, 1), "type": "PRICE_ATTACK",
                                  "action": "A07 ko bhejo: coupon/price jawab ka proposal bane"})
                    self.file_proposal("ALERT", f"Competitor hamla: {sku} par {change:.0f}% price gira — jawab chahiye")
                elif change >= 5:
                    moves.append({"sku": sku, "change_pct": round(change, 1), "type": "PRICE_UP",
                                  "action": "Mauka: competitor mehenga hua — apna price rakho, ads thoda badha sakte ho"})
        return moves
    def gap_report(self, yours: dict, comp: dict) -> dict:
        return competitor_gap(yours["price_per_kg"], comp["price_per_kg"],
                              yours["rating"], comp["rating"], yours["reviews"], comp["reviews"])
