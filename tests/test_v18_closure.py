"""V18 TESTS — data-correctness bandobast: cancelled ginati, exact-line refund, finance-grade milaan, sampurnata, channel raftaar."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from platform_core import ensure_v12
TODAY = datetime.date.today()
def d(n): return (TODAY - datetime.timedelta(days=n)).isoformat()

def _o(st, oid, days_ago, sku, gross, status="Shipped", platform="Amazon", qty=1):
    st.db.execute("INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)", (platform, "default", oid, d(days_ago), status, gross, "INR"))
    st.db.execute("INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)", (platform, "default", oid, oid + "L", sku, "B0", qty, gross, 0))
    st.db.commit()

def test_cancelled_count():
    import analytics as AN
    st = Store(":memory:"); ensure_v12(st.db)
    _o(st, "K1", 1, "SKU", 500); _o(st, "K2", 1, "SKU", 700)
    _o(st, "K3", 1, "SKU", 900, status="Cancelled")
    t = AN.sales_totals(st.db)
    assert t["orders"] == 2 and t["cancelled_orders"] == 1 and t["revenue"] == 1200, t
    st.close()

def test_refund_exact_line():
    import finance as F
    st = Store(":memory:"); ensure_v12(st.db)
    st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default','E1', date('now'), 'Shipped', 1000, 'INR')")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','E1','L1','SKU-E','B0',1,750,0)")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','E1','L2','SKU-E','B0',1,250,0)")
    st.db.commit()
    F.record_refunds(st.db, [{"order_id": "E1", "sku": "SKU-E", "line_id": "L2", "refund": 250}])
    rows = {r["line_id"]: r["refund"] for r in st.db.execute("SELECT line_id, refund FROM order_items")}
    assert rows == {"L1": 0.0, "L2": 250.0}, f"exact line par hi refund lagega: {rows}"
    st.close()

def test_finance_grade_and_completeness():
    import pilot as P
    st = Store(":memory:"); ensure_v12(st.db)
    _o(st, "F1", 2, "SKU-F", 1000)
    _o(st, "F2", 2, "SKU-F", 500)
    _o(st, "F3", 2, "SKU-F", 800)
    st.db.execute("INSERT INTO order_fees VALUES ('Amazon','F1','SKU-F',1000,120)")
    st.db.execute("INSERT INTO order_fees VALUES ('Amazon','F3','SKU-F',850,100)")  # rakam alag — mismatch
    st.db.commit()
    fg = P.finance_grade_matching(st.db, "Amazon", 30)
    assert fg["orders_checked"] == 3 and fg["matched"] == 1 and fg["fee_data_missing"] == 1 and fg["amount_mismatch"] == 1, fg
    assert fg["verdict"].startswith("EXCEPTIONS")
    comp = P.reporting_completeness(st.db, "Amazon", 30)
    assert comp["orders_total"] == 3 and comp["orders_with_fee_data"] == 2 and comp["fee_coverage_pct"] == 66.7, comp
    st.close()

def test_channel_velocity():
    import analytics as AN
    st = Store(":memory:"); ensure_v12(st.db)
    # Amazon: 20 units 10-din span me; Flipkart: 5 units — channel raftaar alag milegi
    _o(st, "VA1", 10, "SKU-V", 0, platform="Amazon", qty=10); _o(st, "VA2", 1, "SKU-V", 0, platform="Amazon", qty=10)
    _o(st, "VF1", 1, "SKU-V", 0, platform="Flipkart", qty=5)
    va = AN.sku_velocity_per_day(st.db, "SKU-V", platform="Amazon")
    vf = AN.sku_velocity_per_day(st.db, "SKU-V", platform="Flipkart")
    assert abs(va - 2.0) < 0.01 and vf == 5.0, (va, vf)
    st.close()

if __name__ == "__main__":
    for t in [test_cancelled_count, test_refund_exact_line, test_finance_grade_and_completeness, test_channel_velocity]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V18 TESTS PASS")
