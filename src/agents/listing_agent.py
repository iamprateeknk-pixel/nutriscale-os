"""A04 Listing Agent — asal title/bullets BANATA hai (template + keyword + claim-safe).
Har generated text pehle Claim Checker se guzarta hai; block ho to text live nahi jayega.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from listing_scorer import Listing, score_listing
from claim_checker import check_listing_text

SAFE_USES = ["daily snacking", "gifting", "baking", "trail mix", "morning routine"]

def generate_title(product: str, grade: str, weight: str, keywords: list, use_case: str = "daily snacking") -> str:
    """Keywords aage, grade+weight saaf, use-case Rufus-AI readable. 200 char ke andar."""
    lead = ", ".join(k.title() for k in keywords[:2]) if keywords else product
    title = f"{product} {grade} {weight} | {lead} | Premium Quality, Fresh & Hygienically Packed | Ideal for {use_case.title()}"
    return title[:200].rstrip(" |")

def generate_bullets(facts: dict) -> list:
    """facts: origin, grade_detail, nutrition_line, pack_line, uses(list).
    Koi bimari-cure wala dawa jaan-bujh kar nahi — checker iski pushti karega."""
    b = [
        f"Premium {facts.get('grade_detail','quality')} — {facts.get('origin','chuni hui upaj')} se, har dana size aur rang me ek jaisa.",
        f"Poshak tattvon se bharpur: {facts.get('nutrition_line','protein, fiber aur healthy fats ka achha srot')} — roz ke khane ke liye upyukt.",
        f"Taazgi pakki: {facts.get('pack_line','food-grade hygienic packing, nitrogen flush ke saath')} — kurkurapan aur swad barkarar.",
        "Upyog: " + ", ".join(facts.get("uses", SAFE_USES[:3])) + " — poore parivar ke liye.",
        "Bharosa: FSSAI licensed packing, batch par expiry saaf chhapi — kharab nikle to aasan return/replacement niti.",
    ]
    return b

class ListingAgent(BaseAgent):
    id = "A04"; name = "Listing Optimization"
    def improve_with_llm(self, current: Listing, product: str, grade: str, weight: str,
                         keywords: list, facts: dict) -> dict:
        """LLM key ho to copy LLM se, warna rule-templates par fallback. Dono raaste claim-check se guzarte hain."""
        if not self.llm.available:
            r = self.improve(current, product, grade, weight, keywords, facts); r["source"] = "RULES (LLM key nahi)"
            return r
        import json as _json
        prompt = (f"Amazon India listing ke liye JSON banao: {{\"title\": \"...\", \"bullets\": [\"...\" x5]}}\n"
                  f"Product: Dry Fruit Farm Premium {product} {grade} {weight}. Keywords: {', '.join(keywords)}.\n"
                  f"Tathya: {facts.get('grade_detail','')}; {facts.get('origin','')}; {facts.get('nutrition_line','')}; {facts.get('pack_line','')}.\n"
                  f"Niyam: title 200 akshar se kam, koi bimari-ilaaj ka dawa NAHI (FSSAI), Hinglish chalegi.")
        try:
            raw = self.llm.generate(prompt, system="Tum ek tajurbe-kaar Amazon India listing visheshagya ho.")
            data = _json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
            title, bullets = str(data["title"])[:200], [str(b) for b in data["bullets"]][:5]
        except Exception:
            r = self.improve(current, product, grade, weight, keywords, facts); r["source"] = "RULES (LLM fail -> fallback)"
            return r
        claims = check_listing_text(title + " " + " ".join(bullets))
        if not claims["can_go_live"]:
            r = self.improve(current, product, grade, weight, keywords, facts); r["source"] = "RULES (LLM copy claim-check fail -> fallback)"
            return r
        before = score_listing(current)
        after_listing = Listing(title=title, bullets=5, image_count=current.image_count, has_video=current.has_video,
                                has_a_plus=current.has_a_plus, rating=current.rating, review_count=current.review_count,
                                price_per_kg=current.price_per_kg, top3_avg_price_per_kg=current.top3_avg_price_per_kg,
                                backend_terms_filled=True, main_keywords_in_title=min(5, len(keywords) or 5))
        after = score_listing(after_listing)
        prop = self.file_proposal("LISTING_PATCH", f"{product} {weight} listing upgrade (LLM copy, claim-checked)",
                                  predicted=f"Score {before['score']} -> {after['score']}")
        return {"blocked": False, "title": title, "bullets": bullets, "claims": claims,
                "score_before": before, "score_after_expected": after, "proposal": prop, "source": "LLM"}

    def improve(self, current: Listing, product: str, grade: str, weight: str,
                keywords: list, facts: dict) -> dict:
        before = score_listing(current)
        title = generate_title(product, grade, weight, keywords)
        bullets = generate_bullets(facts)
        full_text = title + " " + " ".join(bullets)
        claims = check_listing_text(full_text)
        if not claims["can_go_live"]:
            return {"blocked": True, "reasons": claims["blocked_reasons"],
                    "note": "Generated text claim-check me fail — live nahi jayega, pehle sudhar hoga"}
        # Expected after: title keywords pure, bullets 5, backend bhara hua (baaki cheezein waisi hi)
        after_listing = Listing(title=title, bullets=5, image_count=current.image_count,
                                has_video=current.has_video, has_a_plus=current.has_a_plus,
                                rating=current.rating, review_count=current.review_count,
                                price_per_kg=current.price_per_kg,
                                top3_avg_price_per_kg=current.top3_avg_price_per_kg,
                                backend_terms_filled=True, main_keywords_in_title=min(5, len(keywords) or 5))
        after = score_listing(after_listing)
        prop = self.file_proposal("LISTING_PATCH",
                                  f"{product} {weight} ki listing upgrade — naya title + 5 bullets + backend terms",
                                  predicted=f"Score {before['score']} -> {after['score']} (andaaz, asal asar 14 din me maapa jayega)")
        return {"blocked": False, "title": title, "bullets": bullets, "claims": claims,
                "score_before": before, "score_after_expected": after, "proposal": prop}
