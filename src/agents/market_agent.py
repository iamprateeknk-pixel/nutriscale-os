"""A01 Market Research Agent — prepares demand around the season/festival calendar.
Dates are season windows (each year's exact date is verified against the calendar) —
the dry-fruit year revolves around these windows.
"""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent

# (name, start month, peak month, what is special)
SEASONS = [
    ("Rakhi Gifting", 7, 8, "Gift packs, small combos — premium packing for sisters"),
    ("Diwali Gifting (biggest)", 9, 11, "Corporate hampers, gift boxes — the biggest opportunity of the year, stock 45 days ahead"),
    ("Wedding Season", 11, 2, "Bulk buying, shagun packs, premium grades (Mamra, W240)"),
    ("Ramadan / Eid", 2, 4, "Demand for dates (khajoor) and dry fruits — the date changes every year, verify it"),
    ("New Year / Fitness Resolution", 12, 1, "Healthy snacking, protein — New Year resolution shoppers"),
    ("Summer Dry Season", 4, 6, "Demand slows in mango season — use this time for listing/review improvements"),
]

def season_for_date(d: datetime.date) -> dict:
    m = d.month
    for name, start, peak, note in SEASONS:
        months = []
        cur = start
        while True:
            months.append(cur)
            if cur == peak: break
            cur = cur % 12 + 1
        if m in months:
            lead = 45 if "Diwali" in name else 30
            return {"season": name, "in_window": True, "note": note,
                    "prep": f"Have stock and listings ready {lead} days ahead; launch gift/hamper variants"}
    return {"season": "Normal", "in_window": False, "note": "No major season — time for fundamentals (reviews, images)",
            "prep": "Plan for the next season"}

class MarketAgent(BaseAgent):
    id = "A01"; name = "Market Research"
    def today_brief(self, today: datetime.date = None) -> dict:
        s = season_for_date(today or datetime.date.today())
        if s["in_window"]:
            self.file_proposal("ALERT", f"Season in progress: {s['season']} — {s['prep']}")
        return s
