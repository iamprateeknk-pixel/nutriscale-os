"""V13 TESTS — outcome engine, SKU-exact fees, listings publish, 360, filters, security, E2E pilot simulation."""
import os, sys, time, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

def test_outcome_engine_loop():
    """V14 ke baad: maap asal dated khidkiyon se hota hai (jama-kul totals se nahi — woh galat tha)."""
    import outcome_engine as OE
    from actions import create_proposal, approve, queue_action, execute
    import auth as A
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    A.create_user(st.db, "own", "pass1234", "Owner"); owner = {"username": "own", "role": "Owner"}
    today = datetime.date.today()
    def order(oid, days_ago, gross):
        d = (today - datetime.timedelta(days=days_ago)).isoformat()
        st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default',?,?,'Shipped',?,'INR')", (oid, d, gross))
        st.db.execute("INSERT INTO order_items VALUES ('Amazon','default',?,?,'SKU-BR','B0',1,?,0)", (oid, oid + "L", gross))
    order("PB1", 10, 1500)   # pehle ki khidki
    order("PA1", 3, 2600)    # baad ki khidki — behtar
    st.db.commit()
    p = create_proposal(st.db, "BID_DOWN", "Amazon", "acc", {"sku": "SKU-BR"}, "ONE_TAP", "t", "oc-1")
    approve(st.db, p["id"], owner); queue_action(st.db, p["id"], owner)
    class OK:
        def execute(self, payload, action): return {"vendor_ref": "manual:ok"}
    r = execute(st.db, p["id"], owner, OK())
    assert r["state"] == "APPLIED_VERIFIED"
    base = st.db.execute("SELECT baseline FROM action_v12 WHERE id=?", (p["id"],)).fetchone()["baseline"]
    assert base is not None, "execute par baseline tasveer banni chahiye"
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
    st.db.execute("UPDATE action_events SET at=? WHERE action_id=? AND to_state='APPLIED_VERIFIED'", (past, p["id"])); st.db.commit()
    out = OE.measure_due(st.db, windows=(7,))
    assert out["measured"] >= 1
    row = st.db.execute("SELECT * FROM outcomes WHERE action_id=?", (p["id"],)).fetchone()
    assert row["success"] == 1 and row["metric"] == "sku_revenue_window"
    conf = OE.rule_confidence(st.db)
    assert conf and conf[0]["kind"] == "BID_DOWN"
    st.close()

def test_sku_exact_fees():
    import finance as F
    st = Store(":memory:")
    st.db.execute("INSERT OR REPLACE INTO products VALUES ('SKU-X','Exact Wala','Amazon',400,0,0,0,'t')"); st.db.commit()
    F.set_cost(st.db, "SKU-X", 150, 20, approved_by="owner")
    F.import_order_fees(st.db, [{"order_id": "O1", "sku": "SKU-X", "gross": 20000, "fees": 5000}])
    c = F.contribution_v2(st.db, "SKU-X", 400)
    assert c["fee_precision"] == "SKU_EXACT" and abs(c["platform_fees"] - 100.0) < 0.01, "25% asal dar se 400 par 100"
    st.close()

def test_listings_publish_gate():
    import listing_v2 as L
    import capabilities as caps
    st = Store(":memory:")
    d = L.save_draft(st.db, "SKU-L", "Amazon", "Dry Fruit Farm Premium Kaju W320 200g", ["b1"], "", "t")
    r0 = L.publish(st.db, d["id"], "FOOD")  # abhi DRAFT hai
    assert not r0["ok"] and "approve" in r0["error"]
    L.approve_version(st.db, d["id"], "own")
    calls = {}
    class FakeSP:
        def put_listing(self, sku, pt, attrs, mode="VALIDATION_PREVIEW"):
            calls["mode"] = mode
            return {"status": "ACCEPTED", "submissionId": "SUB1", "issues": []}
    r1 = L.publish(st.db, d["id"], "FOOD", sp=FakeSP())
    assert r1["ok"] and r1["mode"] == "VALIDATION_PREVIEW" and calls["mode"] == "VALIDATION_PREVIEW"
    r2 = L.publish(st.db, d["id"], "FOOD", sp=FakeSP(), live=True)
    assert not r2["ok"] and "certified" in r2["error"], "live publish capability bina band rahega"
    caps.set_capability(st.db, "Amazon", "write_listings", "certified", "pilot test")
    r3 = L.publish(st.db, d["id"], "FOOD", sp=FakeSP(), live=True)
    assert r3["ok"] and r3["mode"] == "NORMAL"
    st.close()

