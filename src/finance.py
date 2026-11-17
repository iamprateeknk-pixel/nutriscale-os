"""FIN-01 Finance — versioned costs + contribution. Rules (QA-07):
an UNKNOWN cost is never treated as ZERO, and ad SCALE recommendations are blocked for that SKU.
An old cost (stale > 90 days) also blocks scaling, with a warning.
"""
import os, sys, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

STALE_DAYS = 90

MAX_GST_RATE = 40.0   # highest GST slab; anything above is a typo, not a rate

def ensure_gst(db):
    """V29: GST rate per cost version (percent, e.g. 5). NULL = not given (old rows keep working)."""
    ensure_v12(db)
    if "gst_rate" not in [c[1] for c in db.execute("PRAGMA table_info(cost_versions)")]:
        db.execute("ALTER TABLE cost_versions ADD COLUMN gst_rate REAL"); db.commit()

def check_gst_rate(rate):
    """None stays None (not given). Otherwise a number from 0 to 40 — raises ValueError for anything else."""
    if rate is None or (isinstance(rate, str) and rate.strip() == ""): return None
    r = float(str(rate).replace("%", "").strip())
    if not 0 <= r <= MAX_GST_RATE: raise ValueError(f"GST rate must be between 0 and {MAX_GST_RATE:.0f}% (got {rate})")
    return r

def set_cost(db, sku: str, cogs: float, packaging: float, other_variable: float = 0.0,
             source: str = "", approved_by: str = "", effective_from: str = None, gst_rate=None) -> dict:
    ensure_gst(db)
    gst_rate = check_gst_rate(gst_rate)
    eff = effective_from or datetime.date.today().isoformat()
    db.execute("INSERT INTO cost_versions(sku,effective_from,cogs,packaging,other_variable,source,approved_by,created_at,gst_rate) VALUES (?,?,?,?,?,?,?,?,?)",
               (sku, eff, cogs, packaging, other_variable, source, approved_by, now_utc(), gst_rate)); db.commit()
    return {"sku": sku, "unit_cost": cogs + packaging + other_variable, "effective_from": eff, "gst_rate": gst_rate}

def get_cost(db, sku: str, on_date: str = None) -> dict:
    ensure_gst(db)
    d = on_date or datetime.date.today().isoformat()
    r = db.execute("""SELECT * FROM cost_versions WHERE sku=? AND effective_from<=? ORDER BY effective_from DESC, id DESC LIMIT 1""",
                   (sku, d)).fetchone()
    if not r: return {"known": False, "reason": "No cost recorded for this SKU — scale recommendations are blocked", "sku": sku}
    age = (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(r["effective_from"])).days
    unit = r["cogs"] + r["packaging"] + r["other_variable"]
    return {"known": True, "sku": sku, "unit_cost": unit, "cogs": r["cogs"], "packaging": r["packaging"],
            "other_variable": r["other_variable"], "effective_from": r["effective_from"], "gst_rate": r["gst_rate"],
            "stale": age > STALE_DAYS, "age_days": age,
            "reason": "Cost is older than 90 days — enter a new cost; scaling blocked" if age > STALE_DAYS else "Cost is fresh"}

def _fee_event_id(platform: str, account: str, r: dict) -> str:
    """Stable event identity — the vendor transaction id if given, otherwise a content hash
    (the same event synced twice gets the same identity, so it is never double-counted)."""
    import hashlib
    if r.get("event_id"): return str(r["event_id"])
    basis = "|".join([platform, account, str(r.get("order_id")), str(r.get("sku")),
                      str(r.get("event_type") or "SHIPMENT"), str(r.get("posted_at") or ""),
                      f"{float(r.get('gross') or 0):.2f}", f"{float(r.get('fees') or 0):.2f}",
                      f"{float(r.get('refund') or 0):.2f}"])
    return "h:" + hashlib.sha1(basis.encode()).hexdigest()[:24]

