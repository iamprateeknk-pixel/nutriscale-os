"""A06 Ads Manager Agent — Decision Engine.
One clear action per search term / keyword: KILL, SCALE, BID_DOWN, HOLD or LISTING_PROBLEM.
Rule: save money first, then grow.
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
    # 1. Money is burning: high spend, zero sales
    if s.orders == 0 and s.spend > 1.5 * target_cpa:
        return {"term": s.term, "action": "KILL_ADD_NEGATIVE", "roas": round(roas, 2),
                "reason": f"Rs{s.spend:.0f} spend, 0 sale — target CPA Rs{target_cpa:.0f} exceeded 1.5x"}
    # 2. Winner: scale up
    if roas >= target_roas * 1.5 and s.orders >= 3:
        return {"term": s.term, "action": "SCALE_BID_UP_20", "roas": round(roas, 2),
                "reason": f"ROAS {roas:.1f} is 1.5x above the {target_roas:.1f} target — bid +20%, separate it into an exact campaign"}
    # 3. Low CTR = an image/title problem; bid money is wasted here
    if s.impressions >= 1000 and ctr < 0.3:
        return {"term": s.term, "action": "LISTING_PROBLEM", "roas": round(roas, 2),
                "reason": f"CTR {ctr:.2f}% (<0.3%) — ticket A05/A04 to fix the main image/title; do not raise the bid"}
    # 4. Working but expensive
    if s.spend and roas < target_roas * 0.6 and s.orders >= 1:
        return {"term": s.term, "action": "BID_DOWN_20", "roas": round(roas, 2),
                "reason": f"ROAS {roas:.1f} far below the {target_roas:.1f} target — bid -20%"}
    return {"term": s.term, "action": "HOLD", "roas": round(roas, 2), "reason": "Let more data collect / it is near the target"}

def blended_roas(terms: list[TermStats]) -> float:
    sp = sum(t.spend for t in terms); sa = sum(t.sales for t in terms)
    return round(sa / sp, 2) if sp else 0.0
