"""Listing V2 (LST-01/02/04) — versioned score, content audit, listing versions.
Score v2 is NOT 'Amazon's ranking formula' — it maps buyer + policy quality;
weights are recorded with a version so the old calculation still makes sense if they change later.
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
            "note": "This is NutriScale's quality score — NOT a claim about the Amazon/Flipkart ranking formula"}

def content_audit(own: dict, peer_titles: list) -> dict:
    """LST-02: facts/keywords visible in peers' titles but missing in yours — that is the gap.
    Caution: a peer's claims are not evidence for your product — they only point at what to check."""
    own_t = (own.get("title") or "").lower()
    checks = {"grade": ["w240", "w320", "mamra", "california", "a++"], "pack": ["200g", "500g", "1kg", "250g"],
              "use": ["snacking", "gifting", "baking", "trail mix"], "form": ["raw", "roasted", "salted", "unsweetened", "dried"]}
    gaps = []
    for cat, words in checks.items():
        peer_has = [w for w in words if any(w in (t or "").lower() for t in peer_titles)]
        for w in peer_has:
            if w not in own_t: gaps.append({"category": cat, "missing": w, "seen_in_peers": True})
    return {"gaps": gaps, "note": "A gap only means 'check this' — confirm the fact for your own product first, then add it to the copy"}

def save_draft(db, sku, platform, title, bullets: list, backend_terms: str, created_by: str) -> dict:
    ensure_v12(db)
    last = db.execute("SELECT COALESCE(MAX(version),0) v FROM listing_versions WHERE sku=? AND platform=?", (sku, platform)).fetchone()["v"]
    cur = db.execute("INSERT INTO listing_versions(sku,platform,version,title,bullets,backend_terms,status,created_by,created_at) VALUES (?,?,?,?,?,?, 'DRAFT',?,?)",
                     (sku, platform, last + 1, title, json.dumps(bullets), backend_terms, created_by, now_utc()))
    db.commit(); return {"id": cur.lastrowid, "version": last + 1, "status": "DRAFT"}

def approve_version(db, vid: int, approver: str) -> dict:
    ensure_v12(db)
    r = db.execute("SELECT * FROM listing_versions WHERE id=?", (vid,)).fetchone()
    if not r: return {"ok": False, "error": "Version not found"}
    chk = FR.check_copy(db, r["sku"], (r["title"] or "") + " " + " ".join(json.loads(r["bullets"] or "[]")))
    if not chk["can_publish"]:
        return {"ok": False, "status": "NEEDS_EVIDENCE", "needs_evidence": chk["needs_evidence"],
                "error": "No evidence for the claims — publish/approve blocked (POL-01)"}
    db.execute("UPDATE listing_versions SET status='APPROVED', approved_by=? WHERE id=?", (approver, vid)); db.commit()
    return {"ok": True, "status": "APPROVED", "claim_check": chk}

def publish(db, vid: int, product_type: str, sp=None, live: bool = False) -> dict:
    """LST publish path (V13): only an APPROVED version goes out; VALIDATION_PREVIEW (check) first,
    live only when the write_listings capability is certified. Amazon's issues are recorded as returned."""
    import capabilities as caps
    ensure_v12(db)
    r = db.execute("SELECT * FROM listing_versions WHERE id=?", (vid,)).fetchone()
    if not r: return {"ok": False, "error": "Version not found"}
    if r["status"] != "APPROVED":
        return {"ok": False, "error": f"Version is {r['status']} — it must be approved before publishing"}
    if r["platform"] != "Amazon":
        return {"ok": False, "error": "Publishing currently only supports Amazon (SP-API Listings); Flipkart listings go via CSV/portal"}
    bullets = json.loads(r["bullets"] or "[]")
    attributes = {"item_name": [{"value": r["title"], "marketplace_id": "A21TJRUUN4KGV"}],
                  "bullet_point": [{"value": b, "marketplace_id": "A21TJRUUN4KGV"} for b in bullets]}
    if live:
        c = caps.capability(db, "Amazon", "write_listings")
        if c["status"] != "certified":
            return {"ok": False, "error": f"Live publish is off — the write_listings capability is '{c['status']}'. Run VALIDATION_PREVIEW first, then certify it via pilot sign-off."}
    if sp is None:
        from connectors.amazon_sp import AmazonSP
        sp = AmazonSP()
    mode = "NORMAL" if live else "VALIDATION_PREVIEW"
    resp = sp.put_listing(r["sku"], product_type, attributes, mode=mode)
    issues = resp.get("issues", []) if isinstance(resp, dict) else []
    if live and resp.get("status") == "ACCEPTED":
        db.execute("UPDATE listing_versions SET status='PUBLISHED' WHERE id=?", (vid,)); db.commit()
    return {"ok": True, "mode": mode, "submission": resp.get("submissionId"),
            "vendor_status": resp.get("status"), "issues": issues,
            "note": "Nothing went live in VALIDATION_PREVIEW — it is only Amazon's check" if not live else "Live publish sent"}

def rollback_to(db, sku, platform, version, by) -> dict:
    """LST-04: an old version comes back as a new DRAFT — history is never deleted."""
    ensure_v12(db)
    r = db.execute("SELECT * FROM listing_versions WHERE sku=? AND platform=? AND version=?", (sku, platform, version)).fetchone()
    if not r: return {"ok": False, "error": "That version was not found"}
    return save_draft(db, sku, platform, r["title"], json.loads(r["bullets"] or "[]"), r["backend_terms"], by)
