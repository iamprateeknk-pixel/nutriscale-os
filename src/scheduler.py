"""Scheduler (G3 fix) — roz ke kaam ab sirf likhe hue nahi, registered + chalne wale hain.
Production me yehi jobs cron/Celery-beat par jayengi; yahan runner unhe kram se chalata hai,
koi job fail ho to baaki nahi rukenge — error record hoga aur A09 ko escalate hoga.
"""

DAILY_JOBS = [
    {"time": "06:00", "job": "learning_crawl",        "owner": "A09 Governance", "desc": "Saare sources se nayi seekh, fee/policy alerts pehle"},
    {"time": "06:30", "job": "data_sync",             "owner": "F1 Data Sync",   "desc": "Amazon/Flipkart/Unicommerce ka taaza data"},
    {"time": "07:00", "job": "measure_results",       "owner": "A09 Governance", "desc": "Kal/7-din/14-din purane actions ke results — confidence up/down"},
    {"time": "07:15", "job": "seller_health_check",   "owner": "F10 Health",     "desc": "ODR/cancellation/late dispatch — limit ke paas laal alert"},
    {"time": "07:30", "job": "stock_reconcile",       "owner": "F2 Unicommerce", "desc": "3-way stock milaan — mismatch = oversell rokna"},
    {"time": "08:00", "job": "war_room_report",        "owner": "F8 Report",      "desc": "Roz ki 1-page report tumhe (dashboard + WhatsApp)"},
    {"time": "12:00", "job": "fba_cover_check",        "owner": "F3 Inventory",   "desc": "Days-of-cover — 15 din se kam par replenishment proposal"},
    {"time": "18:00", "job": "rank_probe",             "owner": "A03/A09",        "desc": "Hero keywords ki rank + CTR/CVR record (algorithm seekh)"},
    {"time": "23:00", "job": "daily_learning_summary", "owner": "A09 Governance", "desc": "Aaj kya seekha, kal kya hoga — summary"},
]
WEEKLY_JOBS = [
    {"day": "Sunday", "job": "agent_strength_report", "desc": "Har agent ka Strength Score — pichle Sunday se upar jana chahiye"},
    {"day": "Sunday", "job": "playbook_review",       "desc": "Algorithm playbook + seekhe hue rules ki samiksha"},
]

def run_jobs(handlers: dict, jobs: list = DAILY_JOBS) -> list:
    """handlers: {job_name: callable}. Ek fail ho to baaki chalte rahenge."""
    results = []
    for j in jobs:
        fn = handlers.get(j["job"])
        if fn is None:
            results.append({**j, "status": "SKIPPED_NO_HANDLER (connector/data pending)"}); continue
        try:
            out = fn(); results.append({**j, "status": "DONE", "output": str(out)[:120]})
        except Exception as e:
            results.append({**j, "status": f"FAILED: {e}", "escalate": "A09 Governance"})
    return results
