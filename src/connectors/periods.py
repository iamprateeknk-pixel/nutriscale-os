"""Period Overlap Engine (V14; boundary semantics settled in V15) — Ads report periods
are INCLUSIVE (both the first and last day count). Rules:
- New period lies INSIDE a bigger old one         -> SKIP (no double counting)
- New period fully covers smaller old ones         -> remove the old ones, keep the new (supersede)
- Any overlap of even one day (boundary day too)    -> BLOCK, with a clear reason (splitting an overlap is wrong)
- Adjacent but non-overlapping (one ends, the next starts the following day) -> clean, insert
"""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from platform_core import ensure_v12

def _d(s): return datetime.date.fromisoformat(str(s)[:10])

def existing_periods(db, source: str) -> list:
    ensure_v12(db)
    return [(r["period_start"], r["period_end"]) for r in db.execute(
        "SELECT DISTINCT period_start, period_end FROM search_terms WHERE source=? AND period_start IS NOT NULL AND period_start<>''",
        (source,))]

def apply_period_rows(db, source: str, start: str, end: str, insert_fn) -> dict:
    s_new, e_new = _d(start), _d(end)
    superseded = []
    for (s0, e0) in existing_periods(db, source):
        s, e = _d(s0), _d(e0)
        if s == s_new and e == e_new:
            superseded.append((s0, e0)); continue
        if s <= s_new and e >= e_new:
            return {"status": "SKIPPED_CONTAINED", "detail": f"Old period {s0}..{e0} already covers this — the new one is skipped to avoid double counting"}
        if s_new <= s and e_new >= e:
            superseded.append((s0, e0)); continue
        overlap_days = (min(e, e_new) - max(s, s_new)).days + 1
        if overlap_days > 0:
            return {"status": "BLOCKED_PARTIAL_OVERLAP",
                    "detail": f"Overlaps period {s0}..{e0} by {overlap_days} days (boundary days count) — splitting aggregates would be wrong; remove the old one first or load one larger period"}
    for (s0, e0) in superseded:
        db.execute("DELETE FROM search_terms WHERE source=? AND period_start=? AND period_end=?", (source, s0, e0))
    db.commit()
    n = insert_fn()
    return {"status": "INSERTED", "inserted": n, "replaced_periods": superseded}
