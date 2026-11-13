"""Competitor Lab (CMP-01..04 + CP-01..05 decision packets) — flagship.
Rule: competitor price/rating/content only from DATED snapshots; otherwise 'unknown'.
If grades differ (W240 ≠ W320) it is never a STRICT peer. Money decisions go through the margin gate.
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
    if own["nut_type"] != peer["nut_type"]: return {"class": "NOT_COMPARABLE", "reasons": ["Different fruit/nut altogether"]}
    grade_same = (own.get("grade") or "") == (peer.get("grade") or "")
    pack_same = abs((own.get("pack_g") or 0) - (peer.get("pack_g") or 0)) < 1
    proc_same = (own.get("processing") or "raw") == (peer.get("processing") or "raw")
    if grade_same and pack_same and proc_same:
        return {"class": "STRICT", "reasons": ["Grade, pack, processing — all three match"]}
    if not grade_same: reasons.append(f"Different grade ({own.get('grade')} vs {peer.get('grade')}) — NOT an exact match")
    if not pack_same: reasons.append(f"Different pack ({own.get('pack_g')}g vs {peer.get('pack_g')}g) — compare per ₹/100g")
    if not proc_same: reasons.append("Processing alag (raw/roasted/salted)")
    if grade_same and proc_same: return {"class": "NEAR", "reasons": reasons}
    return {"class": "ALTERNATIVE", "reasons": reasons + ["Directional only — not a direct comparison"]}

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
    """CMP-02: difference between the last two snapshots. A missing value (None) never creates an event —
    'data did not arrive' is never reported as 'something changed'."""
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
    """Section 10A: evidence → gap → hypothesis → margin guardrail → experiment.
    A price-cut recommendation only when cost is known and the floor holds (CP-01)."""
    peer = db.execute("SELECT * FROM peer_products WHERE id=?", (peer_id,)).fetchone()
    snap = db.execute("SELECT * FROM peer_snapshots WHERE peer_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (peer_id,)).fetchone()
    if not peer or not snap:
        return {"status": "INSUFFICIENT_EVIDENCE", "note": "No peer or no fresh snapshot — no packet is built"}
    peer, snap = dict(peer), dict(snap)
    own_facts = {"nut_type": own_product.get("nut_type", ""), "grade": own_product.get("grade", ""),
                 "pack_g": own_product.get("pack_g", 200), "processing": own_product.get("processing", "raw")}
    cls = classify_peer(own_facts, peer)
    own_p100 = price_per_100g(own_product["price"], own_facts["pack_g"])
    peer_p100 = price_per_100g(snap["price"], peer["pack_g"]) if snap["price"] else None
    gap_pct = round((own_p100 - peer_p100) / peer_p100 * 100, 1) if peer_p100 else None
    fin = F.contribution_v2(db, own_product["sku"], own_product["price"], own_product.get("platform", "Amazon"))
    playbook, action = "CP-02", "Check content/keyword gaps first — do not touch price"
    if gap_pct is not None and gap_pct > 5 and cls["class"] in ("STRICT", "NEAR"):
        if fin["known"] and fin["margin_pct"] > 15:
            playbook, action = "CP-01", "Peer is cheaper and there is margin headroom — a small coupon experiment is possible (not a price cut)"
        elif fin["known"]:
            playbook, action = "CP-01", "Peer is cheaper but margin is thin — NO price/coupon; explain value with grade/size proof images"
        else:
            playbook, action = "CP-01", "Peer is cheaper but your own cost is unknown — record cost first; no price decision until then"
    if snap["in_stock"] == 0:
        playbook, action = "CP-05", "Peer appears out of stock (at this time/location) — secure your own stock before raising ads"
    return {"status": "OK", "own": own_product["name"], "peer": peer["title"], "match": cls,
            "gap": {"own_per_100g": own_p100, "peer_per_100g": peer_p100, "gap_pct": gap_pct,
                    "peer_rating": snap["rating"], "peer_reviews": snap["reviews"],
                    "peer_images": snap["image_count"], "observed_at": snap["captured_at"], "source": snap["source"]},
            "financial_guardrail": {"cost_known": fin["known"], "margin_pct": fin.get("margin_pct"),
                                    "scale_allowed": fin.get("scale_allowed")},
            "playbook": playbook, "recommended_action": action,
            "hypothesis_class": "HYPOTHESIS",
            "experiment": {"primary_metric": "CVR", "duration_days": 14,
                           "stop_rule": "Stop the experiment if the margin floor breaks or stock drops below 7 days"},
            "do_not_claim": "No claims about competitor sales/ad spend/rank — dated observations only"}
