"""A03 Keyword Domination + A02 Competitor Intelligence — scoring cores."""

def keyword_opportunity(search_volume: int, relevance: float, competition: float,
                        current_rank: int | None = None) -> dict:
    """Opportunity = volume x relevance / competition. relevance/competition 0-1.
    Rank bonus: agar tum page-2/3 par ho (rank 11-30) to push karne par sabse tez fayda."""
    base = (search_volume * relevance) / max(competition, 0.05)
    bonus = 1.3 if current_rank and 11 <= current_rank <= 30 else 1.0
    score = round(base * bonus, 1)
    tier = "HERO" if score >= 5000 else "GROWTH" if score >= 1500 else "LONGTAIL" if score >= 300 else "IGNORE"
    return {"opportunity_score": score, "tier": tier}

def competitor_gap(your_price_per_kg: float, comp_price_per_kg: float,
                   your_rating: float, comp_rating: float,
                   your_reviews: int, comp_reviews: int) -> dict:
    """Competitor se kahan haar rahe ho — ek nazar me."""
    gaps = []
    price_gap_pct = round((your_price_per_kg - comp_price_per_kg) / comp_price_per_kg * 100, 1)
    if price_gap_pct > 5: gaps.append(f"PRICE: tum {price_gap_pct}% mehange per-kg")
    if comp_rating - your_rating >= 0.2: gaps.append(f"RATING: competitor {comp_rating} vs tum {your_rating}")
    if comp_reviews > your_reviews * 3: gaps.append(f"REVIEWS: competitor ke {comp_reviews} vs tumhare {your_reviews} — trust gap bada hai")
    return {"price_gap_pct": price_gap_pct, "gaps": gaps,
            "attack_plan": "Product Targeting ads + price/coupon match + review gap band karo" if gaps else "Tum aage ho — position defend karo (Brand Defence ads)"}
