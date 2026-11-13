"""A03 Keyword Agent — builds the keyword bank and rank-push picks from search terms in the DB.
The term that actually brings sales is the HERO — not just high-search talk.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from keyword_competitor import keyword_opportunity

BUY_WORDS = ["buy", "price", "500g", "1kg", "250g", "online", "pack"]
PRODUCT_WORDS = ["almond", "badam", "kaju", "cashew", "anjeer", "fig", "kishmish", "raisin", "pista", "pistachio", "akhrot", "walnut", "mamra", "dates", "khajoor"]

def intent_of(term: str) -> str:
    t = term.lower()
    if any(w in t for w in ["wholesale", "bulk rate", "mandi"]): return "B2B_SKIP"
    if any(w in t for w in BUY_WORDS): return "BUY_INTENT"
    if any(w in t for w in PRODUCT_WORDS): return "PRODUCT"
    return "GENERIC"

class KeywordAgent(BaseAgent):
    id = "A03"; name = "Keyword Domination"
    def build_bank(self) -> dict:
        # Each report row is one day — SUM per term first, otherwise no HERO is ever found
        rows = [dict(r) for r in self.store.db.execute(
            "SELECT term, SUM(clicks) clicks, SUM(purchases) purchases, SUM(spend) spend, SUM(sales) sales "
            "FROM search_terms GROUP BY term")]
        if not rows: return {"bank": [], "note": "No search-term data — the bank is empty; import data first"}
        bank = []
        for r in rows:
            intent = intent_of(r["term"])
            cvr = (r["purchases"] / r["clicks"]) if r["clicks"] else 0
            relevance = 0.9 if intent in ("BUY_INTENT", "PRODUCT") else 0.4
            # V12/KWD-01: the old clicks*20 'search volume' guess was REMOVED — it was never Amazon's
            # real volume. Demand signal = your real observed clicks.
            opp = keyword_opportunity(int(r["clicks"]), relevance, 0.6)
            tier = "HERO" if (r["purchases"] >= 5 and cvr >= 0.1) else opp["tier"]
            bank.append({"term": r["term"], "intent": intent, "purchases": r["purchases"],
                         "cvr_pct": round(cvr * 100, 1), "opportunity": opp["opportunity_score"], "tier": tier})
        bank.sort(key=lambda x: (x["tier"] != "HERO", -x["opportunity"]))
        heroes = [b for b in bank if b["tier"] == "HERO"]
        if heroes:
            self.file_proposal("ALERT", f"Keyword bank ready: {len(heroes)} HERO keywords for rank push — {', '.join(h['term'] for h in heroes[:3])}")
        return {"bank": bank, "heroes": heroes, "note": f"{len(bank)} terms checked, {len(heroes)} HERO terms found"}

    def placement_plan(self, nut: str, platform: str = "Amazon") -> dict:
        """V23: which keyword goes in title / highlights / backend / negative — with evidence labels."""
        import keyword_intel as KI
        return KI.placement_plan(self.store, nut, platform=platform)

    def sqp_diagnosis(self, platform: str = "Amazon") -> dict:
        """V23: Brand Analytics SQP funnel — what is wrong with each query (not visible / no clicks / no sales / scale up)."""
        import keyword_intel as KI
        f = KI.sqp_funnel(self.store.db, platform)
        scale = [q for q in f["queries"] if q["diagnosis"] == "SCALE_OPPORTUNITY"]
        if scale:
            self.file_proposal("ALERT", f"SQP: {len(scale)} queries convert but are not seen — "
                                        + ", ".join(q["query"] for q in scale[:3]))
        return f
