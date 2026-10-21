"""Organic Flywheel — Blended ROAS / TACOS engine.
Sach: Ads Console ka ROAS sirf paid sales ginta hai.
Blended ROAS = Total Sales / Ad Spend. Jaise-jaise organic rank badhta hai,
wahi spend dugni total sales lata hai — yahi ROAS 8-10 ka asal rasta hai.
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
    """Target total sales aur blended ROAS se ulta hisaab: kitna ad spend chahiye."""
    return round(total_sales_target / target_blended_roas, 2)

def rank_mode(organic_rank: int | None, hero_keyword: bool) -> str:
    """A06 ka mode: rank nahi mila to RANK_PUSH (breakeven ads, maksad page-1),
    rank mil gaya to HARVEST (spend ghatao, free organic sales uthao)."""
    if not hero_keyword: return "NORMAL"
    if organic_rank is None or organic_rank > 10: return "RANK_PUSH"
    return "HARVEST"
