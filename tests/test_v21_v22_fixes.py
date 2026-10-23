"""V21+V22 TESTS — audit-9 closure: refund accumulation (event ledger), event-ID stability
(reorder/partial), VERIFIED sakht thresholds, BA drop-folder automation, catalog snapshots."""
import os, sys, datetime, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from platform_core import ensure_v12
TODAY = datetime.date.today()
def d(n): return (TODAY - datetime.timedelta(days=n)).isoformat()

def _o(st, oid, days_ago, sku, gross, qty=1, status="Shipped", platform="Amazon", account="default", line=None):
    st.db.execute("INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)", (platform, account, oid, d(days_ago), status, gross, "INR"))
    st.db.execute("INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)", (platform, account, oid, line or (oid + "L"), sku, "B0", qty, gross, 0))
    st.db.commit()

def test_refund_accumulation():
    import finance as F
    st = Store(":memory:"); ensure_v12(st.db)
    _o(st, "R1", 2, "SKU-R", 1000, line="L1")
    # do partial refunds, alag-alag events — purana SET dusre par pehle ko mita deta tha
    F.record_refunds(st.db, [{"order_id": "R1", "sku": "SKU-R", "line_id": "L1", "refund": 100, "event_id": "re-1"}])
    F.record_refunds(st.db, [{"order_id": "R1", "sku": "SKU-R", "line_id": "L1", "refund": 150, "event_id": "re-2"}])
    r = st.db.execute("SELECT refund FROM order_items WHERE external_order_id='R1' AND line_id='L1'").fetchone()
    assert r["refund"] == 250.0, f"partial refunds JUDNE chahiye (100+150), mile {r['refund']}"
    # wahi event dobara — dohari ginati nahi
    F.record_refunds(st.db, [{"order_id": "R1", "sku": "SKU-R", "line_id": "L1", "refund": 150, "event_id": "re-2"}])
    r2 = st.db.execute("SELECT refund FROM order_items WHERE external_order_id='R1' AND line_id='L1'").fetchone()
    assert r2["refund"] == 250.0, "ek hi event dobara aane par rakam dugni nahi hogi"
    st.close()

def test_refund_prorata_cumulative_and_account_scope():
    import finance as F
    st = Store(":memory:"); ensure_v12(st.db)
    _o(st, "R2", 2, "SKU-P", 300, account="acc1", line="LA")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','acc1','R2','LB','SKU-P','B0',1,100,0)"); st.db.commit()
    _o(st, "R2", 2, "SKU-P", 999, account="acc2", line="LA")   # dusra khaata, wahi order+line naam
    F.record_refunds(st.db, [{"order_id": "R2", "sku": "SKU-P", "refund": 60}], seller_account="acc1")
    F.record_refunds(st.db, [{"order_id": "R2", "sku": "SKU-P", "refund": 40}], seller_account="acc1")
    rows = {(r["seller_account"], r["line_id"]): r["refund"] for r in st.db.execute(
        "SELECT seller_account, line_id, refund FROM order_items WHERE external_order_id='R2'")}
    assert rows[("acc1", "LA")] == 75.0 and rows[("acc1", "LB")] == 25.0, \
        f"cumulative 100 ka anupaat 75/25 hona chahiye: {rows}"
    assert rows[("acc2", "LA")] == 0.0, "acc1 ka refund acc2 ki line ko nahi chhuna chahiye"
    st.close()

def _sp_with(payload):
    from connectors.amazon_sp import AmazonSP
    def transport(req):
        if "auth" in req["url"]: return 200, {"access_token": "T"}
        return 200, payload
    return AmazonSP(cfg={"client_id": "a", "client_secret": "b", "refresh_token": "c", "marketplace_id": "M"},
                    transport=transport)

def _ship(posted, sku, gross, fees):
    return {"PostedDate": posted, "ShipmentItemList": [{"SellerSKU": sku,
            "ItemChargeList": [{"ChargeType": "Principal", "ChargeAmount": {"CurrencyAmount": gross}}],
            "ItemFeeList": [{"FeeAmount": {"CurrencyAmount": -fees}}]}]}

def test_event_id_stability():
    import finance as F
    p1 = {"payload": {"FinancialEvents": {"ShipmentEventList": [_ship("2026-10-01", "SKU-A", 500, 60),
                                                                 _ship("2026-10-02", "SKU-A", 500, 60),
                                                                 _ship("2026-10-02", "SKU-B", 300, 40)]}}}
    p2 = {"payload": {"FinancialEvents": {"ShipmentEventList": [_ship("2026-10-02", "SKU-B", 300, 40),
                                                                 _ship("2026-10-02", "SKU-A", 500, 60),
                                                                 _ship("2026-10-01", "SKU-A", 500, 60)]}}}   # wahi events, ulta kram
    ids1 = sorted(r["event_id"] for r in _sp_with(p1).get_order_financials("OX"))
    ids2 = sorted(r["event_id"] for r in _sp_with(p2).get_order_financials("OX"))
    assert ids1 == ids2, "reordered response par event-ids BADALNE nahi chahiye"
    # naya event judne par purane ids sthir
    p3 = {"payload": {"FinancialEvents": {"ShipmentEventList": [_ship("2026-10-01", "SKU-A", 500, 60),
                                                                 _ship("2026-10-02", "SKU-A", 500, 60),
                                                                 _ship("2026-10-02", "SKU-B", 300, 40),
                                                                 _ship("2026-10-03", "SKU-A", 700, 90)]}}}
    ids3 = sorted(r["event_id"] for r in _sp_with(p3).get_order_financials("OX"))
    assert set(ids1) < set(ids3), "naya event judne par purane ids wahi rehne chahiye"
    # aur import par dohari ginati nahi
    st = Store(":memory:"); ensure_v12(st.db)
    F.import_order_fees(st.db, _sp_with(p1).get_order_financials("OX"))
    F.import_order_fees(st.db, _sp_with(p2).get_order_financials("OX"))
    agg = st.db.execute("SELECT SUM(gross) g FROM order_fees WHERE external_order_id='OX'").fetchone()
    assert agg["g"] == 1300, f"reordered re-import par yog 1300 hi rahega, mila {agg['g']}"
    st.close()

