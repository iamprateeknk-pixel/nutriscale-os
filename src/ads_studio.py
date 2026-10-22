"""Ads Studio (ADS-01..06) — munafe se chalne wala ads dimaag.
Purana niyam 'sab par ROAS 4' galat tha: har SKU ka target uske contribution se banta hai.
Cost unknown = bid/scale ki sifarish BAND (sirf ghatao/pause ki surakshit sifarish chalegi).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import finance as F

def campaign_health(store) -> list:
    """ADS-01: har campaign ki sehat — spend/sales/ROAS/ACOS + data ki tazgi ka saboot."""
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
    """ADS-02: max CPC = CVR × order ki net value × allowed ACOS.
    Allowed ACOS = contribution-before-ads margin − owner ka profit floor."""
    if clicks < 30 or orders < 2:
        return {"blocked": True, "reason": f"Sample chhota hai (clicks {clicks}, orders {orders}) — bid badlav ka faisla andaz par nahi hoga",
                "min_clicks": 30, "min_orders": 2}
    fin = F.contribution_v2(db, sku, price, platform)
    if not fin["known"]:
        return {"blocked": True, "reason": fin["reason"], "remedy": "Pehle is SKU ki cost darj karo (Costs screen)"}
    cvr = orders / clicks
    margin_before_ads = fin["contribution"] + 0  # ad_per_unit=0 par contribution hi margin-before-ads hai
    net_per_order = price - (price - fin["contribution"])  # = contribution wali rakam dobara saaf
    net_per_order = fin["contribution"]
    allowed_acos = max((fin["margin_pct"] - profit_floor_pct) / 100.0, 0.0)
    if allowed_acos <= 0:
        return {"blocked": True, "reason": f"Margin {fin['margin_pct']}% tumhare profit floor {profit_floor_pct}% se upar hi nahi — "
                                           "is SKU par koi bhi CPC munafa nahi dega. Pehle price/cost theek karo, ads band rakho.",
                "margin_pct": fin["margin_pct"]}
    max_cpc = round(cvr * price * allowed_acos, 2)
    suggested = min(max(current_cpc * 0.8, 0.0), max_cpc) if current_cpc > max_cpc else current_cpc
    change = round((suggested - current_cpc) / current_cpc * 100, 1) if current_cpc else 0.0
    if abs(change) > 20:  # ek din me 20% se zyada badlav kabhi nahi
        suggested = round(current_cpc * (1 + (0.2 if change > 0 else -0.2)), 2)
        change = 20.0 if change > 0 else -20.0
    return {"blocked": False, "sku": sku, "current_cpc": current_cpc, "suggested_cpc": suggested,
            "change_pct": change, "cvr_pct": round(cvr * 100, 1), "margin_pct": fin["margin_pct"],
            "allowed_acos_pct": round(allowed_acos * 100, 1), "max_cpc": max_cpc,
            "reason": "Target ACOS is SKU ke asal contribution aur tumhare profit floor se bana hai — global ROAS number se nahi"}

def harvest_candidates(store, min_orders: int = 2) -> list:
    """ADS-03: broad/auto me bikne wale terms ko Exact me harvest; negative sirf tab jab
    term kahin bhi convert na hua ho (galti se jeetne wale term ko marna sabse mehenga)."""
    conv_terms = {r["term"] for r in store.db.execute("SELECT DISTINCT term FROM search_terms WHERE purchases>0")}
    harvest, negatives = [], []
    for r in store.db.execute("""SELECT term, campaign, SUM(purchases) pu, SUM(spend) sp, SUM(clicks) cl
                                 FROM search_terms GROUP BY term, campaign"""):
        if r["pu"] >= min_orders:
            harvest.append({"term": r["term"], "from_campaign": r["campaign"], "orders": r["pu"],
                            "action": "Exact campaign me harvest karo; source campaign me exact-negative lagao taaki paisa do jagah na bante"})
        elif r["sp"] >= 80 and r["term"] in conv_terms:
            pass  # doosri jagah convert hua hai — negative NAHI lagega
        elif r["sp"] >= 80:
            negatives.append({"term": r["term"], "campaign": r["campaign"], "wasted": round(r["sp"]),
                              "action": "Exact negative — kahin bhi convert nahi hua"})
    return {"harvest": harvest, "negatives": negatives}

def pacing_alerts(store, daily_budget_cap: float, inventory_qty: dict = None) -> list:
    """ADS-04: kharch ki raftaar aur stock ki ghanti."""
    alerts = []
    total = store.db.execute("SELECT COALESCE(SUM(spend),0) s FROM campaigns").fetchone()["s"]
    zero_sales = store.db.execute("SELECT COUNT(*) c FROM campaigns WHERE sales=0 AND spend>0").fetchone()["c"]
    if zero_sales: alerts.append({"type": "WASTE", "detail": f"{zero_sales} campaigns me kharch hai par sale zero — pause list dekho"})
    for sku, qty in (inventory_qty or {}).items():
        if qty <= 0: alerts.append({"type": "STOCKOUT", "sku": sku, "detail": "Stock khatm — is SKU ke ads rokne ka proposal banao, varna paisa jalega"})
    alerts.append({"type": "INFO", "detail": f"Kul campaign kharch (imported arsa): ₹{total:,.0f}; roz ka cap ₹{daily_budget_cap:,.0f} control center se लागू hai"})
    return alerts

def portfolio_scenarios(store, monthly_budget: float) -> dict:
    """ADS-05: budget ke 3 bandobast — aaj ka, prastavit (munafa gate ke saath), surakshit."""
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
            "note": "Prastavit bantwara sirf ROAS≥2 walon ko zero-sale walon ka hissa deta hai; asal lagu Action Plan + approval se hoga. Ye andaaz hai, guarantee nahi."}
