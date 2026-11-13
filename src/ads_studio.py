"""Ads Studio (ADS-01..06) — a profit-driven ads brain.
The old rule 'ROAS 4 for everything' was wrong: each SKU's target comes from its own contribution.
Unknown cost = bid/scale recommendations OFF (only safe reduce/pause recommendations run).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import finance as F

def campaign_health(store) -> list:
    """ADS-01: health of each campaign — spend/sales/ROAS/ACOS + evidence of data freshness."""
    out = []
    for r in store.db.execute("SELECT * FROM campaigns ORDER BY spend DESC"):
        c = dict(r)
        c["roas"] = round(c["sales"] / c["spend"], 2) if c["spend"] else None
        c["acos_pct"] = round(c["spend"] / c["sales"] * 100, 1) if c["sales"] else None
        c["evidence"] = "Observed — imported campaign report (source: campaigns table)"
        out.append(c)
    return out

def recommend_bid(db, sku: str, price: float, current_cpc: float, clicks: int, orders: int,
                  profit_floor_pct: float = 10.0, platform: str = "Amazon") -> dict:
    """ADS-02: max CPC = CVR × net value per order × allowed ACOS.
    Allowed ACOS = contribution-before-ads margin − the owner's profit floor."""
    if clicks < 30 or orders < 2:
        return {"blocked": True, "reason": f"Sample too small (clicks {clicks}, orders {orders}) — no bid change based on a guess",
                "min_clicks": 30, "min_orders": 2}
    fin = F.contribution_v2(db, sku, price, platform)
    if not fin["known"]:
        return {"blocked": True, "reason": fin["reason"], "remedy": "Record this SKU's cost first (Costs screen)"}
    cvr = orders / clicks
    margin_before_ads = fin["contribution"] + 0  # with ad_per_unit=0, contribution is the margin before ads
    net_per_order = price - (price - fin["contribution"])  # = the contribution amount again
    net_per_order = fin["contribution"]
    allowed_acos = max((fin["margin_pct"] - profit_floor_pct) / 100.0, 0.0)
    if allowed_acos <= 0:
        return {"blocked": True, "reason": f"Margin {fin['margin_pct']}% is not above your profit floor of {profit_floor_pct}% — "
                                           "no CPC is profitable on this SKU. Fix price/cost first and keep ads off.",
                "margin_pct": fin["margin_pct"]}
    max_cpc = round(cvr * price * allowed_acos, 2)
    suggested = min(max(current_cpc * 0.8, 0.0), max_cpc) if current_cpc > max_cpc else current_cpc
    change = round((suggested - current_cpc) / current_cpc * 100, 1) if current_cpc else 0.0
    if abs(change) > 20:  # never more than a 20% change in one day
        suggested = round(current_cpc * (1 + (0.2 if change > 0 else -0.2)), 2)
        change = 20.0 if change > 0 else -20.0
    return {"blocked": False, "sku": sku, "current_cpc": current_cpc, "suggested_cpc": suggested,
            "change_pct": change, "cvr_pct": round(cvr * 100, 1), "margin_pct": fin["margin_pct"],
            "allowed_acos_pct": round(allowed_acos * 100, 1), "max_cpc": max_cpc,
            "reason": "Target ACOS comes from this SKU's real contribution and your profit floor — not a global ROAS number"}

def harvest_candidates(store, min_orders: int = 2) -> list:
    """ADS-03: harvest terms that sell in broad/auto into Exact; negate only when
    a term never converted anywhere (killing a winning term by mistake is the most expensive error)."""
    conv_terms = {r["term"] for r in store.db.execute("SELECT DISTINCT term FROM search_terms WHERE purchases>0")}
    harvest, negatives = [], []
    for r in store.db.execute("""SELECT term, campaign, SUM(purchases) pu, SUM(spend) sp, SUM(clicks) cl
                                 FROM search_terms GROUP BY term, campaign"""):
        if r["pu"] >= min_orders:
            harvest.append({"term": r["term"], "from_campaign": r["campaign"], "orders": r["pu"],
                            "action": "Harvest into an Exact campaign; add an exact negative in the source campaign so spend is not split"})
        elif r["sp"] >= 80 and r["term"] in conv_terms:
            pass  # converted elsewhere — NO negative
        elif r["sp"] >= 80:
            negatives.append({"term": r["term"], "campaign": r["campaign"], "wasted": round(r["sp"]),
                              "action": "Exact negative — never converted anywhere"})
    return {"harvest": harvest, "negatives": negatives}

def pacing_alerts(store, daily_budget_cap: float, inventory_qty: dict = None) -> list:
    """ADS-04: spend pace and stock alarms."""
    alerts = []
    total = store.db.execute("SELECT COALESCE(SUM(spend),0) s FROM campaigns").fetchone()["s"]
    zero_sales = store.db.execute("SELECT COUNT(*) c FROM campaigns WHERE sales=0 AND spend>0").fetchone()["c"]
    if zero_sales: alerts.append({"type": "WASTE", "detail": f"{zero_sales} campaigns spend with zero sales — check the pause list"})
    for sku, qty in (inventory_qty or {}).items():
        if qty <= 0: alerts.append({"type": "STOCKOUT", "sku": sku, "detail": "Out of stock — propose pausing this SKU's ads, otherwise money burns"})
    alerts.append({"type": "INFO", "detail": f"Total campaign spend (imported period): ₹{total:,.0f}; daily cap ₹{daily_budget_cap:,.0f} is enforced by the control center"})
    return alerts

def portfolio_scenarios(store, monthly_budget: float) -> dict:
    """ADS-05: three budget scenarios — current, proposed (with profit gate), safe."""
    camps = [dict(r) for r in store.db.execute("SELECT * FROM campaigns WHERE spend>0 ORDER BY spend DESC")]
    total = sum(c["spend"] for c in camps) or 1
    current = {c["name"]: round(c["spend"] / total * 100, 1) for c in camps}
    winners = [c for c in camps if c["sales"] / c["spend"] >= 2.0]
    losers = [c for c in camps if c["sales"] == 0]
    proposal = {}
    freed = sum(c["spend"] for c in losers) / total * 100
    for c in camps:
        share = c["spend"] / total * 100
        if c in losers: proposal[c["name"]] = 0.0
        elif c in winners and winners: proposal[c["name"]] = round(share + freed / len(winners), 1)
        else: proposal[c["name"]] = round(share, 1)
    return {"monthly_budget": monthly_budget, "current_pct": current, "proposal_pct": proposal,
            "conservative_pct": {k: round(v * 0.7, 1) for k, v in proposal.items()},
            "note": "The proposed split only moves zero-sale campaigns' share to those with ROAS≥2; real changes go through the Action Plan + approval. This is an estimate, not a guarantee."}
