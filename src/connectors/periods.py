"""Period Overlap Engine (V14) — Ads reports ke overlapping periods ka imaandaar niyam.
Barabar period ka replace to pehle se tha; asli khatra tha alag-alag par overlapping windows
(e.g. roz 2-din ki khidki) — dono ginati ho jati thi. Ab:
- Naya period kisi bade purane period ke ANDAR hai  -> SKIP (purana dhakta hai, dohra hisaab nahi)
- Naya period purane chhote periods ko dhakta hai  -> purane hatakar naya (supersede)
- Aadha-overlap (crossing)                          -> BLOCK, saaf wajah ke saath (andaaz nahi lagega)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from platform_core import ensure_v12

def existing_periods(db, source: str) -> list:
    ensure_v12(db)
    return [(r["period_start"], r["period_end"]) for r in db.execute(
        "SELECT DISTINCT period_start, period_end FROM search_terms WHERE source=? AND period_start IS NOT NULL AND period_start<>''",
        (source,))]

def apply_period_rows(db, source: str, start: str, end: str, insert_fn) -> dict:
    periods = existing_periods(db, source)
    superseded = []
    for (s, e) in periods:
        if s == start and e == end:
            superseded.append((s, e)); continue
        if s <= start and e >= end:
            return {"status": "SKIPPED_CONTAINED", "detail": f"Purana period {s}..{e} isey pehle se dhakta hai — dohra hisaab rokne ke liye naya skip"}
        if start <= s and end >= e:
            superseded.append((s, e)); continue
        if s < end and start < e:
            return {"status": "BLOCKED_PARTIAL_OVERLAP", "detail": f"Period {s}..{e} se aadha takraav hai — aggregates tod kar jodna galat hoga; pehle purana hatao ya poora bada period lao"}
    for (s, e) in superseded:
        db.execute("DELETE FROM search_terms WHERE source=? AND period_start=? AND period_end=?", (source, s, e))
    db.commit()
    n = insert_fn()
    return {"status": "INSERTED", "inserted": n, "replaced_periods": superseded}
