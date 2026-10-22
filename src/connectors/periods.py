"""Period Overlap Engine (V14, V15 me boundary semantics pakki) — Ads reports ke periods
INCLUSIVE hote hain (pehla aur aakhri din dono ginati me). Niyam:
- Naya period kisi bade purane ke ANDAR hai        -> SKIP (dohra hisaab nahi)
- Naya period purane chhoto ko poora dhakta hai    -> purane hatakar naya (supersede)
- Ek bhi din ka takraav (boundary din bhi)         -> BLOCK, saaf wajah (aadha takraav todna galat)
- Sata hua par takraav-rahit (ek khatm, dusra agle din se) -> saaf, insert
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
            return {"status": "SKIPPED_CONTAINED", "detail": f"Purana period {s0}..{e0} isey pehle se dhakta hai — dohra hisaab rokne ke liye naya skip"}
        if s_new <= s and e_new >= e:
            superseded.append((s0, e0)); continue
        overlap_days = (min(e, e_new) - max(s, s_new)).days + 1
        if overlap_days > 0:
            return {"status": "BLOCKED_PARTIAL_OVERLAP",
                    "detail": f"Period {s0}..{e0} se {overlap_days} din ka takraav hai (boundary din bhi ginati me aata hai) — aggregates todna galat hoga; pehle purana hatao ya poora bada period lao"}
    for (s0, e0) in superseded:
        db.execute("DELETE FROM search_terms WHERE source=? AND period_start=? AND period_end=?", (source, s0, e0))
    db.commit()
    n = insert_fn()
    return {"status": "INSERTED", "inserted": n, "replaced_periods": superseded}
