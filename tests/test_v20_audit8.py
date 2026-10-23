"""V20 TESTS — audit-8 closure: stale velocity, seller-account fee key, fee events (no overwrite),
explicit stock-channel mapping + sellable/unsellable, attribution (coverage/contamination/verified-only),
Brand Analytics importer."""
import os, sys, datetime, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from platform_core import ensure_v12
TODAY = datetime.date.today()
def d(n): return (TODAY - datetime.timedelta(days=n)).isoformat()

def _o(st, oid, days_ago, sku, gross, qty=1, status="Shipped", platform="Amazon", account="default"):
    st.db.execute("INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)", (platform, account, oid, d(days_ago), status, gross, "INR"))
    st.db.execute("INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)", (platform, account, oid, oid + "L", sku, "B0", qty, gross, 0))
    st.db.commit()

def test_velocity_stale_anchor():
    import analytics as AN
    st = Store(":memory:"); ensure_v12(st.db)
    _o(st, "STALE1", 60, "SKU-ST", 500, qty=30)   # 60 din purani bikri — V19 me yahi 'taaza' raftaar ban jati thi
    rep = AN.sku_velocity_report(st.db, "SKU-ST")
    assert rep["velocity_per_day"] == 0.0, f"stale bikri aaj ki khidki se bahar hai, raftaar 0 honi chahiye: {rep}"
    assert rep["stale"] is True and rep["days_since_last_sale"] == 60 and rep["warning"], rep
    assert rep["window_end"] == TODAY.isoformat(), "khidki ka aakhri din AAJ hona chahiye, aakhri bikri nahi"
    _o(st, "FRESH1", 2, "SKU-ST", 300, qty=6)
    rep2 = AN.sku_velocity_report(st.db, "SKU-ST")
    assert rep2["stale"] is False and rep2["velocity_per_day"] > 0, rep2
    st.close()

def test_fee_events_no_overwrite():
    import finance as F
    st = Store(":memory:"); ensure_v12(st.db)
    rows = [
        {"order_id": "E1", "sku": "SKU-E", "event_id": "ev-ship-1", "event_type": "SHIPMENT", "gross": 500, "fees": 60, "refund": 0},
        {"order_id": "E1", "sku": "SKU-E", "event_id": "ev-ship-2", "event_type": "SHIPMENT", "gross": 500, "fees": 60, "refund": 0},
        {"order_id": "E1", "sku": "SKU-E", "event_id": "ev-ref-1", "event_type": "REFUND", "gross": 0, "fees": 0, "refund": 200},
    ]
    r1 = F.import_order_fees(st.db, rows)
    assert r1["imported"] == 3, r1
    agg = st.db.execute("SELECT gross, fees, refund FROM order_fees WHERE external_order_id='E1' AND sku='SKU-E'").fetchone()
    assert agg["gross"] == 1000 and agg["fees"] == 120 and agg["refund"] == 200, \
        f"do shipment events JUDNE chahiye, overwrite nahi: {dict(agg)}"
    r2 = F.import_order_fees(st.db, rows)   # wahi events dobara sync — dohari ginati nahi
    assert r2["imported"] == 0, r2
    agg2 = st.db.execute("SELECT gross FROM order_fees WHERE external_order_id='E1' AND sku='SKU-E'").fetchone()
    assert agg2["gross"] == 1000, "re-import par rakam dugni nahi honi chahiye"
    st.close()

def test_fee_seller_account_separation():
    import finance as F, pilot as P
    st = Store(":memory:"); ensure_v12(st.db)
    _o(st, "DUP", 2, "SKU-A", 1000, account="acc1")
    _o(st, "DUP", 2, "SKU-A", 1000, account="acc2")   # ek hi order-id, do khaate
    F.import_order_fees(st.db, [{"order_id": "DUP", "sku": "SKU-A", "gross": 1000, "fees": 100, "refund": 0}],
                        seller_account="acc1")
    fg = P.finance_grade_matching(st.db, "Amazon", 30)
    assert fg["matched"] == 1 and fg["fee_data_missing"] == 1, \
        f"acc1 ki fees acc2 ke order ko MATCHED nahi bana sakti: {fg}"
    exc = [e for e in fg["exceptions"] if e["issue"] == "FEE_DATA_MISSING"]
    assert exc and exc[0]["account"] == "acc2", fg["exceptions"]
    st.close()

def test_order_fees_migration():
    st = Store(":memory:")
    st.db.execute("DROP TABLE IF EXISTS order_fees")
    st.db.execute("""CREATE TABLE order_fees(platform TEXT, external_order_id TEXT, sku TEXT,
                     gross REAL, fees REAL, refund REAL DEFAULT 0,
                     PRIMARY KEY(platform, external_order_id, sku))""")
    st.db.execute("INSERT INTO order_fees VALUES ('Amazon','OLD1','SKU-O',700,90,0)"); st.db.commit()
    ensure_v12(st.db)
    cols = [c[1] for c in st.db.execute("PRAGMA table_info(order_fees)")]
    assert "seller_account" in cols, "purani table par seller_account aana chahiye"
    r = st.db.execute("SELECT seller_account, gross FROM order_fees WHERE external_order_id='OLD1'").fetchone()
    assert r["seller_account"] == "default" and r["gross"] == 700, "purana data 'default' khaate me surakshit rahe"
    st.close()