def import_order_fees(db, rows: list, platform: str = "Amazon", seller_account: str = "default") -> dict:
    """SP Finances fees — V20: every financial EVENT is first recorded separately (order_fee_events),
    then order_fees becomes their SUM. The old INSERT OR REPLACE overwrote a second shipment event for the
    same order+SKU with the first one — now amounts add up instead of being erased.
    Each row may carry its own seller_account; otherwise the function's account is used."""
    ensure_v12(db); new_events, touched = 0, set()
    for r in rows:
        if not r.get("sku"): continue
        acct = str(r.get("seller_account") or seller_account)
        eid = _fee_event_id(platform, acct, r)
        cur = db.execute("""INSERT OR IGNORE INTO order_fee_events
                            (event_id,platform,seller_account,external_order_id,sku,event_type,gross,fees,refund,posted_at,imported_at)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                         (eid, platform, acct, r["order_id"], r["sku"], str(r.get("event_type") or "SHIPMENT"),
                          float(r.get("gross") or 0), float(r.get("fees") or 0), float(r.get("refund") or 0),
                          str(r.get("posted_at") or ""), now_utc()))
        if cur.rowcount: new_events += 1
        touched.add((platform, acct, r["order_id"], r["sku"]))
    for (pf, acct, oid, sku) in touched:
        agg = db.execute("""SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(fees),0) f, COALESCE(SUM(refund),0) rf
                            FROM order_fee_events WHERE platform=? AND seller_account=? AND external_order_id=? AND sku=?""",
                         (pf, acct, oid, sku)).fetchone()
        db.execute("INSERT OR REPLACE INTO order_fees VALUES (?,?,?,?,?,?,?)",
                   (pf, acct, oid, sku, agg["g"], agg["f"], agg["rf"]))
    db.commit()
    return {"imported": new_events, "events_total_seen": len(rows), "orders_updated": len(touched)}

def record_refunds(db, rows: list, platform: str = "Amazon", seller_account: str = "default") -> dict:
    """Refund amount in order_items.refund — revenue is always NET (gross - refund) (V15).
    V21 P0 FIX: each call used to SET (overwrite) the line refund — a second partial refund on the same line
    ERASED the first. Now every refund is first recorded in the refund_events LEDGER
    (event-id/content-hash identity, scope = platform+seller_account+order+line),
    and the line refund is the SUM of all its events — partial refunds ADD UP instead of being erased.
    Events with a line id go straight to that line; events without one are spread over the SKU total
    in proportion to gross (the V17 rule, but on the CUMULATIVE total, not per call)."""
    import hashlib
    ensure_v12(db); new_events, touched = 0, set()
    for r in rows:
        if not r.get("sku") and not r.get("line_id"): continue
        amt = float(r.get("refund") or 0)
        if amt <= 0: continue
        acct = str(r.get("seller_account") or seller_account)
        eid = str(r.get("event_id") or "h:" + hashlib.sha1("|".join([
            platform, acct, str(r.get("order_id")), str(r.get("line_id") or ""), str(r.get("sku") or ""),
            f"{amt:.2f}", str(r.get("posted_at") or "")]).encode()).hexdigest()[:24])
        cur = db.execute("""INSERT OR IGNORE INTO refund_events
                            (event_id,platform,seller_account,external_order_id,line_id,sku,amount,posted_at,imported_at)
                            VALUES (?,?,?,?,?,?,?,?,?)""",
                         (eid, platform, acct, r["order_id"], str(r.get("line_id") or ""), str(r.get("sku") or ""),
                          amt, str(r.get("posted_at") or ""), now_utc()))
        if cur.rowcount: new_events += 1
        touched.add((platform, acct, r["order_id"]))
    n = 0
    for (pf, acct, oid) in touched:
        # per-line sum of exact-line events
        exact = {row["line_id"]: row["s"] for row in db.execute(
            """SELECT line_id, SUM(amount) s FROM refund_events
               WHERE platform=? AND seller_account=? AND external_order_id=? AND line_id<>''
               GROUP BY line_id""", (pf, acct, oid))}
        # events without a line, per SKU total — spread in proportion to gross
        sku_totals = {row["sku"]: row["s"] for row in db.execute(
            """SELECT sku, SUM(amount) s FROM refund_events
               WHERE platform=? AND seller_account=? AND external_order_id=? AND line_id=''
               GROUP BY sku""", (pf, acct, oid))}
        lines = db.execute("""SELECT line_id, sku, gross FROM order_items
                              WHERE platform=? AND seller_account=? AND external_order_id=? ORDER BY gross DESC""",
                           (pf, acct, oid)).fetchall()
        by_sku = {}
        for l in lines: by_sku.setdefault(l["sku"], []).append(l)
        final = {l["line_id"]: float(exact.get(l["line_id"], 0.0)) for l in lines}
        for sku, tot in sku_totals.items():
            ls = by_sku.get(sku, [])
            if not ls: continue
            gsum = sum(l["gross"] or 0 for l in ls) or 1.0
            allocated = 0.0
            for i, l in enumerate(ls):
                share = tot if len(ls) == 1 else (
                    round(tot - allocated, 2) if i == len(ls) - 1
                    else round(tot * (l["gross"] or 0) / gsum, 2))
                allocated += share
                final[l["line_id"]] = round(final.get(l["line_id"], 0.0) + share, 2)
        for lid, val in final.items():
            if val or lid in exact:
                db.execute("UPDATE order_items SET refund=? WHERE platform=? AND seller_account=? AND external_order_id=? AND line_id=?",
                           (round(val, 2), pf, acct, oid, lid)); n += 1
    db.commit(); return {"updated_lines": n, "new_refund_events": new_events}

def sku_fee_rate(db, sku: str, platform: str = "Amazon", seller_account: str = None) -> dict:
    """This SKU's real fee rate from order_fees (SKU_EXACT only with enough gross).
    V20: with a seller_account, only that account's rate — accounts are never mixed."""
    ensure_v12(db)
    r = db.execute("SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(fees),0) f FROM order_fees WHERE sku=? AND platform=? AND (? IS NULL OR seller_account=?)",
                   (sku, platform, seller_account, seller_account)).fetchone()
    if r and r["g"] and r["g"] >= 5000:
        return {"rate": r["f"] / r["g"], "gross_basis": r["g"], "precision": "SKU_EXACT"}
    return {"rate": None, "gross_basis": r["g"] if r else 0, "precision": None}

