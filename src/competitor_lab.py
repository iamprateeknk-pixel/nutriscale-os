"""Competitor Lab (CMP-01..04 + CP-01..05 decision packets) — flagship.
Niyam: competitor ka price/rating/content sirf DATED snapshot se; na mile to 'unknown'.
Grade barabar na ho (W240 ≠ W320) to STRICT peer kabhi nahi. Paisa ka faisla margin gate se.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc
import finance as F

def price_per_100g(price: float, pack_g: float) -> float:
    return round(price / pack_g * 100, 2) if pack_g else None

def classify_peer(own: dict, peer: dict) -> dict:
    """own/peer: {nut_type, grade, pack_g, processing}"""
    reasons = []
    if own["nut_type"] != peer["nut_type"]: return {"class": "NOT_COMPARABLE", "reasons": ["Phal/giri hi alag hai"]}
    grade_same = (own.get("grade") or "") == (peer.get("grade") or "")
    pack_same = abs((own.get("pack_g") or 0) - (peer.get("pack_g") or 0)) < 1
    proc_same = (own.get("processing") or "raw") == (peer.get("processing") or "raw")
    if grade_same and pack_same and proc_same:
        return {"class": "STRICT", "reasons": ["Grade, pack, processing — teeno barabar"]}
    if not grade_same: reasons.append(f"Grade alag hai ({own.get('grade')} vs {peer.get('grade')}) — exact match NAHI")
    if not pack_same: reasons.append(f"Pack alag ({own.get('pack_g')}g vs {peer.get('pack_g')}g) — ₹/100g se tulna hogi")
    if not proc_same: reasons.append("Processing alag (raw/roasted/salted)")
    if grade_same and proc_same: return {"class": "NEAR", "reasons": reasons}
    return {"class": "ALTERNATIVE", "reasons": reasons + ["Sirf disha ke liye — seedhi tulna nahi"]}

def add_peer(db, platform, peer_ref, url, title, nut_type, grade, pack_g, processing="raw",
             source="manual-verified-url", added_by="owner") -> int:
    ensure_v12(db)
    cur = db.execute("INSERT INTO peer_products(platform,peer_ref,url,title,nut_type,grade,pack_g,processing,source,added_by,added_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (platform, peer_ref, url, title, nut_type, grade, pack_g, processing, source, added_by, now_utc()))
    db.commit(); return cur.lastrowid

def add_snapshot(db, peer_id, price=None, mrp=None, coupon=None, rating=None, reviews=None,
                 image_count=None, in_stock=None, delivery_days=None, title=None,
                 source="manual-observation", capture_id=None) -> int:
    ensure_v12(db)
    capture_id = capture_id or f"cap-{peer_id}-{now_utc()}"
    cur = db.execute("""INSERT OR IGNORE INTO peer_snapshots(peer_id,captured_at,price,mrp,coupon,rating,reviews,image_count,in_stock,delivery_days,title,source,capture_id)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (peer_id, now_utc(), price, mrp, coupon, rating, reviews, image_count,
                      in_stock, delivery_days, title, source, capture_id))
    db.commit(); return cur.lastrowid

def detect_changes(db, peer_id) -> list:
    """CMP-02: aakhiri do snapshots ka farq. Koi value missing (None) ho to us par event NAHI banega —
    'data nahi aaya' ko 'badlav ho gaya' kabhi nahi likhenge."""
    rows = [dict(r) for r in db.execute("SELECT * FROM peer_snapshots WHERE peer_id=? ORDER BY captured_at DESC, id DESC LIMIT 2", (peer_id,))]
    if len(rows) < 2: return []
    new, old = rows[0], rows[1]
    events = []
    for field, label in [("price", "Price"), ("rating", "Rating"), ("image_count", "Images"), ("in_stock", "Stock"), ("title", "Title")]:
        a, b = new.get(field), old.get(field)
        if a is None or b is None or a == b: continue
        delta = (a - b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None
        events.append({"peer_id": peer_id, "change_type": label, "before": b, "after": a,
                       "delta": delta, "before_at": old["captured_at"], "after_at": new["captured_at"],
                       "source": new["source"], "capture_id": new["capture_id"]})
    return events

def decision_packet(db, own_product: dict, peer_id: int) -> dict:
    """Section 10A: saboot → farq → parikalpana (hypothesis) → margin guardrail → tajurba (experiment).
    Price ghataane ki sifarish tabhi jab cost pata ho aur floor na toote (CP-01)."""
    peer = db.execute("SELECT * FROM peer_products WHERE id=?", (peer_id,)).fetchone()
    snap = db.execute("SELECT * FROM peer_snapshots WHERE peer_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (peer_id,)).fetchone()
    if not peer or not snap:
        return {"status": "INSUFFICIENT_EVIDENCE", "note": "Peer ya uska taaza snapshot nahi hai — packet nahi banega"}
    peer, snap = dict(peer), dict(snap)
    own_facts = {"nut_type": own_product.get("nut_type", ""), "grade": own_product.get("grade", ""),
                 "pack_g": own_product.get("pack_g", 200), "processing": own_product.get("processing", "raw")}
    cls = classify_peer(own_facts, peer)
    own_p100 = price_per_100g(own_product["price"], own_facts["pack_g"])
    peer_p100 = price_per_100g(snap["price"], peer["pack_g"]) if snap["price"] else None
    gap_pct = round((own_p100 - peer_p100) / peer_p100 * 100, 1) if peer_p100 else None
    fin = F.contribution_v2(db, own_product["sku"], own_product["price"], own_product.get("platform", "Amazon"))
    playbook, action = "CP-02", "Pehle content/keyword gap ki jaanch — price ko haath mat lagao"
    if gap_pct is not None and gap_pct > 5 and cls["class"] in ("STRICT", "NEAR"):
        if fin["known"] and fin["margin_pct"] > 15:
            playbook, action = "CP-01", "Peer sasta hai aur margin me gunjaish hai — coupon ka chhota tajurba chal sakta hai (price cut nahi)"
        elif fin["known"]:
            playbook, action = "CP-01", "Peer sasta hai par margin patla hai — price/coupon NAHI; grade/size ke saboot wali image se value samjhao"
        else:
            playbook, action = "CP-01", "Peer sasta hai par apni cost hi nahi pata — pehle cost darj karo, tab tak price par koi faisla nahi"
    if snap["in_stock"] == 0:
        playbook, action = "CP-05", "Peer stock-out dikh raha hai (is samay/ilaake me) — apna stock pakka karke hi ads badhao"
    return {"status": "OK", "own": own_product["name"], "peer": peer["title"], "match": cls,
            "gap": {"own_per_100g": own_p100, "peer_per_100g": peer_p100, "gap_pct": gap_pct,
                    "peer_rating": snap["rating"], "peer_reviews": snap["reviews"],
                    "peer_images": snap["image_count"], "observed_at": snap["captured_at"], "source": snap["source"]},
            "financial_guardrail": {"cost_known": fin["known"], "margin_pct": fin.get("margin_pct"),
                                    "scale_allowed": fin.get("scale_allowed")},
            "playbook": playbook, "recommended_action": action,
            "hypothesis_class": "HYPOTHESIS",
            "experiment": {"primary_metric": "CVR", "duration_days": 14,
                           "stop_rule": "Margin floor toote ya stock 7 din se kam bache to tajurba band"},
            "do_not_claim": "Competitor ki sales/ads kharch/rank ka koi dawa nahi — sirf dated observation hai"}
