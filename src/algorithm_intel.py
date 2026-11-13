"""Algorithm Intelligence — understanding the Amazon + Flipkart algorithms, update by update.
TRUTH: the exact algorithms are both platforms' secrets. These models are estimated weights from official
guidance + industry consensus, and the Rank Probe keeps correcting them from your own data.
"""
import math

# ---------- Amazon Search Rank Model (estimated weights, total 100) ----------
AMAZON_RANK_WEIGHTS = {
    "relevance_indexing": 20,   # keyword is in title/backend terms and indexed
    "sales_velocity": 20,       # recent sales velocity — the fastest effect
    "conversion_rate": 18,      # % of page visitors who buy
    "ctr": 12,                  # click % when shown in search
    "price_competitiveness": 10,
    "prime_fba": 8,             # FBA/Prime badge
    "stock_availability": 6,    # stock khatm = rank khatm
    "rating_reviews": 6,
}
FLIPKART_RANK_WEIGHTS = {
    "relevance_indexing": 20,
    "price_competitiveness": 16,  # price weighs more on Flipkart
    "rating_reviews": 14,
    "flipkart_assured": 14,       # the Assured badge = key to rank
    "sales_velocity": 14,
    "seller_rating": 10,
    "dispatch_speed": 7,
    "low_returns": 5,
}

def rank_readiness(scores: dict, platform: str = "amazon") -> dict:
    """scores: each factor 0-100. Output: how rank-ready you are + the weakest factor."""
    w = AMAZON_RANK_WEIGHTS if platform == "amazon" else FLIPKART_RANK_WEIGHTS
    total = sum(scores.get(k, 0) * wt for k, wt in w.items()) / 100
    weakest = min(w, key=lambda k: scores.get(k, 0) * w[k] / max(w[k], 1) if k in scores else 0)
    weakest = min(scores, key=lambda k: scores[k]) if scores else None
    return {"platform": platform, "rank_readiness_score": round(total, 1),
            "weakest_factor": weakest,
            "fix_first": f"'{weakest}' is the weakest — to improve rank, fix this first (weight {w.get(weakest)}%)"}

def buybox_score_amazon(price_rank: int, total_sellers: int, is_fba: bool,
                        seller_rating: float, in_stock: bool) -> dict:
    """Buy Box: 80%+ of Amazon sales go through the Buy Box. price_rank 1 = cheapest."""
    if not in_stock: return {"buybox_chance_pct": 0, "note": "No stock = Buy Box impossible"}
    score = 100 - (price_rank - 1) * (60 / max(total_sellers, 1))
    if is_fba: score += 15
    score += (seller_rating - 4.0) * 10
    return {"buybox_chance_pct": round(max(0, min(100, score)), 1),
            "note": "FBA + competitive price + seller rating — all three are keys to the Buy Box"}

# ---------- Algorithm Change Impact ----------
CHANGE_MAP = [
    (["fee", "referral", "commission", "shulk"], ["F4 Profit Flow", "A07 Pricing"], "HIGH", "Every SKU margin must be recalculated"),
    (["fba", "fulfillment", "warehouse", "storage"], ["F3 Inventory & FBA Flow"], "HIGH", "Stock plan and shipment plan will change"),
    (["search", "ranking", "algorithm", "cosmo", "rufus", "a10", "a9"], ["A04 Listing", "A03 Keyword", "Rank Probe"], "HIGH", "Playbook update + listing dobara parkho"),
    (["advertising", "ads", "sponsored", "bid"], ["A06 Ads Manager"], "MEDIUM", "Campaign structure/bidding parkho"),
    (["policy", "account health", "odr", "performance"], ["F10 Seller Health Flow", "A09 Governance"], "HIGH", "Account suraksha — turant dhyan do"),
    (["review", "rating"], ["A08 Review Agent"], "MEDIUM", "Review strategy parkho"),
    (["unicommerce", "api"], ["F1 Data Sync", "F2 Unicommerce Flow"], "MEDIUM", "Integration parkho"),
]

def assess_algorithm_change(change_text: str) -> dict:
    """The F9 Watch Flow catches changes; this function assesses their impact (A09 acts on it)."""
    t = change_text.lower(); hits = []
    for keywords, affected, severity, note in CHANGE_MAP:
        if any(k in t for k in keywords):
            hits.append({"affected": affected, "severity": severity, "note": note})
    if not hits:
        return {"impact": "LOW", "hits": [], "action": "Record it, no immediate change"}
    sev = "HIGH" if any(h["severity"] == "HIGH" for h in hits) else "MEDIUM"
    return {"impact": sev, "hits": hits,
            "action": "Create a playbook update proposal -> small experiment -> Tier-1 approval -> rollout"}

# ---------- Rank Probe: reverse-engineering the algorithm from your data ----------
def pearson(xs: list, ys: list) -> float:
    n = len(xs)
    if n < 3 or n != len(ys): return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return round(num / den, 3) if den else 0.0

def rank_probe_insight(ctr_series: list, rank_series: list) -> dict:
    """Lower rank number = better. So a negative correlation with CTR = CTR lowers the rank number (good)."""
    r = pearson(ctr_series, rank_series)
    if r <= -0.5: insight = "Strong evidence: rank improves as CTR rises — CTR is the key in this category"
    elif r >= 0.5: insight = "Reverse pattern — something other than CTR (maybe price/velocity) drives rank; probe further"
    else: insight = "No clear pattern yet — more days of data needed"
    return {"correlation_ctr_rank": r, "insight": insight}
