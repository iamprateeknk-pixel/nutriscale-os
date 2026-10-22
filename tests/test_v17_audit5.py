"""V17 AUDIT-5 TESTS — asal HTTP regression (360 crash), campaign-map metrics suraksha,
refund line-allocation, scoped reconciliation, backup job."""
import os, sys, subprocess, time, json, urllib.request, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
ROOT = os.path.join(os.path.dirname(__file__), "..")
TODAY = datetime.date.today()
def d(n): return (TODAY - datetime.timedelta(days=n)).isoformat()

def test_http_360_no_crash():
    """P0 regression: asal HTTP par /360?platform= — pehle NameError se 500 crash hota tha."""
    dbf = "/tmp/v17_http.db"
    if os.path.exists(dbf): os.remove(dbf)
    env = dict(os.environ, NUTRISCALE_DB=dbf, PORT="8797",
               NUTRISCALE_OWNER_USER="boss", NUTRISCALE_OWNER_PASSWORD="pass1234")
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "backend", "app.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = "http://127.0.0.1:8797"
        for _ in range(40):
            try:
                urllib.request.urlopen(base + "/api/health", timeout=1); break
            except Exception: time.sleep(0.25)
        def call(path, data=None, token=None):
            req = urllib.request.Request(base + path,
                                         data=json.dumps(data).encode() if data is not None else None,
                                         headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
            with urllib.request.urlopen(req, timeout=5) as r:
                payload = json.loads(r.read())
                return payload.get("data", payload)
        tok = call("/api/v1/auth/login", {"username": "boss", "password": "pass1234"})["token"]
        # product seed (usi DB file me, doosre connection se)
        seed = Store(dbf); seed.upsert_product("SKU-H", "HTTP wala", "Flipkart", 250); seed.close()
        v = call("/api/v1/products/SKU-H/360?platform=Flipkart", token=tok)
        assert v.get("found") and v.get("platform_view") == "Flipkart", v
        v2 = call("/api/v1/products/SKU-H/360", token=tok)
        assert v2.get("found"), v2
    finally:
        proc.terminate(); proc.wait(timeout=5)

def test_campaign_map_preserves_metrics():
    import sync_service as SS
    st = Store(":memory:")
    st.upsert_campaign("Hero", "Amazon", 5000, 9000, source="CSV asal")
    class FakeAds:
        def list_campaigns(self): return [{"campaignId": "C77", "name": "Hero"}]
    SS.sync_campaign_map(st, ads=FakeAds())
    row = st.db.execute("SELECT spend, sales FROM campaigns WHERE name='Hero'").fetchone()
    assert row["spend"] == 5000 and row["sales"] == 9000, "asal metrics ₹0 se kuchle nahi jane chahiye"
    from platform_core import campaign_name_for
    assert campaign_name_for(st.db, "Amazon", "C77") == "Hero"
    st.close()

def test_refund_allocation_lines():
    import finance as F
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default','OA', date('now'), 'Shipped', 1000, 'INR')")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','OA','L1','SKU-M','B0',1,750,0)")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','OA','L2','SKU-M','B0',1,250,0)")
    st.db.commit()
    F.record_refunds(st.db, [{"order_id": "OA", "sku": "SKU-M", "refund": 100}])
    rows = st.db.execute("SELECT line_id, refund FROM order_items ORDER BY line_id").fetchall()
    assert rows[0]["refund"] == 75.0 and rows[1]["refund"] == 25.0, f"anupaat 75/25 hona chahiye: {[dict(r) for r in rows]}"
    assert sum(r["refund"] for r in rows) == 100.0
    st.close()

def test_reconciliation_scoped_and_backup_job():
    import pilot as P
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default','S1',?, 'Shipped', 2000, 'INR')", (d(2),))
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','S1','L1','SKU','B0',1,2000,0)")
    st.db.execute("INSERT INTO settlements(platform,seller_account,settlement_id,period_start,period_end,gross,fees,refunds,taxes,net) VALUES ('Amazon','default','ST1',?,?,1980,100,0,0,1880)", (d(10), d(1)))
    st.db.execute("INSERT INTO settlements(platform,seller_account,settlement_id,period_start,period_end,gross,fees,refunds,taxes,net) VALUES ('Amazon','default','ST-OLD',?,?,99999,0,0,0,99999)", (d(90), d(61)))
    st.db.commit()
    rep = P.reconciliation_report(st, "Amazon", days=30)
    assert rep["orders_in_window"]["net_revenue"] == 2000
    assert rep["settlements_overlapping_window"]["gross_full"] == 1980, "purana settlement khidki se bahar rahega"
    assert rep["window_difference_full_amounts"] == 20.0
    st.close()
    # backup job — file DB par
    import job_handlers as JH
    bf = "/tmp/v17_bk.db"
    if os.path.exists(bf): os.remove(bf)
    stf = Store(bf)
    msg = JH.build_handlers(stf)["backup_restore"]()
    assert "Backup taiyaar" in msg and os.path.exists("/tmp/backups/" + [f for f in os.listdir("/tmp/backups") if f.endswith(".db")][0])
    stf.close()

if __name__ == "__main__":
    for t in [test_campaign_map_preserves_metrics, test_refund_allocation_lines,
              test_reconciliation_scoped_and_backup_job, test_http_360_no_crash]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V17 TESTS PASS")
