"""Scheduler (G3 fix) — daily jobs are not just listed but registered and actually run.
In production these jobs move to cron/Celery-beat; here the runner executes them in order,
and one failing job never stops the others — the error is recorded and escalated to A09.
"""

DAILY_JOBS = [
    {"time": "06:00", "job": "learning_crawl",        "owner": "A09 Governance", "desc": "Refresh rules + learn from outcomes and your data; fee/policy alerts first"},
    {"time": "06:30", "job": "data_sync",             "owner": "F1 Data Sync",   "desc": "Fresh Amazon/Flipkart/Unicommerce data"},
    {"time": "06:45", "job": "brand_analytics_import", "owner": "F1 Data Sync",  "desc": "Auto-import new files from the Brand Analytics drop folder (SQP/SCP)"},
    {"time": "07:00", "job": "measure_results",       "owner": "A09 Governance", "desc": "Results of actions from yesterday/7/14 days ago — confidence up/down"},
    {"time": "07:15", "job": "seller_health_check",   "owner": "F10 Health",     "desc": "ODR/cancellation/late dispatch — red alert near the limits"},
    {"time": "07:30", "job": "stock_reconcile",       "owner": "F2 Unicommerce", "desc": "3-way stock milaan — mismatch = oversell rokna"},
    {"time": "07:45", "job": "growth_autopilot",      "owner": "A06/A03",        "desc": "Playbook findings -> approval-gated proposals (negatives, harvest, SQP scale, stock-out pause)"},
    {"time": "08:00", "job": "war_room_report",        "owner": "F8 Report",      "desc": "Your daily one-page report (dashboard)"},
    {"time": "12:00", "job": "fba_cover_check",        "owner": "F3 Inventory",   "desc": "Days of cover — replenishment alert under 21 days"},
    {"time": "18:00", "job": "rank_probe",             "owner": "A03/A09",        "desc": "Record hero keyword rank + CTR/CVR (algorithm learning)"},
    {"time": "21:00", "job": "weekly_report",          "owner": "A09 Governance", "desc": "Sundays only: weekly growth report (data/reports/)"},
    {"time": "23:00", "job": "daily_learning_summary", "owner": "A09 Governance", "desc": "What was learned today, what happens tomorrow — summary"},
    {"time": "23:30", "job": "backup_restore",       "owner": "OPS-01",         "desc": "Nightly DB backup (data/backups/) with restore test"},
]
WEEKLY_JOBS = [
    {"day": "Sunday", "job": "agent_strength_report", "desc": "Strength score per agent — should rise week over week"},
    {"day": "Sunday", "job": "playbook_review",       "desc": "Review the algorithm playbook + learned rules"},
]

def run_jobs(handlers: dict, jobs: list = DAILY_JOBS) -> list:
    """handlers: {job_name: callable}. If one fails the rest keep running."""
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
