"""Algorithm Intelligence — Amazon + Flipkart ke algorithm ko samajhna, har update par.
SACH: exact algorithm dono platforms ka secret hai. Ye models official guidance +
industry consensus ke estimated weights hain, aur Rank Probe apne data se inhe sahi karta rahega.
"""
import math

# ---------- Amazon Search Rank Model (weights andaaze se, kul 100) ----------
AMAZON_RANK_WEIGHTS = {
    "relevance_indexing": 20,   # title/backend terms me keyword hai aur index ho raha hai
    "sales_velocity": 20,       # haal ki bikri ki raftaar — sabse tez asar
    "conversion_rate": 18,      # page par aake kharidne walo ka %
    "ctr": 12,                  # search me dikhne par click %
    "price_competitiveness": 10,
    "prime_fba": 8,             # FBA/Prime badge
    "stock_availability": 6,    # stock khatm = rank khatm
    "rating_reviews": 6,
}
FLIPKART_RANK_WEIGHTS = {
    "relevance_indexing": 20,
    "price_competitiveness": 16,  # Flipkart par price ka wazan zyada
    "rating_reviews": 14,
    "flipkart_assured": 14,       # Assured badge = rank ki chaabi
    "sales_velocity": 14,
    "seller_rating": 10,
    "dispatch_speed": 7,
    "low_returns": 5,
}

def rank_readiness(scores: dict, platform: str = "amazon") -> dict:
    """scores: har factor 0-100. Output: rank ke liye kitne taiyaar ho + sabse kamzor factor."""
    w = AMAZON_RANK_WEIGHTS if platform == "amazon" else FLIPKART_RANK_WEIGHTS
    total = sum(scores.get(k, 0) * wt for k, wt in w.items()) / 100
    weakest = min(w, key=lambda k: scores.get(k, 0) * w[k] / max(w[k], 1) if k in scores else 0)
    weakest = min(scores, key=lambda k: scores[k]) if scores else None
    return {"platform": platform, "rank_readiness_score": round(total, 1),
            "weakest_factor": weakest,
            "fix_first": f"'{weakest}' sabse kamzor hai — rank badhana hai to pehle yahi fix karo (weight {w.get(weakest)}%)"}

def buybox_score_amazon(price_rank: int, total_sellers: int, is_fba: bool,
                        seller_rating: float, in_stock: bool) -> dict:
    """Buy Box: Amazon par 80%+ sales Buy Box se aati hain. price_rank 1 = sabse sasta."""
    if not in_stock: return {"buybox_chance_pct": 0, "note": "Stock nahi = Buy Box impossible"}
    score = 100 - (price_rank - 1) * (60 / max(total_sellers, 1))
    if is_fba: score += 15
    score += (seller_rating - 4.0) * 10
    return {"buybox_chance_pct": round(max(0, min(100, score)), 1),
            "note": "FBA + pratiyogita price + seller rating — teeno Buy Box ki chaabi"}

# ---------- Algorithm Change Impact ----------
CHANGE_MAP = [
    (["fee", "referral", "commission", "shulk"], ["F4 Profit Flow", "A07 Pricing"], "HIGH", "Saare SKU ke margin dobara ginne padenge"),
    (["fba", "fulfillment", "warehouse", "storage"], ["F3 Inventory & FBA Flow"], "HIGH", "Stock yojna aur shipment plan badlega"),
    (["search", "ranking", "algorithm", "cosmo", "rufus", "a10", "a9"], ["A04 Listing", "A03 Keyword", "Rank Probe"], "HIGH", "Playbook update + listing dobara parkho"),
    (["advertising", "ads", "sponsored", "bid"], ["A06 Ads Manager"], "MEDIUM", "Campaign structure/bidding parkho"),
    (["policy", "account health", "odr", "performance"], ["F10 Seller Health Flow", "A09 Governance"], "HIGH", "Account suraksha — turant dhyan do"),
    (["review", "rating"], ["A08 Review Agent"], "MEDIUM", "Review strategy parkho"),
    (["unicommerce", "api"], ["F1 Data Sync", "F2 Unicommerce Flow"], "MEDIUM", "Integration parkho"),
]

def assess_algorithm_change(change_text: str) -> dict:
    """F9 Watch Flow badlav pakdega, ye function uska asar batayega (A09 ispar action lega)."""
    t = change_text.lower(); hits = []
    for keywords, affected, severity, note in CHANGE_MAP:
        if any(k in t for k in keywords):
            hits.append({"affected": affected, "severity": severity, "note": note})
    if not hits:
        return {"impact": "LOW", "hits": [], "action": "Record karo, koi turant badlav nahi"}
    sev = "HIGH" if any(h["severity"] == "HIGH" for h in hits) else "MEDIUM"
    return {"impact": sev, "hits": hits,
            "action": "Playbook update proposal banao -> chhota experiment -> Tier-1 approval -> rollout"}

# ---------- Rank Probe: apne data se algorithm ko ulta samajhna ----------
def pearson(xs: list, ys: list) -> float:
    n = len(xs)
    if n < 3 or n != len(ys): return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return round(num / den, 3) if den else 0.0

def rank_probe_insight(ctr_series: list, rank_series: list) -> dict:
    """Rank number chhota = behtar. Isiliye CTR ke saath negative correlation = CTR rank ghata raha hai (acha)."""
    r = pearson(ctr_series, rank_series)
    if r <= -0.5: insight = "Mazboot saboot: CTR badhne se rank upar jata hai — is category me CTR hi chaabi hai"
    elif r >= 0.5: insight = "Ulta pattern — CTR ke alawa kuch aur (shayad price/velocity) rank chala raha hai, aur probe karo"
    else: insight = "Abhi pattern saaf nahi — aur din ka data chahiye"
    return {"correlation_ctr_rank": r, "insight": insight}
