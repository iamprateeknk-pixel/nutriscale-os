"""Keyword Intelligence (V23) — keyword kahan rakhna hai aur kis query par kya theek karna hai.

Teen sources, teeno ka saboot alag label ke saath:
  OBSERVED_ADS  = apni Ads search-term report (clicks/orders/spend — asal)
  BRAND_ANALYTICS = SQP report (market share funnel — Amazon ka apna data)
  SEED_VOCAB    = marketplace_knowledge ka shabdkosh (Hinglish/grade/pack) — sirf beej, volume UNKNOWN
Search volume ka koi andaaz nahi banaya jata (KWD-01 niyam).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12
import marketplace_knowledge as MK
from keyword_lab import normalize_term, EXCLUDE_INTENT

def _share(brand, total):
    return round(brand / total, 4) if total else None

def sqp_funnel(db, platform: str = "Amazon", min_impressions: float = 50) -> dict:
    """AMZ-Q-01..03: har query par impression→click→cart→purchase share, aur kis seedhi par girta hai."""
    ensure_v12(db)
    rows = db.execute("""SELECT query, SUM(search_volume) sv, SUM(impressions) im, SUM(brand_impressions) bim,
                                SUM(clicks) cl, SUM(brand_clicks) bcl, SUM(cart_adds) ca, SUM(brand_cart_adds) bca,
                                SUM(purchases) pu, SUM(brand_purchases) bpu,
                                MIN(period_start) ps, MAX(period_end) pe
                         FROM brand_analytics WHERE report_type='SQP' AND platform=? AND query IS NOT NULL AND query<>''
                         GROUP BY query""", (platform,)).fetchall()
    if not rows:
        return {"available": False, "queries": [],
                "note": "SQP data nahi — Seller Central > Brand Analytics > Search Query Performance export karke "
                        "data/brand_analytics_inbox/ me daalo (roz 06:45 khud import hoga)"}
    low_imp = MK.rule("AMZ-Q-03")["value"]["low_impr_share"]
    out = []
    for r in rows:
        if (r["im"] or 0) < min_impressions: continue
        s = {"impression": _share(r["bim"] or 0, r["im"]), "click": _share(r["bcl"] or 0, r["cl"]),
             "cart": _share(r["bca"] or 0, r["ca"]), "purchase": _share(r["bpu"] or 0, r["pu"])}
        diag, action, rid, prio = "HEALTHY", "Share banaye rakho; hafte-war trend dekho", "AMZ-Q-01", 3
        imp, clk, pur = s["impression"] or 0, s["click"], s["purchase"]
        if pur is not None and imp and pur > imp and imp < low_imp:
            diag, rid, prio = "SCALE_OPPORTUNITY", "AMZ-Q-03", 1
            action = "Convert karta hai par dikhta nahi — margin parkh kar is query par ads/bid badhao, title/backend me pakka karo"
        elif imp < 0.01:
            diag, rid, prio = "NOT_VISIBLE", "AMZ-Q-02", 2
            action = "Relevance/dikhne ki kami — keyword title ya backend me daalo, exact-match ad chalao"
        elif clk is not None and clk < imp * 0.6:
            diag, rid, prio = "TILE_PROBLEM", "AMZ-Q-02", 1
            action = "Dikhta hai par click nahi — main image, title ki pehli 40 akshar, price/per-100g, reviews/badge sudharo"
        elif pur is not None and clk and pur < clk * 0.6:
            diag, rid, prio = "OFFER_PROBLEM", "AMZ-Q-02", 1
            action = "Click aata hai par bikri nahi — price, A+ content, reviews, delivery speed, pack-size options parkho"
        out.append({"query": r["query"], "search_volume": r["sv"], "shares": s, "diagnosis": diag,
                    "action": action, "rule_id": rid, "priority": prio,
                    "period": f"{r['ps']}..{r['pe']}", "evidence": "BRAND_ANALYTICS (Amazon SQP)"})
    out.sort(key=lambda x: (x["priority"], -(x["search_volume"] or 0)))
    counts = {}
    for q in out: counts[q["diagnosis"]] = counts.get(q["diagnosis"], 0) + 1
    return {"available": True, "queries": out, "diagnosis_counts": counts,
            "note": "Share = tumhara hissa / poore market ka; funnel ki jis seedhi par girta hai wahi theek karo (AMZ-Q-02)"}

def seed_terms(nut: str, grade: str = None, weight: str = None) -> list:
    """Shabdkosh se beej-shabd — volume UNKNOWN, sirf backend/research ki disha.
    grade/weight diye hon to SIRF wahi variant — W240 kaju ke backend me W180/W320 ya doosra pack-size daalna
    galat variant ka shabd hai (kharidaar ko bhatkata hai, Amazon irrelevant terms mana karta hai)."""
    v = MK.NUT_VOCAB.get(nut)
    if not v: return []
    out = [nut, nut + "s"] + v["hinglish"] + v.get("hindi", [])
    g_low = (grade or "").lower()
    grades = [g for g in v["grades"] if g in g_low] if grade else v["grades"]
    out += [f"{g} {nut}" for g in grades] + [f"{g} {v['hinglish'][0]}" for g in grades if grade]
    packs = [weight.lower().replace(" ", "")] if weight else MK.INTENT_MODIFIERS["pack"]
    out += [f"{nut} {p}" for p in packs] + ([f"{v['hinglish'][0]} {p}" for p in packs] if weight else [])
    out += [f"{v['hinglish'][0]} {u}" for u in MK.INTENT_MODIFIERS["use"][:3]]
    return out

def keyword_universe(store, nut: str = None, platform: str = "Amazon", grade: str = None, weight: str = None) -> list:
    """Teeno sources ko ek suchi me — har term ka saboot aur kaam ka score."""
    db = store.db; ensure_v12(db)
    terms = {}
    def get(t):
        # Raw term par pehchan — 'badam' aur 'almond' alag shabd hain (backend me dono chahiye), normalized sirf jaankari
        k = t.lower().strip()
        return terms.setdefault(k, {"term": k, "normalized": normalize_term(k), "sources": set(), "clicks": 0, "orders": 0,
                                    "spend": 0.0, "sales": 0.0, "sqp": None})
    for r in db.execute("SELECT term, SUM(clicks) cl, SUM(purchases) pu, SUM(spend) sp, SUM(sales) sa FROM search_terms GROUP BY term"):
        if nut and nut not in normalize_term(r["term"]): continue
        e = get(r["term"]); e["sources"].add("OBSERVED_ADS")
        e["clicks"] += r["cl"] or 0; e["orders"] += r["pu"] or 0; e["spend"] += r["sp"] or 0; e["sales"] += r["sa"] or 0
    f = sqp_funnel(db, platform)
    for q in f["queries"]:
        if nut and nut not in normalize_term(q["query"]): continue
        e = get(q["query"]); e["sources"].add("BRAND_ANALYTICS"); e["sqp"] = {"shares": q["shares"], "diagnosis": q["diagnosis"],
                                                                            "search_volume": q["search_volume"]}
    if nut:
        for t in seed_terms(nut, grade, weight):
            get(t)["sources"].add("SEED_VOCAB")
    out = []
    for e in terms.values():
        excluded = any(x in e["normalized"] for x in EXCLUDE_INTENT)
        cvr = e["orders"] / e["clicks"] if e["clicks"] else None
        score = 0.0
        score += min(e["orders"] * 2, 60)
        score += min((cvr or 0) * 200, 30)
        if e["sales"] > e["spend"] > 0: score += 10
        if e["sqp"]:
            sv = e["sqp"]["search_volume"] or 0
            score += min(sv / 500, 20)
            if e["sqp"]["diagnosis"] == "SCALE_OPPORTUNITY": score += 10
        if e["sources"] == {"SEED_VOCAB"}: score = 1.0  # sirf beej — saboot aane tak neeche
        wasted = e["spend"] >= 200 and e["orders"] == 0
        out.append({"term": e["term"], "normalized": e["normalized"], "sources": sorted(e["sources"]),
                    "clicks": e["clicks"], "orders": e["orders"], "cvr_pct": round(cvr * 100, 1) if cvr is not None else None,
                    "spend": round(e["spend"], 2), "sales": round(e["sales"], 2), "sqp": e["sqp"],
                    "excluded": excluded, "wasted_spend": wasted,
                    "score": 0 if excluded else round(score, 1),
                    "search_volume_status": "BRAND_ANALYTICS" if e["sqp"] else "UNKNOWN (koi andaaz nahi)"})
    return sorted(out, key=lambda x: -x["score"])

def placement_plan(store, nut: str, title_slots: int = 1, highlight_slots: int = 4, platform: str = "Amazon",
                   grade: str = None, weight: str = None) -> dict:
    """Kaunsa keyword kahan: TITLE (sabse saboot-wala 1) → ITEM_HIGHLIGHTS/BULLETS → BACKEND (variants, Hinglish) → NEGATIVE."""
    uni = keyword_universe(store, nut, platform, grade, weight)
    plan = {"TITLE": [], "HIGHLIGHTS_BULLETS": [], "BACKEND": [], "NEGATIVE_ADS": [], "RESEARCH_MORE": []}
    for k in uni:
        if k["excluded"] or k["wasted_spend"]:
            plan["NEGATIVE_ADS"].append({"term": k["term"], "why": "galat irada" if k["excluded"] else f"₹{k['spend']} kharch, 0 order"})
            continue
        proven = k["orders"] >= 3 or (k["sqp"] and (k["sqp"]["search_volume"] or 0) > 0)
        if proven and len(plan["TITLE"]) < title_slots: plan["TITLE"].append(k["term"])
        elif proven and len(plan["HIGHLIGHTS_BULLETS"]) < highlight_slots: plan["HIGHLIGHTS_BULLETS"].append(k["term"])
        elif k["sources"] == ["SEED_VOCAB"]: plan["BACKEND"].append(k["term"]); plan["RESEARCH_MORE"].append(k["term"])
        else: plan["BACKEND"].append(k["term"])
    evidence = sum(1 for k in uni if k["sources"] != ["SEED_VOCAB"])
    return {"nut": nut, "plan": plan, "terms_considered": len(uni), "terms_with_evidence": evidence,
            "rule_ids": ["AMZ-T-01", "AMZ-T-02", "AMZ-K-02", "AMZ-K-03", "AMZ-Q-02"],
            "note": ("Saboot-wale terms kam hain — plan zyadatar shabdkosh par hai; Ads/SQP data aate hi khud sudhrega"
                     if evidence < 3 else "Plan asal data (Ads + SQP) par bana hai")}
