"""V15 AUDIT-4 TESTS — TACOS matched enforcement, campaign ID maap, coverage gate, order reconciliation, boundary din."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
TODAY = datetime.date.today()
def d(days_ago): return (TODAY - datetime.timedelta(days=days_ago)).isoformat()

def _order(st, oid, days_ago, sku, gross, status="Shipped", platform="Amazon"):
    st.db.execute("INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)", (platform, "default", oid, d(days_ago), status, gross, "INR"))
    st.db.execute("INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)", (platform, "default", oid, oid + "L", sku, "B0", 1, gross, 0))
    st.db.commit()

def test_period_boundary_day():
    from connectors.periods import apply_period_rows
    st = Store(":memory:")
    def ins(ps, pe, sp):
        return lambda: (st.add_search_term("kaju", "C", sp, sp * 2, 5, 1, source="SRC", period_start=ps, period_end=pe), 1)[1]
    assert apply_period_rows(st.db, "SRC", d(13), d(7), ins(d(13), d(7), 100))["status"] == "INSERTED"
    # boundary din (d(7)) dono me hai — takraav, block hona chahiye
    assert apply_period_rows(st.db, "SRC", d(7), d(1), ins(d(7), d(1), 50))["status"] == "BLOCKED_PARTIAL_OVERLAP"
    # agle din se shuru — saaf
    assert apply_period_rows(st.db, "SRC", d(6), d(1), ins(d(6), d(1), 50))["status"] == "INSERTED"
    st.close()

def test_order_status_upsert_and_refund_net():
    import sync_service as SS, finance as F, analytics as AN
    st = Store(":memory:")
    class FakeSP:
        def __init__(self): self.status = "Shipped"
        def get_orders(self, since): return [{"AmazonOrderId": "O1", "PurchaseDate": d(1), "OrderStatus": self.status, "OrderTotal": {"Amount": 500}}]
        def get_order_items(self, oid): return [{"OrderItemId": "L1", "SellerSKU": "SKU-R", "QuantityOrdered": 1, "ItemPrice": {"Amount": 500}}]
    sp = FakeSP()
    SS.sync_amazon_orders(st, "x", sp=sp)
    assert AN.sales_totals(st.db)["revenue"] == 500
    sp.status = "Cancelled"   # order baad me cancel ho gaya — purana IGNORE isey kabhi na pakadta
    SS.sync_amazon_orders(st, "x", sp=sp)
    hdr = st.db.execute("SELECT status FROM order_headers WHERE external_order_id='O1'").fetchone()
    assert hdr["status"] == "Cancelled"
    assert AN.sales_totals(st.db)["revenue"] == 0, "cancelled order ki bikri ginati se bahar"
    # refund: doosra order, 500 me se 200 wapas
    _order(st, "O2", 1, "SKU-R", 500)
    F.record_refunds(st.db, [{"order_id": "O2", "sku": "SKU-R", "refund": 200}])
    assert AN.sales_totals(st.db)["revenue"] == 300, "revenue NET (gross - refund) honi chahiye"
    st.close()

def test_outcome_campaign_id_and_coverage():
    import outcome_engine as OE
    from actions import create_proposal, approve, queue_action, execute
    import auth as A
    from platform_core import ensure_v12, map_campaign
    st = Store(":memory:"); ensure_v12(st.db)
    A.create_user(st.db, "own", "pass1234", "Owner"); owner = {"username": "own", "role": "Owner"}
    map_campaign(st.db, "Amazon", "CAMP-42", "Hero Campaign")
    # khidkiyaan: applied = 8 din pehle; pehle [15..9], baad [8..2] — 7-7 din ke periods
    st.add_search_term("kaju", "Hero Campaign", 100, 150, 10, 1, source="T", period_start=d(15), period_end=d(9))
    st.add_search_term("kaju", "Hero Campaign", 100, 320, 10, 3, source="T", period_start=d(8), period_end=d(2))
    p = create_proposal(st.db, "BID_DOWN", "Amazon", "acc", {"campaign_id": "CAMP-42", "platform": "Amazon"}, "ONE_TAP", "t", "v15-1")
    approve(st.db, p["id"], owner); queue_action(st.db, p["id"], owner)
    class OK:
        def execute(self, payload, action): return {"vendor_ref": "ads:1"}
    execute(st.db, p["id"], owner, OK())
    applied = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
    st.db.execute("UPDATE action_events SET at=? WHERE action_id=? AND to_state='APPLIED_VERIFIED'", (applied, p["id"])); st.db.commit()
    out = OE.measure_due(st.db, windows=(7,))
    assert out["measured"] == 1, f"campaign_id se naam milkar maap hona chahiye: {out}"
    row = st.db.execute("SELECT * FROM outcomes WHERE action_id=?", (p["id"],)).fetchone()
    assert row["metric"] == "campaign_roas_window" and row["success"] == 1
    # coverage gate: sirf 2 order-lines wala SKU action — nateeja nahi banna chahiye
    _order(st, "C1", 12, "SKU-SPARSE", 100); _order(st, "C2", 3, "SKU-SPARSE", 200)
    p2 = create_proposal(st.db, "PRICE_TEST", "Amazon", "acc", {"sku": "SKU-SPARSE"}, "ONE_TAP", "t", "v15-2")
    approve(st.db, p2["id"], owner); queue_action(st.db, p2["id"], owner)
    execute(st.db, p2["id"], owner, OK())
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)).isoformat()
    st.db.execute("UPDATE action_events SET at=? WHERE action_id=? AND to_state='APPLIED_VERIFIED'", (old, p2["id"])); st.db.commit()
    out2 = OE.measure_due(st.db, windows=(7,))
    assert out2["measured"] == 0 and out2["insufficient_data"] >= 1, f"kam data par jhootha nateeja nahi: {out2}"
    st.close()

def test_warroom_matched_tacos():
    from warroom_service import warroom_data as war_room
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    for i in range(5): _order(st, f"W{i}", 2, "SKU-T", 2000)
    st.db.commit()
    wr = war_room(st)
    assert wr["kpis"]["tacos_status"] == "NOT_COMPARABLE" and wr["kpis"]["tacos_pct"] is None, \
        f"ads period data bina TACOS nahi banna chahiye: {wr['kpis'].get('tacos_status')}"
    # V17: MATCHED ke liye 30-din khidki ki >=80% din-coverage chahiye — roz ke periods bharo (kul kharch ₹2000)
    for k in range(30):
        st.add_search_term("badam", "C", round(2000 / 30, 2), 100, 2, 0, source="Amazon Ads API (Reporting v3)",
                           period_start=d(29 - k), period_end=d(29 - k))
    wr2 = war_room(st)
    assert wr2["kpis"]["tacos_status"] == "MATCHED" and abs(wr2["kpis"]["tacos_pct"] - 20.0) < 0.2, wr2["kpis"]
    st.close()

def test_product360_platforms():
    import product360 as P3
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    st.upsert_product("SKU-D", "Dual", "Amazon", 300); st.upsert_product("SKU-D", "Dual", "Flipkart", 280)
    _order(st, "P1", 1, "SKU-D", 900, platform="Amazon"); _order(st, "P2", 1, "SKU-D", 400, platform="Flipkart")
    v = P3.product_360(st.db, "SKU-D")
    assert v["sales_by_platform"]["Amazon"]["revenue"] == 900 and v["sales_by_platform"]["Flipkart"]["revenue"] == 400
    vf = P3.product_360(st.db, "SKU-D", "Flipkart")
    assert vf["sales"]["revenue"] == 400 and vf["platform_view"] == "Flipkart"
    st.close()

if __name__ == "__main__":
    for t in [test_period_boundary_day, test_order_status_upsert_and_refund_net,
              test_outcome_campaign_id_and_coverage, test_warroom_matched_tacos, test_product360_platforms]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V15 TESTS PASS")
