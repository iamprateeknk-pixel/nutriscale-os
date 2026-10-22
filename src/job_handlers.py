"""JOB-01 sudhar (V12.1): har job ka APNA handler — pehle daemon sab ko ek hi
daily_cycle() se chalata tha (audit me sahi pakda gaya). Ab:
- data_sync asal sync chalata hai (connector configured ho tab; warna imaandaar SKIP)
- baaki jobs apne-apne asal function se judte hain; jo data maangta hai aur data na ho to SKIP.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

def _data_sync(store):
    from connectors import config as cfg
    ready = [n for n, s in cfg.status_all().items() if s["configured"]]
    if not ready:
        return "SKIP: koi connector configured nahi — aaj data CSV import se aayega (ye nakli sync nahi chalega)"
    out = []
    if "amazon_ads" in ready:
        import datetime
        from connectors.amazon_ads import AmazonAds
        end = datetime.date.today(); start = end - datetime.timedelta(days=2)
        r = AmazonAds().sync_search_terms(store, start.isoformat(), end.isoformat())
        out.append(f"ads terms {r['imported']}")
    if "amazon_sp" in ready:
        import sync_service, datetime
        since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).isoformat()
        r = sync_service.sync_amazon_orders(store, since)
        out.append(f"sp orders {r['orders']}")
    return "Sync hua: " + ", ".join(out) if out else "SKIP: configured connector ka sync function is job me nahi joda"

def _measure_results(store):
    ensure_v12(store.db)
    store.db.execute("CREATE TABLE IF NOT EXISTS outcomes(id INTEGER PRIMARY KEY, action_ref TEXT, window_days INT, metric TEXT, before REAL, after REAL, executed INT, at TEXT)")
    n = store.db.execute("SELECT COUNT(*) c FROM outcomes").fetchone()["c"]
    ex = store.db.execute("SELECT COUNT(*) c FROM experiments WHERE verdict IS NOT NULL").fetchone()["c"]
    return f"Maape gaye nateeje: {n} outcomes, {ex} experiments par verdict — seekh inhi se banti hai"

def _seller_health(store):
    ensure_v12(store.db)
    n = store.db.execute("SELECT COUNT(*) c FROM order_headers").fetchone()["c"]
    if not n: return "SKIP: orders ka data hi nahi — seller health ka andaaz nahi lagega"
    return f"Canonical orders maujud: {n} — ODR/cancel ki asal ginati SP-API sync ke baad milegi (abhi report-import par nirbhar)"

def _stock_reconcile(store):
    from unicommerce_agent import reconcile
    inv = store.db.execute("SELECT COUNT(*) c FROM inventory").fetchone()["c"]
    if not inv: return "SKIP: inventory data nahi — milaan mumkin nahi"
    master = {r["sku"]: r["q"] for r in store.db.execute("SELECT sku, SUM(qty) q FROM inventory GROUP BY sku")}
    channel = {r["sku"]: r["q"] for r in store.db.execute(
        "SELECT sku, SUM(qty) q FROM inventory WHERE location LIKE '%FBA%' OR location LIKE '%Amazon%' GROUP BY sku")}
    r = reconcile(master, channel)
    return f"Stock milaan hua (master vs FBA/Amazon channel): {str(r)[:180]}"

def _war_room(store):
    from warroom_service import warroom_data
    w = warroom_data(store)
    if not w.get("connected"): return "SKIP: asal data nahi — khaali report nahi bhejunga"
    store.add_knowledge("War room report bani (roz ka snapshot)", "job:war_room_report", "high", "F8")
    return "War Room report taiyaar — dashboard par taaza hai"

def _fba_cover(store):
    inv = store.db.execute("SELECT COUNT(*) c FROM inventory").fetchone()["c"]
    if not inv: return "SKIP: inventory nahi — cover ka hisaab nahi banega"
    low = store.db.execute("SELECT sku, SUM(qty) q FROM inventory GROUP BY sku HAVING q<50").fetchall()
    return f"FBA cover parakh: {len(low)} SKU 50 units se neeche — replenishment proposal Ads/Listing se pehle dekho" if low else "FBA cover theek hai"

def _rank_probe(store):
    ensure_v12(store.db)
    n = store.db.execute("SELECT COUNT(*) c FROM rank_observations").fetchone()["c"]
    return (f"Rank observations darj: {n}. Licensed rank feed connected nahi — naye points manual/licensed "
            "source se hi aayenge, system khud bazaar ghurega nahi (policy)")

def _learning_crawl(store):
    from learning_sources import SOURCES
    return f"Seekh ke {len(SOURCES)} sources registry me parkhe gaye — fee/policy badlav ki jaankari inhi se aati hai"

def _learning_summary(store):
    ensure_v12(store.db)
    runs = store.db.execute("SELECT status, COUNT(*) c FROM job_runs WHERE date(started_at)=date('now') GROUP BY status").fetchall()
    s = ", ".join(f"{r['status']}:{r['c']}" for r in runs) or "aaj ke runs abhi darj ho rahe hain"
    return f"Din ka saar — jobs: {s}"

def build_handlers(store) -> dict:
    return {
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
