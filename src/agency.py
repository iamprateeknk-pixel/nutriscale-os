"""AGY-01 Agency Scorecard — agency ne kaha vs asal me hua.
Agency ke 'humne kar diya' par nahi, vendor-confirmed badlav (action_events) par hisaab hoga.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

def _tables(db):
    ensure_v12(db)
    db.execute("""CREATE TABLE IF NOT EXISTS agency_tasks(
      id INTEGER PRIMARY KEY, title TEXT, platform TEXT, due_date TEXT, status TEXT DEFAULT 'PLANNED',
      evidence_ref TEXT, created_at TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS agency_fees(
      id INTEGER PRIMARY KEY, month TEXT, amount REAL, platform TEXT, note TEXT)""")
    db.commit()

def add_task(db, title, platform="Amazon", due_date="") -> dict:
    _tables(db)
    cur = db.execute("INSERT INTO agency_tasks(title,platform,due_date,created_at) VALUES (?,?,?,?)",
                     (title, platform, due_date, now_utc())); db.commit()
    return {"id": cur.lastrowid, "status": "PLANNED"}

def complete_task(db, task_id, evidence_ref="") -> dict:
    _tables(db)
    if not evidence_ref:
        return {"ok": False, "error": "Saboot (badlav ka ref/screenshot) bina task 'ho gaya' nahi mana jayega"}
    db.execute("UPDATE agency_tasks SET status='DONE', evidence_ref=? WHERE id=?", (evidence_ref, task_id)); db.commit()
    return {"ok": True, "status": "DONE"}

def add_fee(db, month, amount, platform="All", note="") -> dict:
    _tables(db)
    db.execute("INSERT INTO agency_fees(month,amount,platform,note) VALUES (?,?,?,?)", (month, amount, platform, note)); db.commit()
    return {"ok": True}

def scorecard(db, month: str = None) -> dict:
    _tables(db)
    tasks = [dict(r) for r in db.execute("SELECT * FROM agency_tasks ORDER BY id DESC LIMIT 100")]
    fees = db.execute("SELECT COALESCE(SUM(amount),0) s FROM agency_fees" + (" WHERE month=?" if month else ""),
                      ((month,) if month else ())).fetchone()["s"]
    done = [t for t in tasks if t["status"] == "DONE"]
    verified_changes = db.execute("""SELECT COUNT(*) c FROM action_events e JOIN action_v12 a ON a.id=e.action_id
                                     WHERE e.to_state='APPLIED_VERIFIED'""").fetchone()["c"]
    return {"tasks_total": len(tasks), "tasks_done_with_evidence": len(done),
            "tasks_pending": len(tasks) - len(done), "fees_total": fees,
            "vendor_verified_changes": verified_changes,
            "completion_pct": round(len(done) / len(tasks) * 100, 1) if tasks else None,
            "note": "Scorecard agency ke dave par nahi — saboot wale kaamo aur verified badlavon par banta hai"}
