"""JOB-01 fix (V12.1): every job has ITS OWN handler — previously the daemon ran everything through a single
daily_cycle() (correctly caught in an audit). Now:
- data_sync runs a real sync (when a connector is configured; otherwise an honest SKIP)
- other jobs call their own real functions; a job that needs data SKIPs when there is none.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

def _data_sync(store):
    from connectors import config as cfg
    ready = [n for n, s in cfg.status_all().items() if s["configured"]]
    if not ready:
        return "SKIP: no connector configured — today's data comes from CSV upload (no fake sync is run)"
    out = []
    import datetime
    today = datetime.date.today()
    if "amazon_ads" in ready:
        from connectors.amazon_ads import AmazonAds
        import sync_service
        yday = (today - datetime.timedelta(days=1)).isoformat()
        # V14: one-day window — each day exactly once, so overlaps cannot happen
        r = AmazonAds().sync_search_terms(store, yday, yday)
        out.append(f"ads terms {r['imported']} ({r.get('overlap_status', '')})")
        try:
            m = sync_service.sync_campaign_map(store)
            out.append(f"campaign naksha {m['mapped']}")
        except Exception as e:
            out.append(f"campaign naksha skip: {type(e).__name__}")
    if "amazon_sp" in ready:
        import sync_service
        since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).isoformat()
        r = sync_service.sync_amazon_orders(store, since)
        out.append(f"sp orders {r['orders']}")
        try:
            f = sync_service.sync_order_fees(store, days=3)
            out.append(f"order fees {f['fee_rows']}")
        except Exception as e:
            out.append(f"fees skip: {type(e).__name__}")
    if "flipkart" in ready:
        import sync_service
        r = sync_service.sync_flipkart(store, (today - datetime.timedelta(days=2)).isoformat(), today.isoformat())
        out.append(f"flipkart items {r['orders_items']}")
    return "Synced: " + ", ".join(out) if out else "SKIP: the configured connector's sync function is not wired into this job"

def _measure_results(store):
    import outcome_engine as OE
    r = OE.measure_due(store.db)
    conf = OE.rule_confidence(store.db)
    n = store.db.execute("SELECT COUNT(*) c FROM outcomes").fetchone()["c"]
    s = "; ".join(f"{c['kind']}: win rate {c['win_rate']} ({c['measured']} measured)" for c in conf) or "no measured outcomes yet"
    import agent_brain as AB
    lb = AB.learn_from_outcomes(store.db)  # V23: new outcomes go straight into playbook confidence
    s += f"; playbook update {lb['applied']}"
    return f"This cycle: {r['measured']} new window-measured outcomes (insufficient data: {r['insufficient_data']}); total {n}. Learning: {s}"

def _seller_health(store):
    ensure_v12(store.db)
    n = store.db.execute("SELECT COUNT(*) c FROM order_headers").fetchone()["c"]
    if not n: return "SKIP: no order data — seller health cannot be assessed"
    return f"Canonical orders present: {n} — real ODR/cancel counts arrive after SP-API sync (currently relies on report imports)"

def _stock_reconcile(store):
    from unicommerce_agent import reconcile
    inv = store.db.execute("SELECT COUNT(*) c FROM inventory").fetchone()["c"]
    if not inv: return "SKIP: no inventory data — reconciliation not possible"
    master = {r["sku"]: r["q"] for r in store.db.execute("SELECT sku, SUM(qty) q FROM inventory GROUP BY sku")}
    channel = {r["sku"]: r["q"] for r in store.db.execute(
        "SELECT sku, SUM(qty) q FROM inventory WHERE location LIKE '%FBA%' OR location LIKE '%Amazon%' GROUP BY sku")}
    r = reconcile(master, channel)
    return f"Stock reconciled (master vs FBA/Amazon channel): {str(r)[:180]}"

def _war_room(store):
    from warroom_service import warroom_data
    w = warroom_data(store)
    if not w.get("connected"): return "SKIP: no real data — an empty report is not sent"
    store.add_knowledge("War room report created (daily snapshot)", "job:war_room_report", "high", "F8")
    return "War Room report ready — fresh on the dashboard"

def _fba_cover(store):
    """V12.2: real days of cover — how many days stock lasts at the daily sales rate (canonical).
    The old '<50 units' guess is gone: 40 units selling 1/day is 40 safe days."""
    inv = store.db.execute("SELECT COUNT(*) c FROM inventory").fetchone()["c"]
    if not inv: return "SKIP: no inventory — cover cannot be calculated"
    import analytics as AN
    from fba_planner import days_of_cover
    alerts, ok = [], 0
    for r in store.db.execute("SELECT sku, SUM(qty) q FROM inventory GROUP BY sku"):
        vel = AN.sku_velocity_per_day(store.db, r["sku"])
        if vel <= 0:
            continue  # no sales data — no claim about cover
        cover = days_of_cover(int(r["q"]), vel)
        if cover < 21: alerts.append(f"{r['sku']}: {cover:.0f} days (stock {int(r['q'])}, sales {vel:.1f}/day)")
        else: ok += 1
    if alerts:
        return "FBA cover WARNING (under 21 days): " + "; ".join(alerts[:5]) + " — time to replenish"
    return f"FBA cover is fine ({ok} SKUs at 21+ days)"

def _rank_probe(store):
    ensure_v12(store.db)
    n = store.db.execute("SELECT COUNT(*) c FROM rank_observations").fetchone()["c"]
    return (f"Rank observations recorded: {n}. No licensed rank feed connected — new points only come from a manual/licensed "
            "source; the system does not scrape the marketplace itself (policy)")

def _learning_crawl(store):
    """V23: the real learning cycle instead of a placeholder — refresh the research playbook, confidence from VERIFIED
    outcomes, new lessons from your data (search terms / SQP). Warns about stale research rules (90+ days)."""
    import agent_brain as AB, marketplace_knowledge as MK
    r = AB.daily_learning_cycle(store)
    stale = MK.stale_rules()
    msg = (f"Playbook: +{r['playbook']['added']} new, {r['playbook']['refreshed']} refreshed; "
           f"{r['outcomes']['applied']} updates from outcomes; {r['own_data']['lessons_updated']} lessons from your data")
    return msg + (f"; RE-RESEARCH: {', '.join(stale[:5])}" if stale else "")

def _learning_summary(store):
    ensure_v12(store.db)
    runs = store.db.execute("SELECT status, COUNT(*) c FROM job_runs WHERE date(started_at)=date('now') GROUP BY status").fetchall()
    s = ", ".join(f"{r['status']}:{r['c']}" for r in runs) or "today's runs are still being recorded"
    return f"Daily summary — jobs: {s}"

def _backup(store):
    """Daily backup into data/backups/ — the restore test runs inside create_backup."""
    import os, datetime
    import ops_finance as OF
    from db_store import DEFAULT_PATH
    db_path = getattr(store, "path", None) or DEFAULT_PATH
    if db_path == ":memory:":
        # An in-memory DB (tests) has no file to back up — it used to create 'backups/' in the cwd (junk in the repo)
        return "SKIP: in-memory DB — nothing to back up to a file"
    dest_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups"); os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"growth_os-{datetime.date.today().isoformat()}.db")
    r = OF.create_backup(db_path, dest)
    return f"Backup ready: {os.path.basename(dest)} ({r['tables']} tables, restore-tested)" if r["ok"] else "Backup failed"

def _brand_analytics_import(store):
    """V22: drop-folder automation — new SQP/SCP files are imported automatically; already-seen files are blocked by SHA."""
    import brand_analytics as BA
    r = BA.import_dropfolder(store.db)
    if not r["available"]: return r["note"]
    return f"Brand Analytics: {r['files_seen']} file(s) seen, {r['imported_files']} new imported ({r['rows_imported']} rows)"

def _growth_autopilot(store):
    """V25: approval-gated proposals from playbook findings — never changes anything live itself."""
    import growth_autopilot as GA
    r = GA.run(store)
    return (f"Autopilot: {len(r['created'])} new proposals, {r['already_proposed_this_week']} already proposed this week"
            + (f", {r['capped']} left for the next run" if r["capped"] else "")
            + (f", {len(r['skipped_disabled_rules'])} skipped because their rule is disabled" if r["skipped_disabled_rules"] else ""))

def _weekly_report(store, today=None):
    """V25: the scheduler only runs daily jobs — the weekly report is only built on Sunday (IST)."""
    import datetime
    t = today or (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()
    if t.weekday() != 6: return "SKIP: today is not Sunday — the report is built on Sunday"
    import growth_autopilot as GA
    r = GA.weekly_report(store, t)
    return f"Weekly report created: {r['saved_to'] or 'in-memory'}"

def build_handlers(store) -> dict:
    return {
        "growth_autopilot": lambda: _growth_autopilot(store),
        "weekly_report": lambda: _weekly_report(store),
        "brand_analytics_import": lambda: _brand_analytics_import(store),
        "backup_restore": lambda: _backup(store),
        "learning_crawl": lambda: _learning_crawl(store),
        "data_sync": lambda: _data_sync(store),
        "measure_results": lambda: _measure_results(store),
        "seller_health_check": lambda: _seller_health(store),
        "stock_reconcile": lambda: _stock_reconcile(store),
        "war_room_report": lambda: _war_room(store),
        "fba_cover_check": lambda: _fba_cover(store),
        "rank_probe": lambda: _rank_probe(store),
        "daily_learning_summary": lambda: _learning_summary(store),
    }