def realized_fee_rate(db, platform: str = "Amazon") -> dict:
    """Real fee rate from settlements — real numbers instead of estimates when there is enough settlement data (V12.1)."""
    ensure_v12(db)
    r = db.execute("SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(fees),0) f, COALESCE(SUM(taxes),0) t FROM settlements WHERE platform=?",
                   (platform,)).fetchone()
    if r and r["g"] and r["g"] >= 10000:
        return {"rate": (r["f"] + r["t"]) / r["g"], "gross_basis": r["g"], "source": "REALIZED"}
    return {"rate": None, "gross_basis": r["g"] if r else 0, "source": "ESTIMATE_ONLY"}

def contribution_v2(db, sku: str, price: float, platform: str = "Amazon", ad_spend_per_unit: float = 0.0) -> dict:
    """Versioned cost + fees (real ones from settlements when available, otherwise a labelled estimate)."""
    c = get_cost(db, sku)
    if not c["known"]:
        return {"sku": sku, "known": False, "scale_allowed": False, "reason": c["reason"],
                "note": "A margin without cost would be a lie — so no number is given"}
    from profit_calculator import SKU as PricedSKU, contribution
    from flipkart_calculator import flipkart_profit
    rf = realized_fee_rate(db, platform)
    est_fees = flipkart_profit(price, 0)["total_fees"] if platform == "Flipkart" else contribution(PricedSKU(sku, price, 0))["marketplace_fees"]
    sf = sku_fee_rate(db, sku, platform)
    if sf["rate"] is not None:
        fees = round(price * sf["rate"], 2); fee_precision = "SKU_EXACT"
        fee_source = f"SKU_EXACT — this SKU's real fee rate {sf['rate']*100:.1f}% on ₹{sf['gross_basis']:,.0f} gross from SP Finances"
    elif rf["rate"] is not None:
        # V12.2 fee precision: confidence depends on how much of total sales the settlements cover
        import analytics as AN
        gmv = AN.sales_totals(db)["revenue"] or 0
        # With no order records at all, settlements are the only evidence of sales — treat coverage as full
        coverage = 1.0 if not gmv else min(1.0, rf["gross_basis"] / gmv)
        realized_fees = price * rf["rate"]
        if coverage >= 0.8:
            fees, fee_precision = realized_fees, "HIGH"
            fee_source = f"REALIZED — settlements cover {coverage*100:.0f}% of sales; fee rate {rf['rate']*100:.1f}% (SKU-level split impossible without settlement detail)"
        elif coverage >= 0.3:
            fees, fee_precision = realized_fees * coverage + est_fees * (1 - coverage), "MEDIUM"
            fee_source = f"BLENDED — settlement coverage {coverage*100:.0f}%: weighted mix of the real rate and the fee-table estimate"
        else:
            fees, fee_precision = est_fees, "LOW"
            fee_source = f"ESTIMATE — settlement coverage only {coverage*100:.0f}%; only the fee-table estimate is left"
        fees = round(fees, 2)
    else:
        fees, fee_precision = est_fees, "LOW"
        fee_source = "ESTIMATE — fee-table estimate (not enough settlement data)"
    # V29 GST: the selling price includes GST, which goes to the government, not to you. With a rate on the cost,
    # the output GST in the price is taken out (costs are then entered WITHOUT GST — input credit is claimed back).
    rate = c.get("gst_rate")
    gst = round(price * rate / (100 + rate), 2) if rate is not None else 0.0
    gst_basis = (f"GST {rate:g}% taken out of the price (₹{gst:,.2f} per unit); costs are treated as excluding GST" if rate is not None else
                 "GST rate not set — GST is NOT taken out of the price, so this margin is too high unless the GST you pay "
                 "is included in 'other'. Add the GST rate to this SKU's cost.")
    net = price - gst - fees - c["unit_cost"] - ad_spend_per_unit
    margin_pct = round(net / price * 100, 1) if price else 0.0
    scale_allowed = (not c["stale"]) and margin_pct > 0
    return {"sku": sku, "known": True, "price": price, "platform_fees": round(fees, 2), "fee_source": fee_source, "fee_precision": fee_precision,
            "unit_cost": c["unit_cost"], "ad_per_unit": ad_spend_per_unit,
            "gst_rate": rate, "gst_per_unit": gst, "gst_basis": gst_basis,
            "contribution": round(net, 2), "margin_pct": margin_pct,
            "break_even_roas": round(price / net, 2) if net > 0 else None,
            "scale_allowed": scale_allowed,
            "reason": c["reason"] if c["stale"] else ("Margin is negative — do not scale" if margin_pct <= 0 else "OK")}
