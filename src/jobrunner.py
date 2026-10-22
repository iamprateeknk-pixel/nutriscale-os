"""JOB-01 Durable Job Runner — IST samay par chalne wale kaam, DB me state ke saath.
Restart ke baad bhi next_run/attemp yaad rehte hain; ek job fail ho to baaki chalte hain;
lock se duplicate run nahi hota; 3 koshish ke baad dead-letter (job_runs me darj).
Asal daemon: `python3 src/jobrunner.py --daemon` (har 60 sec due jobs parkhta hai).
"""
import os, sys, time, datetime, socket
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc
from scheduler import DAILY_JOBS

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
MAX_ATTEMPTS = 3

def _next_run(job_time: str, from_dt: datetime.datetime) -> datetime.datetime:
    h, m = map(int, job_time.split(":"))
    cand = from_dt.replace(hour=h, minute=m, second=0, microsecond=0)
    if cand <= from_dt: cand += datetime.timedelta(days=1)
    return cand

def seed_jobs(db, jobs=DAILY_JOBS):
    ensure_v12(db)
    now = datetime.datetime.now(IST)
    for j in jobs:
        db.execute("INSERT OR IGNORE INTO job_state(job,next_run,attempts) VALUES (?,?,0)",
                   (j["job"], _next_run(j["time"], now).isoformat())); db.commit()

def run_due_jobs(db, handlers: dict, now: datetime.datetime = None) -> list:
    """Abhi due jobs chalao. Handlers na hon to SKIPPED (jhootha DONE nahi) — purana niyam."""
    ensure_v12(db); seed_jobs(db)
    now = now or datetime.datetime.now(IST)
    results, me = [], socket.gethostname()
    for row in db.execute("SELECT * FROM job_state").fetchall():
        st = dict(row)
        if st["locked_by"] and st["locked_by"] != me: continue
        if st["next_run"] and datetime.datetime.fromisoformat(st["next_run"]) > now: continue
        job = st["job"]
        db.execute("UPDATE job_state SET locked_by=?, locked_at=? WHERE job=?", (me, now_utc(), job)); db.commit()
        started = now_utc()
        fn = handlers.get(job)
        if fn is None:
            status, detail = "SKIPPED", "handler registered nahi"
        else:
            try: status, detail = "DONE", str(fn())[:300]
            except Exception as e: status, detail = "FAILED", f"{type(e).__name__}: {e}"[:300]
        attempts = (st["attempts"] or 0) + (1 if status == "FAILED" else 0)
        nxt = _next_run(next(j["time"] for j in DAILY_JOBS if j["job"] == job), now)
        if status == "FAILED" and attempts < MAX_ATTEMPTS:
            nxt = now + datetime.timedelta(minutes=15 * attempts)   # backoff se dobara koshish
        db.execute("UPDATE job_state SET next_run=?, last_run=?, last_status=?, attempts=?, locked_by=NULL WHERE job=?",
                   (nxt.isoformat(), started, status, attempts if status == "FAILED" else 0, job))
        db.execute("INSERT INTO job_runs(job,started_at,finished_at,status,detail) VALUES (?,?,?,?,?)",
                   (job, started, now_utc(), status, detail)); db.commit()
        results.append({"job": job, "status": status, "detail": detail, "next_run": nxt.isoformat()})
    return results

def jobs_status(db) -> list:
    ensure_v12(db); seed_jobs(db)
    return [dict(r) for r in db.execute("SELECT job,next_run,last_run,last_status,attempts FROM job_state ORDER BY next_run")]

def daemon():
    from db_store import Store
    from agents.governance import GovernanceAgent
    print("NutriScale Job Runner daemon shuru (IST). Band karne ke liye Ctrl+C.")
    while True:
        store = Store()
        try:
            gov = GovernanceAgent(store)
            handlers = {j["job"]: (lambda g=gov: g.daily_cycle()) for j in DAILY_JOBS}
            out = run_due_jobs(store.db, handlers)
            for r in out: print(r, flush=True)
        finally: store.close()
        time.sleep(60)

if __name__ == "__main__":
    if "--daemon" in sys.argv: daemon()
    else:
        from db_store import Store
        s = Store()
        try: print(jobs_status(s.db))
        finally: s.close()
