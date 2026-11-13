"""Organic Flywheel — Blended ROAS / TACOS engine.
Truth: the Ads Console ROAS only counts paid sales.
Blended ROAS = Total Sales / Ad Spend. As organic rank grows,
the same spend brings twice the total sales — that is the real path to ROAS 8-10.
"""

def flywheel(ad_spend: float, paid_sales: float, organic_sales: float) -> dict:
    total = paid_sales + organic_sales
    return {
        "ad_spend": ad_spend,
        "paid_roas": round(paid_sales / ad_spend, 2) if ad_spend else 0,
        "organic_sales": organic_sales,
        "organic_share_pct": round(organic_sales / total * 100, 1) if total else 0,
        "total_sales": total,
        "blended_roas": round(total / ad_spend, 2) if ad_spend else 0,
        "tacos_pct": round(ad_spend / total * 100, 1) if total else 0,
    }

def ad_spend_for_target_blended(total_sales_target: float, target_blended_roas: float) -> float:
    """Reverse calculation from target total sales and blended ROAS: how much ad spend is needed."""
    return round(total_sales_target / target_blended_roas, 2)

def rank_mode(organic_rank: int | None, hero_keyword: bool) -> str:
    """A06 mode: without rank, RANK_PUSH (break-even ads, aim for page 1),
    with rank, HARVEST (cut spend, collect free organic sales)."""
    if not hero_keyword: return "NORMAL"
    if organic_rank is None or organic_rank > 10: return "RANK_PUSH"
    return "HARVEST"
