"""Listing V2 (LST-01/02/04) — versioned score, content audit, listing versions.
Score v2 'Amazon ka ranking formula' NAHI hai — ye kharidaar + policy ki quality ka map hai,
weights version ke saath darj hain taaki kal badlein to purana hisaab bhi samajh aaye.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc
import fact_registry as FR

WEIGHTS_V2 = {"keyword_fit": 20, "title_readability": 10, "attributes_complete": 15,
              "images": 15, "bullets_value": 10, "reviews_trust": 10, "price_grade_context": 10,
              "fulfillment": 5, "compliance": 5}
VERSION = "listing-score-v2.0"

def score_v2(listing: dict, facts_verified: bool = True) -> dict:
    """listing keys: title, keywords_in_title, title_len, attributes_filled(0-1), image_count,
    has_size_proof, bullets, rating, review_count, price_per_100g, peer_median_per_100g, fba(bool)"""
    parts = {}
    parts["keyword_fit"] = min(listing.get("keywords_in_title", 0) / 5, 1) * WEIGHTS_V2["keyword_fit"]
    tl = listing.get("title_len", 0)
    parts["title_readability"] = (1.0 if 80 <= tl <= 200 else 0.5) * WEIGHTS_V2["title_readability"]
    parts["attributes_complete"] = listing.get("attributes_filled", 0) * WEIGHTS_V2["attributes_complete"]
    img = listing.get("image_count", 0)
    parts["images"] = (min(img / 7, 1) * 0.7 + (0.3 if listing.get("has_size_proof") else 0)) * WEIGHTS_V2["images"]
    parts["bullets_value"] = min(listing.get("bullets", 0) / 5, 1) * WEIGHTS_V2["bullets_value"]
    parts["reviews_trust"] = (min(listing.get("rating", 0) / 5, 1) * 0.6 +
                               min(listing.get("review_count", 0) / 100, 1) * 0.4) * WEIGHTS_V2["reviews_trust"]
    own, med = listing.get("price_per_100g"), listing.get("peer_median_per_100g")
    parts["price_grade_context"] = (0.6 if not med else max(0.0, 1 - abs(own - med) / med)) * WEIGHTS_V2["price_grade_context"]
    parts["fulfillment"] = WEIGHTS_V2["fulfillment"] if listing.get("fba") else WEIGHTS_V2["fulfillment"] * 0.4
    parts["compliance"] = WEIGHTS_V2["compliance"] if facts_verified else 0
    total = round(sum(parts.values()), 1)
    return {"version": VERSION, "score": total, "breakdown": {k: round(v, 1) for k, v in parts.items()},
            "note": "Ye NutriScale ka quality score hai — Amazon/Flipkart ke ranking formula ka dawa NAHI hai"}

def content_audit(own: dict, peer_titles: list) -> dict:
    """LST-02: peers ke titles me jo tathya/keywords dikhte hain aur apne me nahi — wahi gap.
    Dhyaan: peer ke dawe apne product ke liye saboot nahi bante — sirf jaanch ki disha hai."""
    own_t = (own.get("title") or "").lower()
    checks = {"grade": ["w240", "w320", "mamra", "california", "a++"], "pack": ["200g", "500g", "1kg", "250g"],
              "use": ["snacking", "gifting", "baking", "trail mix"], "form": ["raw", "roasted", "salted", "unsweetened", "dried"]}
    gaps = []
    for cat, words in checks.items():
        peer_has = [w for w in words if any(w in (t or "").lower() for t in peer_titles)]
        for w in peer_has:
            if w not in own_t: gaps.append({"category": cat, "missing": w, "seen_in_peers": True})
    return {"gaps": gaps, "note": "Gap matlab sirf 'jaanch karo' — pehle apne product ka tathya pakka karo, phir copy me daalo"}

def save_draft(db, sku, platform, title, bullets: list, backend_terms: str, created_by: str) -> dict:
    ensure_v12(db)
    last = db.execute("SELECT COALESCE(MAX(version),0) v FROM listing_versions WHERE sku=? AND platform=?", (sku, platform)).fetchone()["v"]
    cur = db.execute("INSERT INTO listing_versions(sku,platform,version,title,bullets,backend_terms,status,created_by,created_at) VALUES (?,?,?,?,?,?, 'DRAFT',?,?)",
                     (sku, platform, last + 1, title, json.dumps(bullets), backend_terms, created_by, now_utc()))
    db.commit(); return {"id": cur.lastrowid, "version": last + 1, "status": "DRAFT"}

def approve_version(db, vid: int, approver: str) -> dict:
    ensure_v12(db)
    r = db.execute("SELECT * FROM listing_versions WHERE id=?", (vid,)).fetchone()
    if not r: return {"ok": False, "error": "Version mila nahi"}
    chk = FR.check_copy(db, r["sku"], (r["title"] or "") + " " + " ".join(json.loads(r["bullets"] or "[]")))
    if not chk["can_publish"]:
        return {"ok": False, "status": "NEEDS_EVIDENCE", "needs_evidence": chk["needs_evidence"],
                "error": "Dawo ke saboot nahi — publish/approve roka gaya (POL-01)"}
    db.execute("UPDATE listing_versions SET status='APPROVED', approved_by=? WHERE id=?", (approver, vid)); db.commit()
    return {"ok": True, "status": "APPROVED", "claim_check": chk}

def rollback_to(db, sku, platform, version, by) -> dict:
    """LST-04: purana version naya DRAFT bankar wapas — itihaas kabhi mita nahi."""
    ensure_v12(db)
    r = db.execute("SELECT * FROM listing_versions WHERE sku=? AND platform=? AND version=?", (sku, platform, version)).fetchone()
    if not r: return {"ok": False, "error": "Woh version mila nahi"}
    return save_draft(db, sku, platform, r["title"], json.loads(r["bullets"] or "[]"), r["backend_terms"], by)
