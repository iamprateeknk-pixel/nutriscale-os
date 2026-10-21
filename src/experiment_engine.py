"""Experiment Engine — agent andaz se nahi, parakh (A/B test) se seekhta hai.
Jeetne wala badlav hi live hoga, haarne wala rollback. Min sample ke bina faisla nahi.
"""
import math

def _rate(conv: int, views: int) -> float:
    return conv / views if views else 0.0

def evaluate_ab(control: dict, treatment: dict, min_views: int = 500) -> dict:
    """control/treatment: {views, conversions}. Dono taraf min data chahiye."""
    if control["views"] < min_views or treatment["views"] < min_views:
        return {"decision": "WAIT", "reason": f"Data kam hai — dono taraf kam se kam {min_views} views chahiye"}
    rc, rt = _rate(control["conversions"], control["views"]), _rate(treatment["conversions"], treatment["views"])
    # Simple z-test for proportions
    n1, n2 = control["views"], treatment["views"]
    p = (control["conversions"] + treatment["conversions"]) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) or 1e-9
    z = (rt - rc) / se
    lift = round((rt - rc) / rc * 100, 1) if rc else 0.0
    if z >= 1.96 and rt > rc:
        return {"decision": "PROMOTE_TREATMENT", "lift_pct": lift, "z": round(z, 2),
                "reason": f"Naya version {lift}% behtar, bharosa 95%+ — live karo, purana rollback ke liye save"}
    if z <= -1.96:
        return {"decision": "KEEP_CONTROL", "lift_pct": lift, "z": round(z, 2),
                "reason": "Naya version kharab hai — rollback, aur ye seekh store karo: ye badlav is SKU par kaam nahi karta"}
    return {"decision": "WAIT", "lift_pct": lift, "z": round(z, 2), "reason": "Fark saaf nahi hai — test aur chalne do"}

def daily_learning_cycle() -> list:
    """Raat 11 baje ki Daily Learning Summary me kya-kya jayega."""
    return ["Kal ke actions ke results (7/14-din wale) — confidence up/down",
            "Aaj web se kya naya seekha (source ke saath)",
            "Chal rahe experiments ki halat — kaun jeet raha hai",
            "Disable hue rules aur unki wajah",
            "Kal ke liye agents ki nayi yojna"]
