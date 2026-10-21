"""A08 Review / Customer Voice Agent — reviews padhkar asal shikayatein nikalta hai.
Shikayat ke pattern hi product/listing sudhar ki sabse sachhi list hai.
"""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent

COMPLAINTS = {
    "SIZE": ["chhota", "small", "size", "patla", "thin"],
    "QUALITY_TASTE": ["bura swad", "taste", "bakwas", "stale", "purana", "smell", "bedboo", "kharab quality"],
    "PACKING": ["packing", "packet phata", "leak", "damage", "toota"],
    "PRICE": ["mehenga", "expensive", "price zyada", "loot"],
    "DELIVERY": ["late", "delay", "der", "slow delivery"],
    "QUANTITY": ["kam quantity", "weight kam", "aadha", "less quantity"],
}
PRAISE = ["achha", "badhiya", "best", "fresh", "tasty", "superb", "mast", "value"]

def analyze_reviews(reviews: list) -> dict:
    """reviews: [{rating, text}]"""
    comp_count, praise = {}, 0
    neg = [r for r in reviews if (r.get("rating") or 5) <= 3]
    for r in reviews:
        t = (r.get("text") or "").lower()
        if any(w in t for w in PRAISE): praise += 1
        for cat, words in COMPLAINTS.items():
            if any(w in t for w in words): comp_count[cat] = comp_count.get(cat, 0) + 1
    top = max(comp_count, key=comp_count.get) if comp_count else None
    actions = {
        "SIZE": "Pack par grade/size bade aksharon me likho + size-comparison photo (shot 2) lagao — ummeed saaf hogi to shikayat ghategi",
        "QUALITY_TASTE": "Supplier/batch ki jaanch karo — freshness ka masla listing se nahi, maal se hai. FEFO lago karo",
        "PACKING": "Packing material badlo — ye sabse sasta sudhar hai aur return bhi ghataega",
        "PRICE": "Per-kg hisaab competitor se milao; chhota pack (250g) ka sasta entry variant banao",
        "DELIVERY": "FBA/Assured ka hissa badhao — delivery ki shikayat wahan sabse kam aati hai",
        "QUANTITY": "Pack par net weight aur 'bina shell ke wazan' saaf likho; jaanch me wazan pura nikle iski QC karo",
    }
    return {"total": len(reviews), "negative": len(neg), "praise_mentions": praise,
            "complaint_counts": comp_count, "top_complaint": top,
            "top_action": actions.get(top, "Koi bada pattern nahi — reviews swasth hain")}

class ReviewAgent(BaseAgent):
    id = "A08"; name = "Review / Customer Voice"
    def analyze(self, reviews: list) -> dict:
        r = analyze_reviews(reviews)
        if r["top_complaint"]:
            self.file_proposal("ALERT", f"Reviews ki sabse badi shikayat: {r['top_complaint']} ({r['complaint_counts'][r['top_complaint']]} baar) — {r['top_action']}")
        return r
