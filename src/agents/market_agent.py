"""A01 Market Research Agent — mausam/festival calendar par demand ki taiyaari.
Tareekhein season-window ke roop me hain (har saal ki pakki tareekh calendar se verify hoti hai) —
dry fruits ka saal inhi windows ke aas-paas ghoomta hai.
"""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent

# (naam, shuru mahina, peak mahina, kya khaas hai)
SEASONS = [
    ("Rakhi Gifting", 7, 8, "Gift packs, chhote combos — behenon ke liye premium packing"),
    ("Diwali Gifting (sabse bada)", 9, 11, "Corporate hampers, gift boxes — saal ka sabse bada mauka, stock 45 din pehle"),
    ("Wedding Season", 11, 2, "Bulk kharid, shagun packs, premium grades (Mamra, W240)"),
    ("Ramadan / Eid", 2, 4, "Khajoor (dates) aur dry fruits ki mang — tareekh har saal badalti hai, verify karna"),
    ("New Year / Fitness Resolution", 12, 1, "Healthy snacking, protein — naye saal ke sankalp wale graahak"),
    ("Summer Dry Season", 4, 6, "Aam ke mausam me mang thodi dhimi — is samay listing/review sudhar ka kaam karo"),
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
                    "prep": f"Stock aur listing {lead} din pehle taiyaar rakho; gift/hamper variants live karo"}
    return {"season": "Normal", "in_window": False, "note": "Koi bada season nahi — temel sudhar (reviews, images) ka samay hai",
            "prep": "Agli season ki taiyaari ka plan banao"}

class MarketAgent(BaseAgent):
    id = "A01"; name = "Market Research"
    def today_brief(self, today: datetime.date = None) -> dict:
        s = season_for_date(today or datetime.date.today())
        if s["in_window"]:
            self.file_proposal("ALERT", f"Season chal raha hai: {s['season']} — {s['prep']}")
        return s
