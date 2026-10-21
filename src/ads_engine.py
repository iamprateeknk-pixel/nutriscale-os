"""A06 Ads Manager Agent — Decision Engine.
Har search term / keyword ke liye ek saaf action: KILL, SCALE, BID_DOWN, HOLD, ya LISTING_PROBLEM.
Rule: paisa pehle bachega, phir badhega.
"""
from dataclasses import dataclass

@dataclass
class TermStats:
    term: str
    spend: float
    sales: float
    clicks: int = 0
    impressions: int = 0
    orders: int = 0

def decide(s: TermStats, target_roas: float, target_cpa: float) -> dict:
    roas = (s.sales / s.spend) if s.spend else 0.0
    ctr = (s.clicks / s.impressions * 100) if s.impressions else 0.0
    # 1. Paisa jal raha hai: zyada spend, zero sale
    if s.orders == 0 and s.spend > 1.5 * target_cpa:
        return {"term": s.term, "action": "KILL_ADD_NEGATIVE", "roas": round(roas, 2),
                "reason": f"Rs{s.spend:.0f} spend, 0 sale — target CPA Rs{target_cpa:.0f} ka 1.5x cross"}
    # 2. Winner: scale karo
    if roas >= target_roas * 1.5 and s.orders >= 3:
        return {"term": s.term, "action": "SCALE_BID_UP_20", "roas": round(roas, 2),
                "reason": f"ROAS {roas:.1f} target {target_roas:.1f} se 1.5x zyada — bid +20%, exact campaign me alag karo"}
    # 3. CTR kam = image/title problem, bid ka paisa yahan waste
    if s.impressions >= 1000 and ctr < 0.3:
        return {"term": s.term, "action": "LISTING_PROBLEM", "roas": round(roas, 2),
                "reason": f"CTR {ctr:.2f}% (<0.3%) — main image/title fix ke liye A05/A04 ko ticket, bid mat badhao"}
    # 4. Chal raha hai par mehenga
    if s.spend and roas < target_roas * 0.6 and s.orders >= 1:
        return {"term": s.term, "action": "BID_DOWN_20", "roas": round(roas, 2),
                "reason": f"ROAS {roas:.1f} target {target_roas:.1f} se bahut kam — bid -20%"}
    return {"term": s.term, "action": "HOLD", "roas": round(roas, 2), "reason": "Data aur collect hone do / target ke aas-paas hai"}

def blended_roas(terms: list[TermStats]) -> float:
    sp = sum(t.spend for t in terms); sa = sum(t.sales for t in terms)
    return round(sa / sp, 2) if sp else 0.0
