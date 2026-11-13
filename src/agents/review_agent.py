"""A08 Review / Customer Voice Agent — reads reviews and extracts the real complaints.
Complaint patterns are the most honest to-do list for product/listing improvements.
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
        "SIZE": "Print grade/size in large letters on the pack + add a size-comparison photo (shot 2) — clear expectations mean fewer complaints",
        "QUALITY_TASTE": "Check the supplier/batch — freshness is a product issue, not a listing issue. Apply FEFO",
        "PACKING": "Change the packing material — the cheapest fix, and it reduces returns too",
        "PRICE": "Match per-kg pricing with competitors; create a cheaper 250g entry pack",
        "DELIVERY": "Increase the FBA/Assured share — delivery complaints are lowest there",
        "QUANTITY": "Print net weight and 'weight without shell' clearly; QC that the weight checks out",
    }
    return {"total": len(reviews), "negative": len(neg), "praise_mentions": praise,
            "complaint_counts": comp_count, "top_complaint": top,
            "top_action": actions.get(top, "No major pattern — reviews are healthy")}

class ReviewAgent(BaseAgent):
    id = "A08"; name = "Review / Customer Voice"
    def analyze(self, reviews: list) -> dict:
        r = analyze_reviews(reviews)
        if r["top_complaint"]:
            self.file_proposal("ALERT", f"Top review complaint: {r['top_complaint']} ({r['complaint_counts'][r['top_complaint']]} times) — {r['top_action']}")
        return r
