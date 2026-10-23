"""FIN-01 Finance — versioned costs + contribution. Niyam (QA-07):
cost UNKNOWN ho to woh ZERO nahi mana jayega, aur us SKU par ad SCALE ki sifarish band hogi.
Cost purani (stale > 90 din) ho to bhi chetaavni ke saath scale roka jayega.
"""
import os, sys, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

STALE_DAYS = 90

def set_cost(db, sku: str, cogs: float, packaging: float, other_variable: float = 0.0,
             source: str = "", approved_by: str = "", effective_from: str = None) -> dict:
    ensure_v12(db)
    eff = effective_from or datetime.date.today().isoformat()
    db.execute("INSERT INTO cost_versions(sku,effective_from,cogs,packaging,other_variable,source,approved_by,created_at) VALUES (?,?,?,?,?,?,?,?)",
               (sku, eff, cogs, packaging, other_variable, source, approved_by, now_utc())); db.commit()
    return {"sku": sku, "unit_cost": cogs + packaging + other_variable, "effective_from": eff}

def get_cost(db, sku: str, on_date: str = None) -> dict:
    ensure_v12(db)
    d = on_date or datetime.date.today().isoformat()
    r = db.execute("""SELECT * FROM cost_versions WHERE sku=? AND effective_from<=? ORDER BY effective_from DESC, id DESC LIMIT 1""",
                   (sku, d)).fetchone()
    if not r: return {"known": False, "reason": "Is SKU ki cost darj nahi — scale ki sifarish band hai", "sku": sku}
    age = (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(r["effective_from"])).days
    unit = r["cogs"] + r["packaging"] + r["other_variable"]
    return {"known": True, "sku": sku, "unit_cost": unit, "cogs": r["cogs"], "packaging": r["packaging"],
            "other_variable": r["other_variable"], "effective_from": r["effective_from"],
            "stale": age > STALE_DAYS, "age_days": age,
            "reason": "Cost 90 din se purani hai — nayi cost daalo, scale roka gaya" if age > STALE_DAYS else "Cost taaza hai"}

def _fee_event_id(platform: str, account: str, r: dict) -> str:
    """Event ki pakki pehchan — vendor ne transaction-id diya to wahi, warna content-hash
    (ek hi event dobara sync ho to pehchan takrayegi aur dohari ginati nahi hogi)."""
    import hashlib
    if r.get("event_id"): return str(r["event_id"])
    basis = "|".join([platform, account, str(r.get("order_id")), str(r.get("sku")),
                      str(r.get("event_type") or "SHIPMENT"), str(r.get("posted_at") or ""),
                      f"{float(r.get('gross') or 0):.2f}", f"{float(r.get('fees') or 0):.2f}",
                      f"{float(r.get('refund') or 0):.2f}"])
    return "h:" + hashlib.sha1(basis.encode()).hexdigest()[:24]

def import_order_fees(db, rows: list, platform: str = "Amazon", seller_account: str = "default") -> dict:
    """SP Finances fees — V20: pehle har financial EVENT alag darj hota hai (order_fee_events),
    phir order_fees usi ka YOG banta hai. Purana INSERT OR REPLACE ek hi order+SKU ke dusre
    shipment-event ko pehle wale se OVERWRITE kar deta tha — ab rakam judti hai, mit-ti nahi.
    Har row apna seller_account la sakti hai; na laaye to function-wala account lagega."""
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
    """Refund rakam order_items.refund me — revenue ab hamesha NET (gross - refund) ginega (V15).
    V21 P0 FIX: pehle har call line ki refund ko SET (overwrite) kar deta tha — ek hi line par
    dusra partial refund aate hi pehla MIT jata tha. Ab har refund pehle refund_events LEDGER me
    darj hota hai (event-id/content-hash pehchan, scope = platform+seller_account+order+line),
    aur line ki refund uske saare events ka YOG hoti hai — partial refunds JUDTE hain, mitte nahi.
    Line-id wala event seedha usi line par; bina line-id wala SKU-ke-kul par gross-anupaat me
    banta hai (V17 ka niyam, par ab CUMULATIVE kul par, har call ke tukde par nahi)."""
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
        # exact-line events ka yog line-war
        exact = {row["line_id"]: row["s"] for row in db.execute(
            """SELECT line_id, SUM(amount) s FROM refund_events
               WHERE platform=? AND seller_account=? AND external_order_id=? AND line_id<>''
               GROUP BY line_id""", (pf, acct, oid))}
        # bina-line events SKU-war kul — gross-anupaat me bantenge
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
    """order_fees se is SKU ki asal fee-dar (paryapt gross ho tabhi SKU_EXACT).
    V20: seller_account diya to sirf usi khaate ki dar — khaate mix nahi honge."""
    ensure_v12(db)
    r = db.execute("SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(fees),0) f FROM order_fees WHERE sku=? AND platform=? AND (? IS NULL OR seller_account=?)",
                   (sku, platform, seller_account, seller_account)).fetchone()
    if r and r["g"] and r["g"] >= 5000:
        return {"rate": r["f"] / r["g"], "gross_basis": r["g"], "precision": "SKU_EXACT"}
    return {"rate": None, "gross_basis": r["g"] if r else 0, "precision": None}

