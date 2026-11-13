"""Compliance Flow — FSSAI + Health Claim Checker.
A false health claim on dry fruits = a blocked listing + FSSAI action. Every listing passes this before going live.
"""
import re

BANNED = [  # disease-cure claims — strictly prohibited
    (r"\b(cur(e|es|ed|ing)|heal(s|ed|ing)?|treat(s|ed|ing|ment)|prevent(s|ed|ing)?|theek kar\w*|ilaaj)\b.*\b(diabet\w*|cancer|bp|blood pressure|thyroid|heart|cholesterol)\b", "Bimari theek karne ka dawa — FSSAI/Ads Code ke khilaf, listing turant band ho sakti hai"),
    (r"\b(diabet\w*|cancer|sugar|cholesterol)\b.*\b(cur(e|es|ed|ing)|control\w*|revers\w*|theek)\b", "Cure/control claims together with a disease are prohibited"),
    (r"\b(weight loss|vajan ghat\w*)\b.*\b(guarantee|pakka|\d+\s*(din|days?)\s*me)\b", "Guaranteed weight-loss dawa mana hai"),
    (r"\b100%\s*(pure|natural|organic)\b", "'100%' or 'organic' without a certificate is prohibited — only allowed with a certificate"),
]
RISKY = [
    (r"\b(diabetic|diabetes|sugar)\b", "'Diabetic-friendly' type claims need evidence/a lab report — risky without it"),
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
            "note": "If BLOCKED the listing will NOT go live — A04 fixes the text first"}

def check_label(label_fields_present: list) -> dict:
    missing = [m for m in LABEL_MUST if m not in [x.lower() for x in label_fields_present]]
    return {"label_ok": not missing, "missing_on_label": missing}