def test_stock_mapping_and_sellable():
    import product360 as P3, stock as ST
    st = Store(":memory:"); ensure_v12(st.db)
    st.upsert_product("SKU-M", "Map Wala", "Amazon", 300)
    st.upsert_product("SKU-M", "Map Wala", "Flipkart", 310)
    st.set_inventory("SKU-M", "Godown", 50)                       # naam-andaz se unclassified
    st.set_inventory("SKU-M", "Amazon FBA", 40, sellable=30, unsellable=10)
    p0 = P3.product_360(st.db, "SKU-M")
    assert p0["inventory"]["stock_by_channel"].get("unclassified") == 50, p0["inventory"]
    ST.set_stock_channel(st.db, "Godown", "Flipkart", "owner")    # explicit mapping heuristic ko hara degi
    p1 = P3.product_360(st.db, "SKU-M", "Flipkart")
    assert p1["inventory"]["stock_by_channel"].get("Flipkart") == 50, p1["inventory"]
    assert p1["inventory"]["view_qty"] == 50
    godown = [l for l in p1["inventory"]["by_location"] if l["location"] == "Godown"][0]
    assert godown["channel_basis"] == "EXPLICIT", godown
    pa = P3.product_360(st.db, "SKU-M", "Amazon")
    assert pa["inventory"]["stock_by_channel"]["Amazon"] == 30, "channel hisaab SELLABLE par hoga"
    assert pa["inventory"]["unsellable_by_channel"]["Amazon"] == 10, pa["inventory"]
    assert pa["inventory"]["view_qty"] == 30
    # V21: availability ka saboot alag — FBA ka sellable VERIFIED, Godown ka stock UNKNOWN
    assert pa["inventory"]["sellable_verified_by_channel"]["Amazon"] == 30, pa["inventory"]
    assert pa["inventory"]["unknown_availability_by_channel"]["Flipkart"] == 50, pa["inventory"]
    fba = [l for l in pa["inventory"]["by_location"] if l["location"] == "Amazon FBA"][0]
    assert fba["availability"] == "VERIFIED"
    st.close()

def _mk_action(st, owner, kind, platform, payload, key):
    from actions import create_proposal, approve, queue_action, execute
    p = create_proposal(st.db, kind, platform, "acc", payload, "ONE_TAP", "t", key)
    approve(st.db, p["id"], owner); queue_action(st.db, p["id"], owner)
    class OK:
        def execute(self, payload, action): return {"vendor_ref": "manual:ok"}
    r = execute(st.db, p["id"], owner, OK())
    assert r["state"] == "APPLIED_VERIFIED", r
    return p["id"]

def _backdate(st, action_id, days=8):
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
    st.db.execute("UPDATE action_events SET at=? WHERE action_id=? AND to_state='APPLIED_VERIFIED'", (past, action_id))
    st.db.commit()

def test_attribution_verified_clean():
    import outcome_engine as OE, auth as A
    st = Store(":memory:"); ensure_v12(st.db)
    A.create_user(st.db, "own", "pass1234", "Owner"); owner = {"username": "own", "role": "Owner"}
    # V21 VERIFIED threshold: kul >=8 lines + har khidki >=2 order-din — fixture usi ke hisaab se bhara hua
    _o(st, "B1", 10, "SKU-V", 500); _o(st, "B2", 11, "SKU-V", 500); _o(st, "B3", 12, "SKU-V", 500); _o(st, "B4", 13, "SKU-V", 500)
    _o(st, "A1", 3, "SKU-V", 750); _o(st, "A2", 4, "SKU-V", 750); _o(st, "A3", 5, "SKU-V", 750); _o(st, "A4", 6, "SKU-V", 750)
    aid = _mk_action(st, owner, "BID_DOWN", "Amazon", {"sku": "SKU-V"}, "v20-clean")
    _backdate(st, aid)
    out = OE.measure_due(st.db, windows=(7,))
    assert out["measured"] >= 1, out
    row = st.db.execute("SELECT * FROM outcomes WHERE action_id=?", (aid,)).fetchone()
    assert row["attribution"] == "VERIFIED" and row["success"] == 1, dict(row)
    assert row["coverage_pct"] is not None
    conf = OE.rule_confidence(st.db)
    assert conf and conf[0]["measured"] == 1 and conf[0]["win_rate"] == 1.0, conf
    st.close()

