"""Keyword Intelligence (V23) — where each keyword belongs and what to fix for each query.

Three sources, each labelled with its evidence:
  OBSERVED_ADS  = your own Ads search-term report (clicks/orders/spend — real)
  BRAND_ANALYTICS = SQP report (market-share funnel — Amazon's own data)
  SEED_VOCAB    = the marketplace_knowledge vocabulary (Hinglish/grade/pack) — seeds only, volume UNKNOWN
Search volume is never estimated (rule KWD-01).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12
import marketplace_knowledge as MK
from keyword_lab import normalize_term, EXCLUDE_INTENT

def _share(brand, total):
    return round(brand / total, 4) if total else None

def sqp_funnel(db, platform: str = "Amazon", min_impressions: float = 50) -> dict:
    """AMZ-Q-01..03: impression→click→cart→purchase share per query, and the step where it drops."""
    ensure_v12(db)
    rows = db.execute("""SELECT query, SUM(search_volume) sv, SUM(impressions) im, SUM(brand_impressions) bim,
                                SUM(clicks) cl, SUM(brand_clicks) bcl, SUM(cart_adds) ca, SUM(brand_cart_adds) bca,
                                SUM(purchases) pu, SUM(brand_purchases) bpu,
                                MIN(period_start) ps, MAX(period_end) pe
                         FROM brand_analytics WHERE report_type='SQP' AND platform=? AND query IS NOT NULL AND query<>''
                         GROUP BY query""", (platform,)).fetchall()
    if not rows:
        return {"available": False, "queries": [],
                "note": "No SQP data — export Seller Central > Brand Analytics > Search Query Performance and upload it "
                        "(or drop it in data/brand_analytics_inbox/ — auto-imported daily at 06:45)"}
    low_imp = MK.rule("AMZ-Q-03")["value"]["low_impr_share"]
    out = []
    for r in rows:
        if (r["im"] or 0) < min_impressions: continue
        s = {"impression": _share(r["bim"] or 0, r["im"]), "click": _share(r["bcl"] or 0, r["cl"]),
             "cart": _share(r["bca"] or 0, r["ca"]), "purchase": _share(r["bpu"] or 0, r["pu"])}
        diag, action, rid, prio = "HEALTHY", "Maintain share; watch the weekly trend", "AMZ-Q-01", 3
        imp, clk, pur = s["impression"] or 0, s["click"], s["purchase"]
        if pur is not None and imp and pur > imp and imp < low_imp:
            diag, rid, prio = "SCALE_OPPORTUNITY", "AMZ-Q-03", 1
            action = "Converts but is not seen — after checking margin, raise ads/bids on this query and lock it into title/backend"
        elif imp < 0.01:
            diag, rid, prio = "NOT_VISIBLE", "AMZ-Q-02", 2
            action = "Relevance/visibility gap — put the keyword in the title or backend, run an exact-match ad"
        elif clk is not None and clk < imp * 0.6:
            diag, rid, prio = "TILE_PROBLEM", "AMZ-Q-02", 1
            action = "Seen but not clicked — improve the main image, first 40 characters of the title, price/per-100g, reviews/badge"
        elif pur is not None and clk and pur < clk * 0.6:
            diag, rid, prio = "OFFER_PROBLEM", "AMZ-Q-02", 1
            action = "Clicked but not bought — check price, A+ content, reviews, delivery speed, pack-size options"
        out.append({"query": r["query"], "search_volume": r["sv"], "shares": s, "diagnosis": diag,
                    "action": action, "rule_id": rid, "priority": prio,
                    "period": f"{r['ps']}..{r['pe']}", "evidence": "BRAND_ANALYTICS (Amazon SQP)"})
    out.sort(key=lambda x: (x["priority"], -(x["search_volume"] or 0)))
    counts = {}
    for q in out: counts[q["diagnosis"]] = counts.get(q["diagnosis"], 0) + 1
    return {"available": True, "queries": out, "diagnosis_counts": counts,
            "note": "Share = your part / the whole market; fix the funnel step where it drops (AMZ-Q-02)"}

def seed_terms(nut: str, grade: str = None, weight: str = None) -> list:
    """Seed words from the vocabulary — volume UNKNOWN, only a direction for backend/research.
    If grade/weight are given, ONLY that variant — putting W180/W320 or another pack size in a W240 cashew
    backend would be wrong-variant terms (misleads shoppers; Amazon bans irrelevant terms)."""
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
    """All three sources in one list — each term with its evidence and a usefulness score."""
    db = store.db; ensure_v12(db)
    terms = {}
    def get(t):
        # Keyed by raw term — 'badam' and 'almond' are different words (both are needed in the backend); normalized is informational only
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
        if e["sources"] == {"SEED_VOCAB"}: score = 1.0  # seed only — stays low until evidence arrives
        wasted = e["spend"] >= 200 and e["orders"] == 0
        out.append({"term": e["term"], "normalized": e["normalized"], "sources": sorted(e["sources"]),
                    "clicks": e["clicks"], "orders": e["orders"], "cvr_pct": round(cvr * 100, 1) if cvr is not None else None,
                    "spend": round(e["spend"], 2), "sales": round(e["sales"], 2), "sqp": e["sqp"],
                    "excluded": excluded, "wasted_spend": wasted,
                    "score": 0 if excluded else round(score, 1),
                    "search_volume_status": "BRAND_ANALYTICS" if e["sqp"] else "UNKNOWN (no estimate)"})
    return sorted(out, key=lambda x: -x["score"])

def placement_plan(store, nut: str, title_slots: int = 1, highlight_slots: int = 4, platform: str = "Amazon",
                   grade: str = None, weight: str = None) -> dict:
    """Which keyword goes where: TITLE (the 1 with most evidence) → ITEM_HIGHLIGHTS/BULLETS → BACKEND (variants, Hinglish) → NEGATIVE."""
    uni = keyword_universe(store, nut, platform, grade, weight)
    plan = {"TITLE": [], "HIGHLIGHTS_BULLETS": [], "BACKEND": [], "NEGATIVE_ADS": [], "RESEARCH_MORE": []}
    for k in uni:
        if k["excluded"] or k["wasted_spend"]:
            plan["NEGATIVE_ADS"].append({"term": k["term"], "why": "wrong intent" if k["excluded"] else f"₹{k['spend']} spent, 0 orders"})
            continue
        proven = k["orders"] >= 3 or (k["sqp"] and (k["sqp"]["search_volume"] or 0) > 0)
        if proven and len(plan["TITLE"]) < title_slots: plan["TITLE"].append(k["term"])
        elif proven and len(plan["HIGHLIGHTS_BULLETS"]) < highlight_slots: plan["HIGHLIGHTS_BULLETS"].append(k["term"])
        elif k["sources"] == ["SEED_VOCAB"]: plan["BACKEND"].append(k["term"]); plan["RESEARCH_MORE"].append(k["term"])
        else: plan["BACKEND"].append(k["term"])
    evidence = sum(1 for k in uni if k["sources"] != ["SEED_VOCAB"])
    return {"nut": nut, "plan": plan, "terms_considered": len(uni), "terms_with_evidence": evidence,
            "rule_ids": ["AMZ-T-01", "AMZ-T-02", "AMZ-K-02", "AMZ-K-03", "AMZ-Q-02"],
            "note": ("Few evidence-backed terms — the plan is mostly vocabulary-based; it improves automatically once Ads/SQP data arrives"
                     if evidence < 3 else "Plan is based on real data (Ads + SQP)")}