def test_sp_financials_parse():
    from connectors.amazon_sp import AmazonSP
    payload = {"payload": {"FinancialEvents": {"ShipmentEventList": [
        {"ShipmentItemList": [{"SellerSKU": "SKU-X",
                               "ItemChargeList": [{"ChargeType": "Principal", "ChargeAmount": {"CurrencyAmount": 400}}],
                               "ItemFeeList": [{"FeeAmount": {"CurrencyAmount": -60}}, {"FeeAmount": {"CurrencyAmount": -25}}]}]}]}}}
    def transport(req):
        if "auth" in req["url"]: return 200, {"access_token": "T"}
        return 200, payload
    sp = AmazonSP(cfg={"client_id": "a", "client_secret": "b", "refresh_token": "c", "marketplace_id": "M"},
                  transport=transport)
    rows = sp.get_order_financials("O1")
    assert rows and rows[0]["gross"] == 400 and rows[0]["fees"] == 85

def test_360_and_filter_and_security():
    import product360, analytics as AN
    from platform_core import ensure_v12
    import auth as A
    st = Store(":memory:"); ensure_v12(st.db)
    st.db.execute("INSERT OR REPLACE INTO products VALUES ('SKU-3','360 Wala','Amazon',300,0,4.2,10,'t')")
    st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default','O3','2026-10-05','Shipped',600,'INR')")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','O3','I3','SKU-3','B0',2,600,0)")
    st.db.execute("INSERT INTO order_headers VALUES ('Flipkart','default','F3','2026-10-05','Shipped',900,'INR')")
    st.db.execute("INSERT INTO order_items VALUES ('Flipkart','default','F3','I4','SKU-3','B0',3,900,0)")
    st.db.commit()
    assert AN.sales_totals(st.db)["revenue"] == 1500
    assert AN.sales_totals(st.db, "Flipkart")["revenue"] == 900, "platform filter kaam karega"
    p = product360.product_360(st.db, "SKU-3")
    assert p["found"] and p["sales"]["revenue"] == 1500
    # SQL injection ki koshish login par — na crash, na andar
    A.create_user(st.db, "admin", "pass1234", "Owner")
    assert A.verify_login(st.db, "admin' OR '1'='1", "x") is None
    assert A.verify_login(st.db, "admin", "' OR 1=1 --") is None
    st.close()

def test_performance_smoke():
    import analytics as AN
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    rows = [("Amazon", "default", f"O{i}", "2026-10-05", "Shipped", 100, "INR") for i in range(2000)]
    st.db.executemany("INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)", rows)
    items = [("Amazon", "default", f"O{i}", f"I{i}", "SKU-P", "B0", 1, 100, 0) for i in range(2000)]
    st.db.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)", items); st.db.commit()
    t0 = time.time(); tot = AN.sales_totals(st.db); dt = time.time() - t0
    assert tot["revenue"] == 200000 and dt < 1.5, f"2000 orders ka hisaab tez hoga ({dt:.2f}s)"
    st.close()

if __name__ == "__main__":
    for t in [test_outcome_engine_loop, test_sku_exact_fees, test_listings_publish_gate,
              test_sp_financials_parse, test_360_and_filter_and_security, test_performance_smoke]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V13 TESTS PASS")
