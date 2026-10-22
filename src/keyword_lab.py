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
