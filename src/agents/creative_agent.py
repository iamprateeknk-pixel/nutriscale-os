"""A05 Creative Agent — image/video brief banata hai jo CTR badhaye.
Asal image banana designer/AI-image tool ka kaam hai; brief hi woh kagaz hai jispar jeet-haar tay hoti hai.
Har brief claim-check se guzarta hai.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base import BaseAgent
from claim_checker import check_listing_text

def main_image_brief(product: str, grade: str, weight: str, hindi_word: str = "") -> dict:
    shots = [
        {"shot": 1, "type": "MAIN (search me dikhne wali)", "brief": f"Safed background par bhara hua pack + khule {product} ka bada close-up. Pack par '{grade}' aur '{weight}' bade aksharon me. Tasveer ka 85% hissa product — Amazon ka niyam aur CTR dono ke liye."},
        {"shot": 2, "type": "SIZE/GRADE saboot", "brief": f"Hath ke saath ya sikke ke saath size tulna — graahak ki sabse badi shikayat 'size chhota laga' yahin khatm hoti hai."},
        {"shot": 3, "type": "INFOGRAPHIC — fayde", "brief": "3-4 poshak tatva bade saaf aksharon me (protein/fiber) — koi bimari ka dawa NAHI (claim checker rok dega)."},
        {"shot": 4, "type": "USE-CASE lifestyle", "brief": "Subah ke naste/bowl ke saath asal upyog — Rufus-AI aur graahak dono ko use-case samajh aata hai."},
        {"shot": 5, "type": "PACKING/FRESHNESS", "brief": "Sealed hygienic pack, expiry/batch dikhta hua — bharosa banane wali tasveer."},
        {"shot": 6, "type": "COMPARISON chart", "brief": "Hamara grade vs aam bazaar grade — bina kisi competitor ka naam liye."},
        {"shot": 7, "type": "GIFTING (season)", "brief": "Gift-ready packing ki tasveer — Diwali/wedding season me yahi tasveer hamper bechti hai."},
    ]
    text = " ".join(s["brief"] for s in shots)
    claims = check_listing_text(text)
    return {"product": product, "shots": shots, "claims_ok": claims["can_go_live"],
            "video_script": f"30-sec video: 0-5s {product} ka close-up aur crackle sound, 5-15s size/grade saboot, 15-25s 3 upyog, 25-30s pack + {weight} + bharosa line."}

class CreativeAgent(BaseAgent):
    id = "A05"; name = "Creative"
    def brief_for(self, product: str, grade: str, weight: str) -> dict:
        b = main_image_brief(product, grade, weight)
        self.file_proposal("ALERT", f"{product} {weight} ke liye 7-shot image brief + video script taiyaar — designer ko bhejna hai")
        return b
