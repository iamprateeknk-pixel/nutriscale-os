"""Keyword Lab (KWD-01..04) — imaandaar keyword vigyaan.
QA-09 / KWD-01 ka pakka niyam: search volume ka koi source na ho to 'unknown' —
purana `clicks * 20` wala andaaz HATA diya gaya hai (woh Amazon ka volume nahi tha).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

# Hinglish/transliteration jode — ek hi irada, kai roop
SYNONYMS = {"badam": "almond", "almonds": "almond", "kaju": "cashew", "cashews": "cashew",
            "anjeer": "fig", "figs": "fig", "kishmish": "raisin", "raisins": "raisin",
            "akhrot": "walnut", "walnuts": "walnut", "pista": "pistachio", "khajoor": "dates"}
EXCLUDE_INTENT = ["wholesale", "bulk rate", "mandi", "b2b", "job", "recipe video"]

def normalize_term(term: str) -> str:
    words = [SYNONYMS.get(w, w) for w in term.lower().split()]
    return " ".join(words)

def term_variants(term: str) -> list:
    base = term.lower().strip()
    out = {base, normalize_term(base)}
    for k, v in SYNONYMS.items():
        if v in base: out.add(base.replace(v, k))
        if k in base: out.add(base.replace(k, v))
    return sorted(out)

def opportunity_matrix(store, intel=None) -> list:
    """KWD-03: har term ka score sirf SABOOT par — apne clicks/orders (observed),
    SKU fit, margin gate; volume sirf licensed provider se, warna null."""
    rows = []
    for r in store.db.execute("""SELECT term, SUM(clicks) cl, SUM(purchases) pu, SUM(spend) sp, SUM(sales) sa
                                 FROM search_terms GROUP BY term"""):
        t = dict(r)
        excluded = any(x in t["term"].lower() for x in EXCLUDE_INTENT)
        cvr = (t["pu"] / t["cl"]) if t["cl"] else 0
        vol = intel.keyword_volume(t["term"]) if intel else {"status": "UNAVAILABLE", "volume": None}
        score = round(min(cvr * 400, 40) + min(t["pu"] * 5, 30) + (15 if t["sa"] > t["sp"] else 0), 1)
        rows.append({"term": t["term"], "normalized": normalize_term(t["term"]),
                     "clicks": t["cl"], "orders": t["pu"], "cvr_pct": round(cvr * 100, 1),
                     "roas": round(t["sa"] / t["sp"], 2) if t["sp"] else None,
                     "search_volume": vol["volume"], "volume_status": vol["status"],
                     "excluded": excluded, "opportunity_score": 0 if excluded else score,
                     "evidence": "Observed (apne Ads search-term report se); volume: " + vol["status"]})
    return sorted(rows, key=lambda x: -x["opportunity_score"])

def record_rank(db, platform, term, sku, position, rank_type="ORGANIC", page=1,
                locale="IN", device="mobile", source="manual-observation"):
    ensure_v12(db)
    db.execute("INSERT INTO rank_observations(platform,term,sku,rank_type,position,page,locale,device,source,captured_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
               (platform, term, sku, rank_type, position, page, locale, device, source, now_utc())); db.commit()

def rank_diagnostic(store, term: str, sku: str) -> dict:
    """RNK-02: rank girne par pehle sabse aam kaaran parkho — seedha title ko dosh nahi.
    Har parikalpana (hypothesis) ke saath saboot; kaaran pakka kabhi nahi likhenge."""
    db = store.db; ensure_v12(db)
    trend = rank_trend(db, term, sku)
    hyps = []
    qty = db.execute("SELECT COALESCE(SUM(qty),0) q FROM inventory WHERE sku=?", (sku,)).fetchone()["q"]
    if qty <= 0:
        hyps.append({"rank": 1, "hypothesis": "Stock khatm — bina stock ke rank girna aam hai",
                     "evidence": f"inventory qty = {qty}", "action": "Pehle stock bharo, phir rank napo"})
    prod = db.execute("SELECT rating, reviews FROM products WHERE sku=?", (sku,)).fetchone()
    if prod and (prod["rating"] or 0) < 4.0:
        hyps.append({"rank": 2, "hypothesis": "Rating kamzor — kharidaar ka bharosa aur conversion dono dabte hain",
                     "evidence": f"rating {prod['rating']} ({prod['reviews']} reviews)", "action": "Review-agent ki shikayat mining dekho"})
    st = db.execute("SELECT COALESCE(SUM(spend),0) sp, COALESCE(SUM(clicks),0) cl FROM search_terms WHERE term=?", (term,)).fetchone()
    if st and st["cl"] and st["sp"] == 0:
        hyps.append({"rank": 3, "hypothesis": "Is term par ads ka sahara band hai", "evidence": "clicks hain par spend 0",
                     "action": "Ads Studio me is term ka harvest/bid parkho"})
    if qty > 0 and not hyps:
        hyps.append({"rank": 1, "hypothesis": "Stock/rating/ads teeno theek — mausam/mang ya pratiyogita ka asar ho sakta hai",
                     "evidence": "buniyadi checks saaf", "action": "3 aur rank points jodo, phir tajurba (experiment) banao"})
    return {"term": term, "sku": sku, "trend": trend, "hypotheses": hyps,
            "class": "HYPOTHESIS", "note": "Ye disha-suchak hain, siddh kaaran nahi — tajurbe se hi pakka hoga"}

def rank_funnel(store, term: str, sku: str) -> dict:
    """RNK-03: query -> apne clicks/orders (observed) -> SKU contribution (cost pata ho tab)."""
    import finance as F
    db = store.db
    r = db.execute("""SELECT COALESCE(SUM(clicks),0) cl, COALESCE(SUM(purchases),0) pu,
                      COALESCE(SUM(spend),0) sp, COALESCE(SUM(sales),0) sa
                      FROM search_terms WHERE term=?""", (term,)).fetchone()
    prod = db.execute("SELECT price FROM products WHERE sku=?", (sku,)).fetchone()
    fin = F.contribution_v2(db, sku, prod["price"]) if prod else {"known": False, "reason": "product catalog me nahi"}
    return {"term": term, "clicks": r["cl"], "orders": r["pu"],
            "cvr_pct": round(r["pu"] / r["cl"] * 100, 1) if r["cl"] else None,
            "ad_spend": r["sp"], "attributed_sales": r["sa"],
            "contribution": fin, "rank_data": "Rank provider bina rank ka hissa UNAVAILABLE hai",
            "coverage": "Sirf apne Ads search-term data par — kul khoj-mang ka dawa nahi"}


def rank_trend(db, term, sku, rank_type="ORGANIC") -> dict:
    """RNK-01/04: rank ka record scope ke saath; alert ke liye kam se kam 3 tulna-yogya points."""
    rows = [dict(r) for r in db.execute("""SELECT * FROM rank_observations WHERE term=? AND sku=? AND rank_type=?
                                           ORDER BY captured_at""", (term, sku, rank_type))]
    if len(rows) < 3:
        return {"term": term, "points": len(rows), "status": "INSUFFICIENT_DATA",
                "note": "Rank alert ke liye kam se kam 3 observations chahiye — ek point se natija nikaalna mana hai"}
    first, last = rows[0]["position"], rows[-1]["position"]
    return {"term": term, "points": len(rows), "status": "OK", "first": first, "latest": last,
            "delta": first - last, "direction": "UP" if last < first else "DOWN" if last > first else "FLAT",
            "scope": {"locale": rows[-1]["locale"], "device": rows[-1]["device"], "source": rows[-1]["source"]},
            "history": rows}
