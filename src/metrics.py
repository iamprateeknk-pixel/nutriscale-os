"""DAT-02 Metric reconciliation — matched-period gating.
Rule: numbers from different time windows are NEVER combined into a confident number.
If the windows overlap too little, derived metrics (TACOS/organic share) = NOT_COMPARABLE.
"""
import datetime

def _d(s): return datetime.date.fromisoformat(str(s)[:10])

def compare_windows(orders_period: tuple, ads_period: tuple, min_overlap: float = 0.9) -> dict:
    o0, o1, a0, a1 = _d(orders_period[0]), _d(orders_period[1]), _d(ads_period[0]), _d(ads_period[1])
    lo, hi = max(o0, a0), min(o1, a1)
    overlap_days = max((hi - lo).days + 1, 0)
    span = max((o1 - o0).days + 1, (a1 - a0).days + 1, 1)
    ratio = overlap_days / span
    return {"comparable": ratio >= min_overlap, "overlap_ratio": round(ratio, 2),
            "overlap_days": overlap_days,
            "reason": "The time windows match" if ratio >= min_overlap else
                      f"The time windows only overlap {int(ratio*100)}% — showing TACOS/organic share would mislead"}

def tacos(ad_spend: float, total_sales: float, orders_period: tuple, ads_period: tuple) -> dict:
    cmp = compare_windows(orders_period, ads_period)
    if not cmp["comparable"]:
        return {"value": None, "status": "NOT_COMPARABLE", **cmp,
                "note": "Bring data for the other window or align the windows — only then can TACOS be calculated"}
    if not total_sales: return {"value": None, "status": "NO_SALES", **cmp}
    return {"value": round(ad_spend / total_sales * 100, 1), "status": "OK", **cmp,
            "formula": "ad_spend / total_sales (matched period)"}

def coverage(imported_days: int, window_days: int) -> dict:
    pct = round(imported_days / window_days * 100, 1) if window_days else 0.0
    return {"coverage_pct": pct, "status": "FULL" if pct >= 95 else "PARTIAL" if pct >= 50 else "LOW",
            "note": "Low coverage means low confidence in the KPI — the UI shows this"}
