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

def contribution_v2(db, sku: str, price: float, platform: str = "Amazon", ad_spend_per_unit: float = 0.0) -> dict:
    """Versioned cost + maujuda fee calculators se asal contribution."""
    c = get_cost(db, sku)
    if not c["known"]:
        return {"sku": sku, "known": False, "scale_allowed": False, "reason": c["reason"],
                "note": "Cost bina margin ka andaaz jhooth hoga — isiliye number nahi diya gaya"}
    from profit_calculator import SKU as PricedSKU, contribution
    from flipkart_calculator import flipkart_profit
    if platform == "Flipkart":
        fees = flipkart_profit(price, 0)["total_fees"]
    else:
        fees = contribution(PricedSKU(sku, price, 0))["marketplace_fees"]
    net = price - fees - c["unit_cost"] - ad_spend_per_unit
    margin_pct = round(net / price * 100, 1) if price else 0.0
    scale_allowed = (not c["stale"]) and margin_pct > 0
    return {"sku": sku, "known": True, "price": price, "platform_fees": round(fees, 2),
            "unit_cost": c["unit_cost"], "ad_per_unit": ad_spend_per_unit,
            "contribution": round(net, 2), "margin_pct": margin_pct,
            "break_even_roas": round(price / net, 2) if net > 0 else None,
            "scale_allowed": scale_allowed,
            "reason": c["reason"] if c["stale"] else ("Margin ghate me hai — scale nahi" if margin_pct <= 0 else "Theek hai")}
