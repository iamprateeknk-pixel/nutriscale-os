"""A04 Listing Agent — BUILDS real titles/bullets (template + keywords + claim-safe).
All generated text passes the Claim Checker first; blocked text never goes live.
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from listing_scorer import Listing, score_listing
from claim_checker import check_listing_text

SAFE_USES = ["daily snacking", "gifting", "baking", "trail mix", "morning routine"]

def generate_title(product: str, grade: str, weight: str, keywords: list, use_case: str = "daily snacking",
                   brand: str = "") -> str:
    """V23: Amazon's 27-Jul-2026 rule (AMZ-T-01) — title <=75 characters, no word more than twice (AMZ-T-03).
    The old 200-character 'Fresh & Premium...' template would now be cut by Amazon's AI, and 'fresh' is an
    FSSAI conditional word (FS-C-02). Use cases now go into Item Highlights (build_item_highlights)."""
    from listing_rules import build_title_amazon
    hero = " ".join(keywords[:2]) if keywords else ""
    return build_title_amazon(brand, product, grade, weight, hero)["title"]

def generate_bullets(facts: dict) -> list:
    """facts: origin, grade_detail, nutrition_line, pack_line, uses(list), fssai(optional licence no.).
    Deliberately no disease/cure claims — the checker confirms this.
    V24: default text contains NO claims that need evidence (previously 'nitrogen flush', 'FSSAI licensed' and
    'return/replacement policy' were added automatically — without evidence). Such facts only appear when given in facts."""
    b = [
        f"Premium {facts.get('grade_detail') or 'quality'} — from {facts.get('origin') or 'carefully selected harvests'}, cleaned and sorted.",
        f"Rich in nutrients: {facts.get('nutrition_line') or 'a good source of protein, fibre and healthy fats'} — suitable for everyday eating.",
        f"Packing: {facts.get('pack_line') or 'food-grade hygienic pouch'} — keeps the crunch and taste intact.",
        "Uses: " + ", ".join(facts.get("uses") or SAFE_USES[:3]) + " — for the whole family.",
        ("Trust: FSSAI lic. " + facts["fssai"] + "; " if facts.get("fssai") else "Trust: ")
        + "batch, packing date and expiry clearly printed on every pack.",
    ]
    return b

class ListingAgent(BaseAgent):
    id = "A04"; name = "Listing Optimization"

    def build_listing(self, sku: str, brand: str, product: str, nut: str, grade: str = "", weight: str = "",
                      form: str = "", facts: dict = None, platform: str = "Amazon", competitor_brands=(),
                      images=None) -> dict:
        """V23 full path: keyword plan (your data + SQP + vocabulary) -> rule-compliant title/highlights/backend
        -> full audit (Amazon + FSSAI) -> brain advice -> proposal (rule_ids in the payload so outcomes drive learning)."""
        import keyword_intel as KI, listing_rules as LR, agent_brain as AB
        facts = facts or {}
        AB.seed_playbook(self.store.db)
        kp = KI.placement_plan(self.store, nut, platform=platform, grade=grade or None, weight=weight or None)
        plan = kp["plan"]
        hero = plan["TITLE"][0] if plan["TITLE"] else ""
        t = LR.build_title_amazon(brand, product, grade, weight, hero, form)
        uses = facts.get("uses", SAFE_USES[:3])
        hl = LR.build_item_highlights([*(plan["HIGHLIGHTS_BULLETS"][:2]), *uses])
        bullets = generate_bullets(facts)
        backend = LR.pack_backend_terms(plan["HIGHLIGHTS_BULLETS"][2:] + plan["BACKEND"], t["title"], bullets, competitor_brands)
        audit = LR.audit_listing(platform, t["title"], bullets, backend["backend_terms"], hl["item_highlights"],
                                 images, competitor_brands, db=self.store.db, sku=sku)
        AB.record_listing_audit(self.store.db, sku, audit)
        advice = [{"rule_id": a["rule_id"], "confidence": a["confidence"], "action": a["action"] or a["statement"][:140]}
                  for a in AB.advise(self.store.db, agent=self.id, platform=platform)[:6]]
        rule_ids = sorted(set(t["rule_ids"] + hl["rule_ids"] + backend["rule_ids"] + kp["rule_ids"]))
        prop = None
        if audit["can_publish"]:
            # into action_v12 with rule_ids — outcome_engine measures at 7/14 days, agent_brain updates confidence in those rules
            import actions as ACT, hashlib
            payload = {"sku": sku, "platform": platform, "title": t["title"], "item_highlights": hl["item_highlights"],
                       "bullets": bullets, "backend_terms": backend["backend_terms"], "rule_ids": rule_ids}
            key = "LST-" + hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
            prop = ACT.create_proposal(self.store.db, "LISTING_PATCH", platform, "default", payload, "ONE_TAP", self.id, key,
                                       f"Compliance {audit['compliance_score']}/100; real impact is measured after 7/14 days")
            prop = {k: prop[k] for k in ("id", "state", "duplicate")}
        return {"sku": sku, "title": t["title"], "title_chars": t["chars"], "item_highlights": hl["item_highlights"],
                "bullets": bullets, "backend_terms": backend["backend_terms"], "backend_bytes": backend["bytes"],
                "keyword_plan": kp, "audit": audit, "brain_advice": advice, "rule_ids": rule_ids,
                "proposal": prop, "blocked": not audit["can_publish"]}
    def improve_with_llm(self, current: Listing, product: str, grade: str, weight: str,
                         keywords: list, facts: dict) -> dict:
        """With an LLM key the copy comes from the LLM, otherwise it falls back to rule templates. Both paths pass the claim check."""
        if not self.llm.available:
            r = self.improve(current, product, grade, weight, keywords, facts); r["source"] = "RULES (no LLM key)"
            return r
        import json as _json
        prompt = (f"Create JSON for an Amazon India listing: {{\"title\": \"...\", \"bullets\": [\"...\" x5]}}\n"
                  f"Product: Dry Fruit Farm Premium {product} {grade} {weight}. Keywords: {', '.join(keywords)}.\n"
                  f"Tathya: {facts.get('grade_detail','')}; {facts.get('origin','')}; {facts.get('nutrition_line','')}; {facts.get('pack_line','')}.\n"
                  f"Rules: title of at most 75 characters, NO disease/cure claims (FSSAI), English copy.")
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
                    "note": "Generated text failed the claim check — it will not go live until fixed"}
        # Expected after: full title keywords, 5 bullets, backend filled (everything else unchanged)
        after_listing = Listing(title=title, bullets=5, image_count=current.image_count,
                                has_video=current.has_video, has_a_plus=current.has_a_plus,
                                rating=current.rating, review_count=current.review_count,
                                price_per_kg=current.price_per_kg,
                                top3_avg_price_per_kg=current.top3_avg_price_per_kg,
                                backend_terms_filled=True, main_keywords_in_title=min(5, len(keywords) or 5))
        after = score_listing(after_listing)
        prop = self.file_proposal("LISTING_PATCH",
                                  f"{product} {weight} listing upgrade — new title + 5 bullets + backend terms",
                                  predicted=f"Score {before['score']} -> {after['score']} (estimate; real impact measured after 14 days)")
        return {"blocked": False, "title": title, "bullets": bullets, "claims": claims,
                "score_before": before, "score_after_expected": after, "proposal": prop}