def realized_fee_rate(db, platform: str = "Amazon") -> dict:
    """Settlements se asal fee-dar — andaaz ki jagah asal, jab paryapt settlement data ho (V12.1)."""
    ensure_v12(db)
    r = db.execute("SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(fees),0) f, COALESCE(SUM(taxes),0) t FROM settlements WHERE platform=?",
                   (platform,)).fetchone()
    if r and r["g"] and r["g"] >= 10000:
        return {"rate": (r["f"] + r["t"]) / r["g"], "gross_basis": r["g"], "source": "REALIZED"}
    return {"rate": None, "gross_basis": r["g"] if r else 0, "source": "ESTIMATE_ONLY"}

def contribution_v2(db, sku: str, price: float, platform: str = "Amazon", ad_spend_per_unit: float = 0.0) -> dict:
    """Versioned cost + fees (settlements se asal mile to wahi, warna labelled estimate)."""
    c = get_cost(db, sku)
    if not c["known"]:
        return {"sku": sku, "known": False, "scale_allowed": False, "reason": c["reason"],
                "note": "Cost bina margin ka andaaz jhooth hoga — isiliye number nahi diya gaya"}
    from profit_calculator import SKU as PricedSKU, contribution
    from flipkart_calculator import flipkart_profit
    rf = realized_fee_rate(db, platform)
    est_fees = flipkart_profit(price, 0)["total_fees"] if platform == "Flipkart" else contribution(PricedSKU(sku, price, 0))["marketplace_fees"]
    sf = sku_fee_rate(db, sku, platform)
    if sf["rate"] is not None:
        fees = round(price * sf["rate"], 2); fee_precision = "SKU_EXACT"
        fee_source = f"SKU_EXACT — SP Finances ke ₹{sf['gross_basis']:,.0f} gross par is SKU ki asal fee-dar {sf['rate']*100:.1f}%"
    elif rf["rate"] is not None:
        # V12.2 fee precision: settlements kul bikri ka kitna hissa dhakte hain, usi hisaab se bharosa
        import analytics as AN
        gmv = AN.sales_totals(db)["revenue"] or 0
        # Orders ka koi record hi na ho to settlement hi bikri ka ekmatra saboot hai — coverage poori mano
        coverage = 1.0 if not gmv else min(1.0, rf["gross_basis"] / gmv)
        realized_fees = price * rf["rate"]
        if coverage >= 0.8:
            fees, fee_precision = realized_fees, "HIGH"
            fee_source = f"REALIZED — settlements bikri ka {coverage*100:.0f}% dhakte hain; fee-dar {rf['rate']*100:.1f}% (SKU-wise vibhajan settlement detail bina sambhav nahi)"
        elif coverage >= 0.3:
            fees, fee_precision = realized_fees * coverage + est_fees * (1 - coverage), "MEDIUM"
            fee_source = f"BLENDED — settlement coverage {coverage*100:.0f}%: asal dar aur fee-table andaaz ka bojh-daar mishran"
        else:
            fees, fee_precision = est_fees, "LOW"
            fee_source = f"ESTIMATE — settlement coverage sirf {coverage*100:.0f}%; fee-table andaaz hi bacha"
        fees = round(fees, 2)
    else:
        fees, fee_precision = est_fees, "LOW"
        fee_source = "ESTIMATE — fee-table andaaz (settlement data paryapt nahi)"
    net = price - fees - c["unit_cost"] - ad_spend_per_unit
    margin_pct = round(net / price * 100, 1) if price else 0.0
    scale_allowed = (not c["stale"]) and margin_pct > 0
    return {"sku": sku, "known": True, "price": price, "platform_fees": round(fees, 2), "fee_source": fee_source, "fee_precision": fee_precision,
            "unit_cost": c["unit_cost"], "ad_per_unit": ad_spend_per_unit,
            "contribution": round(net, 2), "margin_pct": margin_pct,
            "break_even_roas": round(price / net, 2) if net > 0 else None,
            "scale_allowed": scale_allowed,
            "reason": c["reason"] if c["stale"] else ("Margin ghate me hai — scale nahi" if margin_pct <= 0 else "Theek hai")}
