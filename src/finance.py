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
    if rf["rate"] is not None:
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
