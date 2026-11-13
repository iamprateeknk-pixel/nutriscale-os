"""Experiment Engine — the agent learns from tests (A/B), not from guesses.
Only the winning change goes live; the losing one is rolled back. No decision without a minimum sample.
"""
import math

def _rate(conv: int, views: int) -> float:
    return conv / views if views else 0.0

def evaluate_ab(control: dict, treatment: dict, min_views: int = 500) -> dict:
    """control/treatment: {views, conversions}. Both sides need minimum data."""
    if control["views"] < min_views or treatment["views"] < min_views:
        return {"decision": "WAIT", "reason": f"Not enough data — at least {min_views} views needed on both sides"}
    rc, rt = _rate(control["conversions"], control["views"]), _rate(treatment["conversions"], treatment["views"])
    # Simple z-test for proportions
    n1, n2 = control["views"], treatment["views"]
    p = (control["conversions"] + treatment["conversions"]) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) or 1e-9
    z = (rt - rc) / se
    lift = round((rt - rc) / rc * 100, 1) if rc else 0.0
    if z >= 1.96 and rt > rc:
        return {"decision": "PROMOTE_TREATMENT", "lift_pct": lift, "z": round(z, 2),
                "reason": f"New version is {lift}% better at 95%+ confidence — go live, keep the old one saved for rollback"}
    if z <= -1.96:
        return {"decision": "KEEP_CONTROL", "lift_pct": lift, "z": round(z, 2),
                "reason": "New version is worse — roll back, and store the lesson: this change does not work for this SKU"}
    return {"decision": "WAIT", "lift_pct": lift, "z": round(z, 2), "reason": "No clear difference — let the test run longer"}

def daily_learning_cycle() -> list:
    """What goes into the 11 pm Daily Learning Summary."""
    return ["Results of earlier actions (7/14-day) — confidence up/down",
            "What was newly learned today (with sources)",
            "Status of running experiments — who is winning",
            "Rules that were disabled and why",
            "The agents' plan for tomorrow"]
