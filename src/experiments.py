"""Experiments (CVR-03 / RNK-04) + Learning Store (AIG-01).
Niyam: kam sample par jeet ka elaan NAHI — verdict WIN/LOSS/INCONCLUSIVE hoga,
INCONCLUSIVE hi imaandaar jawab hai jab saboot kam ho.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

MIN_SAMPLE = 100  # har group me kam se kam itne sessions/clicks bina jeet nahi

def _z_test(p1, n1, p2, n2):
    if not n1 or not n2: return 0.0
    pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    return abs(p1 - p2) / se if se else 0.0

def create_experiment(db, name, sku, platform, hypothesis, primary_metric, intervention, owner) -> dict:
    ensure_v12(db)
    overlap = db.execute("""SELECT id, name FROM experiments WHERE sku=? AND status IN ('PLANNED','RUNNING')""",
                         (sku,)).fetchall()
    cur = db.execute("INSERT INTO experiments(name,sku,platform,hypothesis,primary_metric,intervention,status,owner,contamination) VALUES (?,?,?,?,?,?, 'PLANNED',?,?)",
                     (name, sku, platform, hypothesis, primary_metric, intervention, owner,
                      f"overlap with #{overlap[0]['id']} ({overlap[0]['name']})" if overlap else ""))
    db.commit()
    return {"id": cur.lastrowid, "status": "PLANNED",
            "warning": "Isi SKU par ek aur tajurba chal raha hai — dono ke nateeje ghul sakte hain (contamination)" if overlap else ""}

def evaluate(db, exp_id: int, control: dict, variant: dict) -> dict:
    """control/variant: {rate: 0..1, n: sample}. 95% bharosa (z>=1.96) + min sample lazmi."""
    ensure_v12(db)
    if control["n"] < MIN_SAMPLE or variant["n"] < MIN_SAMPLE:
        verdict, note = "INCONCLUSIVE", f"Sample kam hai (control {control['n']}, variant {variant['n']}; kam se kam {MIN_SAMPLE} chahiye)"
    else:
        z = _z_test(control["rate"], control["n"], variant["rate"], variant["n"])
        if z < 1.96: verdict, note = "INCONCLUSIVE", f"Fark bharose ke star par nahi (z={z:.2f} < 1.96)"
        elif variant["rate"] > control["rate"]: verdict, note = "WIN", f"Variant behtar (z={z:.2f})"
        else: verdict, note = "LOSS", f"Variant kamzor (z={z:.2f})"
    db.execute("UPDATE experiments SET verdict=?, verdict_note=?, status='DONE' WHERE id=?", (verdict, note, exp_id)); db.commit()
    return {"experiment": exp_id, "verdict": verdict, "note": note,
            "learning_rule": "Sirf WIN/LOSS hi seekh banta hai; INCONCLUSIVE se koi rule nahi badlega"}

# ---------------- AIG-01 Learning store ----------------
def record_outcome(db, action_ref: str, window_days: int, metric: str, before: float, after: float,
                   executed: bool = True) -> dict:
    """Jo action lagu hi nahi hua, usse seekh darj nahi hogi."""
    ensure_v12(db)
    db.execute("CREATE TABLE IF NOT EXISTS outcomes(id INTEGER PRIMARY KEY, action_ref TEXT, window_days INT, metric TEXT, before REAL, after REAL, executed INT, at TEXT)")
    if not executed:
        return {"recorded": False, "reason": "Action lagu hi nahi hua — usse seekh banana jhooth hoga"}
    db.execute("INSERT INTO outcomes(action_ref,window_days,metric,before,after,executed,at) VALUES (?,?,?,?,?,1,?)",
               (action_ref, window_days, metric, before, after, now_utc())); db.commit()
    return {"recorded": True, "delta_pct": round((after - before) / before * 100, 1) if before else None}

def learning_summary(db) -> dict:
    ensure_v12(db)
    db.execute("CREATE TABLE IF NOT EXISTS outcomes(id INTEGER PRIMARY KEY, action_ref TEXT, window_days INT, metric TEXT, before REAL, after REAL, executed INT, at TEXT)")
    rows = [dict(r) for r in db.execute("SELECT * FROM outcomes ORDER BY id DESC LIMIT 50")]
    return {"outcomes": rows, "count": len(rows),
            "note": "Har seekh ke peeche lagu hua action + maapa gaya nateeja hai — kahani par seekh nahi banti"}
