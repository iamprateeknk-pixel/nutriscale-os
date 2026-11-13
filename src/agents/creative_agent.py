"""A05 Creative Agent — writes image/video briefs that raise CTR.
Making the actual image is the designer's/AI-image tool's job; the brief is the document that decides win or loss.
Every brief passes the claim check.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from claim_checker import check_listing_text

def main_image_brief(product: str, grade: str, weight: str, hindi_word: str = "") -> dict:
    shots = [
        {"shot": 1, "type": "MAIN (shown in search)", "brief": f"Full pack + a big close-up of the open {product} on a white background. '{grade}' and '{weight}' in large letters on the pack. Product fills 85% of the image — for Amazon's rule and for CTR."},
        {"shot": 2, "type": "SIZE/GRADE proof", "brief": f"Size comparison against a hand or a coin — this ends the most common complaint, 'the size looked small'."},
        {"shot": 3, "type": "INFOGRAPHIC — benefits", "brief": "3-4 nutrients in big clear letters (protein/fibre) — NO disease claims (the claim checker will block them)."},
        {"shot": 4, "type": "USE-CASE lifestyle", "brief": "Real use with breakfast/a bowl — both Rufus-AI and shoppers understand the use case."},
        {"shot": 5, "type": "PACKING/FRESHNESS", "brief": "Sealed hygienic pack with expiry/batch visible — a trust-building image."},
        {"shot": 6, "type": "COMPARISON chart", "brief": "Our grade vs the common market grade — without naming any competitor."},
        {"shot": 7, "type": "GIFTING (season)", "brief": "Gift-ready packing — in Diwali/wedding season this is the image that sells hampers."},
    ]
    text = " ".join(s["brief"] for s in shots)
    claims = check_listing_text(text)
    return {"product": product, "shots": shots, "claims_ok": claims["can_go_live"],
            "video_script": f"30-sec video: 0-5s close-up of {product} with a crackle sound, 5-15s size/grade proof, 15-25s 3 uses, 25-30s pack + {weight} + trust line."}

class CreativeAgent(BaseAgent):
    id = "A05"; name = "Creative"
    def brief_for(self, product: str, grade: str, weight: str) -> dict:
        b = main_image_brief(product, grade, weight)
        self.file_proposal("ALERT", f"7-shot image brief + video script ready for {product} {weight} — send to the designer")
        return b