def test_attribution_contaminated():
    import outcome_engine as OE, auth as A
    st = Store(":memory:"); ensure_v12(st.db)
    A.create_user(st.db, "own", "pass1234", "Owner"); owner = {"username": "own", "role": "Owner"}
    _o(st, "B1", 10, "SKU-C", 1000, platform="Amazon"); _o(st, "B2", 11, "SKU-C", 500, platform="Amazon")
    _o(st, "A1", 3, "SKU-C", 2600, platform="Amazon"); _o(st, "A2", 4, "SKU-C", 400, platform="Amazon")
    a1 = _mk_action(st, owner, "BID_DOWN", "Amazon", {"sku": "SKU-C"}, "v20-c1")
    a2 = _mk_action(st, owner, "PRICE_CHANGE", "Flipkart", {"sku": "SKU-C"}, "v20-c2")  # dusra channel, wahi SKU, wahi samay
    _backdate(st, a1); _backdate(st, a2)
    OE.measure_due(st.db, windows=(7,))
    rows = st.db.execute("SELECT attribution, success FROM outcomes WHERE metric LIKE 'sku_revenue%'").fetchall()
    assert rows and all(r["attribution"] == "CONTAMINATED" and r["success"] is None for r in rows), \
        f"cross-channel dusra action ho to nateeja kisi ek ke naam nahi lagna chahiye: {[dict(r) for r in rows]}"
    conf = OE.rule_confidence(st.db)
    for c in conf: assert c["measured"] == 0, f"CONTAMINATED nateeja seekh nahi ban sakta: {c}"
    st.close()

def test_brand_analytics_import():
    import brand_analytics as BA, import_wizard as W
    st = Store(":memory:"); ensure_v12(st.db)
    csv_text = ("Search Query,Search Query Volume,Impressions: Total Count,Impressions: Brand Count,"
                "Clicks: Total Count,Clicks: Brand Count,Cart Adds: Total Count,Cart Adds: Brand Count,"
                "Purchases: Total Count,Purchases: Brand Count\n"
                "brazil nuts 200g,1200,5000,1500,300,120,60,30,25,10\n"
                "cranberry dry fruit,800,3000,900,150,60,30,12,10,4\n")
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(csv_text); path = f.name
    assert W.guess_kind(["Search Query", "Search Query Volume"]) == "brand_analytics"
    r = BA.import_brand_analytics(st.db, path, period=("2026-10-01", "2026-10-07"))
    assert r["ok"] and r["report_type"] == "SQP" and r["imported"] == 2, r
    s = BA.summary(st.db)
    assert s["available"] and s["top_queries_by_purchases"][0]["query"] == "brazil nuts 200g", s
    assert s["top_queries_by_purchases"][0]["brand_purchase_share_pct"] == 40.0, s
    r2 = BA.import_brand_analytics(st.db, path)
    assert r2["duplicate"] is True and r2["imported"] == 0, "wahi file dobara nahi ghusegi"
    st.close()

def test_http_new_endpoints():
    """V17 ki seekh: naye endpoints asal HTTP par — brand-analytics + stock channel-map (GET/POST)."""
    import subprocess, time, json, urllib.request
    ROOT = os.path.join(os.path.dirname(__file__), "..")
    dbf = "/tmp/v20_http.db"
    if os.path.exists(dbf): os.remove(dbf)
    env = dict(os.environ, NUTRISCALE_DB=dbf, PORT="8799",
               NUTRISCALE_OWNER_USER="boss", NUTRISCALE_OWNER_PASSWORD="pass1234")
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "backend", "app.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = "http://127.0.0.1:8799"
        for _ in range(40):
            try:
                urllib.request.urlopen(base + "/health", timeout=1); break
            except Exception: time.sleep(0.25)
        def call(path, data=None, token=None):
            req = urllib.request.Request(base + path,
                                         data=json.dumps(data).encode() if data is not None else None,
                                         headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
            with urllib.request.urlopen(req, timeout=5) as r:
                payload = json.loads(r.read())
                return payload.get("data", payload)
        tok = call("/api/v1/auth/login", {"username": "boss", "password": "pass1234"})["token"]
        ba = call("/api/v1/brand-analytics", token=tok)
        assert ba["available"] is False, "data bina available=False hi imaandaari hai"
        seed = Store(dbf); seed.set_inventory("SKU-H", "Godown", 12); seed.close()
        m0 = call("/api/v1/stock/channel-map", token=tok)
        g = [l for l in m0["locations"] if l["location"] == "Godown"][0]
        assert g["channel"] == "unclassified" and g["basis"] == "UNCLASSIFIED", g
        call("/api/v1/stock/channel-map", {"location": "Godown", "channel": "Amazon"}, token=tok)
        m1 = call("/api/v1/stock/channel-map", token=tok)
        g1 = [l for l in m1["locations"] if l["location"] == "Godown"][0]
        assert g1["channel"] == "Amazon" and g1["basis"] == "EXPLICIT", g1
    finally:
        proc.terminate(); proc.wait(timeout=5)

if __name__ == "__main__":
    for t in [test_velocity_stale_anchor, test_fee_events_no_overwrite, test_fee_seller_account_separation,
              test_order_fees_migration, test_stock_mapping_and_sellable, test_attribution_verified_clean,
              test_attribution_contaminated, test_brand_analytics_import, test_http_new_endpoints]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V20 TESTS PASS")
