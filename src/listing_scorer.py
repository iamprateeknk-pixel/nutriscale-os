"""A04 Listing Optimization Agent — Listing Score 0-100.
Score <70 => ads scale BLOCK. Pehle listing fix, phir spend.
"""
from dataclasses import dataclass, field

@dataclass
class Listing:
    title: str
    bullets: int                 # bullet points ki sankhya
    image_count: int
    has_video: bool = False
    has_a_plus: bool = False
    rating: float = 0.0
    review_count: int = 0
    price_per_kg: float = 0.0
    top3_avg_price_per_kg: float = 0.0
    backend_terms_filled: bool = False
    main_keywords_in_title: int = 0   # top keywords me se kitne title me hain (out of 5)

def score_listing(l: Listing) -> dict:
    issues, score = [], 0.0
    # Title 20
    t = 0
    if 120 <= len(l.title) <= 200: t += 10
    elif len(l.title) >= 80: t += 6
    else: issues.append("Title bahut chhota hai — keywords + grade + weight + use-case add karo")
    t += min(l.main_keywords_in_title, 5) * 2
    if l.main_keywords_in_title < 3: issues.append("Top 5 keywords me se 3 se kam title me hain — indexing weak hoga")
    score += t
    # Images 20
    score += min(l.image_count, 7) * 2
    if l.image_count < 6: issues.append(f"Sirf {l.image_count} images — kam se kam 6-7 chahiye (infographics ke saath)")
    if l.has_video: score += 6
    else: issues.append("Video nahi hai — video wali listings ka conversion zyada hota hai")
    # Bullets 15
    score += min(l.bullets, 5) * 3
    if l.bullets < 5: issues.append("5 benefit-first bullets pure karo (health, origin, grade, freshness, use)")
    # A+ 10
    if l.has_a_plus: score += 10
    else: issues.append("A+ Content nahi hai — brand story + comparison chart lagao")
    # Reviews 15
    if l.rating >= 4.3: score += 7
    elif l.rating >= 4.0: score += 4
    else: issues.append(f"Rating {l.rating} kam hai — 4.2 se niche conversion girta hai")
    if l.review_count >= 200: score += 8
    elif l.review_count >= 50: score += 5
    elif l.review_count >= 20: score += 2
    else: issues.append(f"Sirf {l.review_count} reviews — Vine + review strategy chahiye (kam se kam 50 ka target)")
    # Price 10 (per-kg vs top-3 competitor)
    if l.top3_avg_price_per_kg:
        gap = (l.price_per_kg - l.top3_avg_price_per_kg) / l.top3_avg_price_per_kg * 100
        if gap <= 0: score += 10
        elif gap <= 5: score += 7
        elif gap <= 10: score += 4
        else: issues.append(f"Price per-kg top-3 competitor se {gap:.0f}% zyada hai — ya price kam karo ya value justify karo (grade/premium)")
    # Backend 10
    if l.backend_terms_filled: score += 10
    else: issues.append("Backend search terms khali/incomplete — Hinglish + misspelling terms yahi aate hain (badam, badaam, kaju, kishmish)")
    verdict = "SCALE_OK" if score >= 70 else "FIX_FIRST_ADS_BLOCKED"
    return {"score": round(score, 1), "verdict": verdict, "issues": issues}