def test_verified_threshold_strict():
    import outcome_engine as OE, auth as A
    from actions import create_proposal, approve, queue_action, execute
    st = Store(":memory:"); ensure_v12(st.db)
    A.create_user(st.db, "own", "pass1234", "Owner"); owner = {"username": "own", "role": "Owner"}
    # sirf 2+2 lines — V20 me ye VERIFIED ban jata tha; V21 me LOW_COVERAGE hona chahiye
    _o(st, "B1", 10, "SKU-S", 1000); _o(st, "B2", 11, "SKU-S", 500)
    _o(st, "A1", 3, "SKU-S", 2600); _o(st, "A2", 4, "SKU-S", 400)
    p = create_proposal(st.db, "BID_DOWN", "Amazon", "acc", {"sku": "SKU-S"}, "ONE_TAP", "t", "v21-low")
    approve(st.db, p["id"], owner); queue_action(st.db, p["id"], owner)
    class OK:
        def execute(self, payload, action): return {"vendor_ref": "manual:ok"}
    assert execute(st.db, p["id"], owner, OK())["state"] == "APPLIED_VERIFIED"
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
    st.db.execute("UPDATE action_events SET at=? WHERE action_id=? AND to_state='APPLIED_VERIFIED'", (past, p["id"])); st.db.commit()
    OE.measure_due(st.db, windows=(7,))
    row = st.db.execute("SELECT * FROM outcomes WHERE action_id=?", (p["id"],)).fetchone()
    assert row and row["attribution"] == "LOW_COVERAGE", f"chhota namuna VERIFIED nahi ho sakta: {dict(row) if row else None}"
    conf = OE.rule_confidence(st.db)
    assert all(c["measured"] == 0 for c in conf), "LOW_COVERAGE seekh nahi banega"
    st.close()

def test_dropfolder_automation():
    import brand_analytics as BA
    st = Store(":memory:"); ensure_v12(st.db)
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "sqp.csv"), "w") as f:
            f.write("Search Query,Search Query Volume,Impressions: Total Count,Clicks: Total Count,Purchases: Total Count\n"
                    "kaju w240,500,2000,100,8\n")
        r1 = BA.import_dropfolder(st.db, folder=td)
        assert r1["available"] and r1["imported_files"] == 1 and r1["rows_imported"] == 1, r1
        r2 = BA.import_dropfolder(st.db, folder=td)
        assert r2["imported_files"] == 0, "dusri daud me wahi file dobara import nahi hogi"
    r3 = BA.import_dropfolder(st.db, folder="/nonexistent-xyz")
    assert r3["available"] is False
    # scheduler me job + handler dono maujud
    from scheduler import DAILY_JOBS
    from job_handlers import build_handlers
    assert any(j["job"] == "brand_analytics_import" for j in DAILY_JOBS)
    assert "brand_analytics_import" in build_handlers(st)
    st.close()

def test_catalog_snapshots():
    import catalog_snapshots as CS, import_wizard as W
    st = Store(":memory:"); ensure_v12(st.db)
    assert W.guess_kind(["ASIN", "Title", "BSR", "Price"]) == "catalog_snapshot"
    with tempfile.TemporaryDirectory() as td:
        p1 = os.path.join(td, "cat1.csv")
        with open(p1, "w") as f:
            f.write("ASIN,Seller SKU,Title,Category,BSR,Price,Rating,Reviews\n"
                    "B0XYZ,SKU-C,Dry Fruit Farm Kaju,Grocery,1500,279,4.1,120\n")
        r = CS.import_catalog_csv(st.db, p1, captured_date="2026-10-01")
        assert r["ok"] and r["imported"] == 1, r
        p2 = os.path.join(td, "cat2.csv")
        with open(p2, "w") as f:
            f.write("ASIN,Seller SKU,Title,Category,BSR,Price,Rating,Reviews\n"
                    "B0XYZ,SKU-C,Dry Fruit Farm Kaju,Grocery,900,269,4.2,150\n")
        CS.import_catalog_csv(st.db, p2, captured_date="2026-10-20")
        t = CS.bsr_trend(st.db)
        a = t["asins"][0]
        assert a["bsr_first"] == 1500 and a["bsr_last"] == 900 and a["bsr_change"] == -600, a
        r2 = CS.import_catalog_csv(st.db, p1)
        assert r2["duplicate"] is True
    st.close()

if __name__ == "__main__":
    for t in [test_refund_accumulation, test_refund_prorata_cumulative_and_account_scope,
              test_event_id_stability, test_verified_threshold_strict,
              test_dropfolder_automation, test_catalog_snapshots]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V21/V22 TESTS PASS")
