"""Compliance Flow — FSSAI + Health Claim Checker.
Dry fruits par galat health claim = listing band + FSSAI ki karwai. Koi listing live hone se pehle isse guzregi.
"""
import re

BANNED = [  # bimari theek karne ke daave — bilkul mana hai
    (r"\b(cure|theek kar\w*|ilaaj)\b.*\b(diabetes|cancer|bp|blood pressure|thyroid|heart)\b", "Bimari theek karne ka dawa — FSSAI/Ads Code ke khilaf, listing turant band ho sakti hai"),
    (r"\b(diabetes|cancer|sugar)\b.*\b(cure|control|reverse|theek)\b", "Bimari ke saath cure/control ka dawa mana hai"),
    (r"\b(weight loss|vajan ghat\w*)\b.*\b(guarantee|pakka|\d+\s*(din|days?)\s*me)\b", "Guaranteed weight-loss dawa mana hai"),
    (r"\b100%\s*(pure|natural|organic)\b", "'100%' ya bina certificate ke 'organic' likhna mana hai — certificate ho to hi chalega"),
]
RISKY = [
    (r"\b(diabetic|diabetes|sugar)\b", "'Diabetic-friendly' type dawaon ke liye saboot/lab report chahiye — bina uske risk hai"),
    (r"\b(immunity|rog pratirodh\w*)\b", "Immunity dawa FSSAI ki nazar me sensitive hai — halke shabdon me rakho ('poshak tattvon se bharpur')"),
    (r"\b(no added sugar|bina cheeni)\b", "Ye dawa tabhi agar asal me added sugar zero hai aur label par bhi waisa hi likha hai"),
]
LABEL_MUST = ["fssai license number", "net weight", "expiry / best before", "nutrition facts",
              "ingredients", "manufacturer/packer naam-pata", "veg logo", "mrp"]

def check_listing_text(text: str) -> dict:
    t = text.lower(); blocks, warnings = [], []
    for pat, msg in BANNED:
        if re.search(pat, t): blocks.append(msg)
    for pat, msg in RISKY:
        if re.search(pat, t): warnings.append(msg)
    return {"can_go_live": not blocks, "blocked_reasons": blocks, "warnings": warnings,
            "note": "BLOCK ho to listing live NAHI hogi — A04 pehle text sudharega"}

def check_label(label_fields_present: list) -> dict:
    missing = [m for m in LABEL_MUST if m not in [x.lower() for x in label_fields_present]]
    return {"label_ok": not missing, "missing_on_label": missing}
