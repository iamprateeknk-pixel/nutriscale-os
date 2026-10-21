"""A03 Keyword Agent — DB ke search terms se keyword bank aur rank-push chunav.
Jo term asal me bikri de raha hai wahi HERO hai; sirf badi search wali baatein nahi.
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
        rows = [dict(r) for r in self.store.db.execute("SELECT * FROM search_terms")]
        if not rows: return {"bank": [], "note": "Search-term data nahi — bank khaali hai, pehle data import karo"}
        bank = []
        for r in rows:
            intent = intent_of(r["term"])
            cvr = (r["purchases"] / r["clicks"]) if r["clicks"] else 0
            relevance = 0.9 if intent in ("BUY_INTENT", "PRODUCT") else 0.4
            opp = keyword_opportunity(max(int(r["clicks"] * 20), 100), relevance, 0.6)
            tier = "HERO" if (r["purchases"] >= 5 and cvr >= 0.1) else opp["tier"]
            bank.append({"term": r["term"], "intent": intent, "purchases": r["purchases"],
                         "cvr_pct": round(cvr * 100, 1), "opportunity": opp["opportunity_score"], "tier": tier})
        bank.sort(key=lambda x: (x["tier"] != "HERO", -x["opportunity"]))
        heroes = [b for b in bank if b["tier"] == "HERO"]
        if heroes:
            self.file_proposal("ALERT", f"Keyword bank taiyaar: {len(heroes)} HERO keywords Rank-Push ke liye — {', '.join(h['term'] for h in heroes[:3])}")
        return {"bank": bank, "heroes": heroes, "note": f"{len(bank)} terms parkhe gaye, {len(heroes)} HERO mile"}
