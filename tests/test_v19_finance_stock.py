"""V19 TESTS — trailing velocity, gross/refund alag milaan, capability naam ekta, channel stock, settlement NON-FINAL."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from platform_core import ensure_v12
TODAY = datetime.date.today()
def d(n): return (TODAY - datetime.timedelta(days=n)).isoformat()

def _o(st, oid, days_ago, sku, gross, qty=1, status="Shipped", platform="Amazon", account="default"):
    st.db.execute("INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)", (platform, account, oid, d(days_ago), status, gross, "INR"))
    st.db.execute("INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)", (platform, account, oid, oid + "L", sku, "B0", qty, gross, 0))
    st.db.commit()

def test_velocity_trailing_only():
    import analytics as AN
    st = Store(":memory:"); ensure_v12(st.db)
    # 90 din pehle ki badi bikri (100 units) trailing khidki se BAHAR hai — all-time/30 wala purana hisaab 3.4+/din deta tha
    _o(st, "OLD", 90, "SKU-T", 0, qty=100)
    _o(st, "N1", 5, "SKU-T", 0, qty=6); _o(st, "N2", 1, "SKU-T", 0, qty=4)   # trailing: 10 units, span 5 din
    _o(st, "CX", 2, "SKU-T", 0, qty=50, status="Cancelled")                  # cancelled bhi bahar
    v = AN.sku_velocity_per_day(st.db, "SKU-T")
    assert abs(v - 2.0) < 0.01, f"trailing 10 units / 5 din = 2.0 hona chahiye, mila {v}"
    st.close()

def test_finance_matching_gross_refund_split():
    import pilot as P, finance as F
    st = Store(":memory:"); ensure_v12(st.db)
    _o(st, "G1", 2, "SKU-G", 1000)
    st.db.execute("UPDATE order_items SET refund=200 WHERE external_order_id='G1'"); st.db.commit()
    F.import_order_fees(st.db, [{"order_id": "G1", "sku": "SKU-G", "gross": 1000, "fees": 150, "refund": 200}])
    fg = P.finance_grade_matching(st.db, "Amazon", 30)
    assert fg["matched"] == 1, f"gross aur refund dono milne par MATCHED hona chahiye (NET-vs-GROSS wali purani galti): {fg}"
    # refund alag ho to REFUND_MISMATCH pakda jayega
    _o(st, "G2", 2, "SKU-G", 500)
    F.import_order_fees(st.db, [{"order_id": "G2", "sku": "SKU-G", "gross": 500, "fees": 80, "refund": 90}])
    fg2 = P.finance_grade_matching(st.db, "Amazon", 30)
    assert fg2["amount_mismatch"] == 1 and "REFUND_MISMATCH" in str(fg2["exceptions"])
    st.close()

def test_capability_name_consistent():
    import capabilities as caps
    st = Store(":memory:")
    caps.seed_capabilities(st.db)
    c = caps.capability(st.db, "Amazon", "write_listings")
    assert c["status"] == "not_certified", f"publish gate jis naam ko dekhta hai wahi registry me hona chahiye: {c}"
    assert caps.capability(st.db, "Amazon", "edit_listing")["status"] == "unavailable"
    st.close()

def test_product360_channel_stock():
    import product360 as P3
    st = Store(":memory:"); ensure_v12(st.db)
    st.upsert_product("SKU-S", "Stocky", "Amazon", 300)
    st.set_inventory("SKU-S", "Amazon FBA", 40); st.set_inventory("SKU-S", "Flipkart Warehouse", 10); st.set_inventory("SKU-S", "Godown", 5)
    va = P3.product_360(st.db, "SKU-S", "Amazon")
    assert va["inventory"]["stock_by_channel"] == {"Amazon": 40, "Flipkart": 10, "unclassified": 5}, va["inventory"]
    assert va["inventory"]["view_qty"] == 40
    st.close()

def test_settlement_nonfinal_label():
    import pilot as P
    st = Store(":memory:"); ensure_v12(st.db)
    _o(st, "S1", 2, "SKU", 2000)
    st.db.execute("INSERT INTO settlements(platform,seller_account,settlement_id,period_start,period_end,gross,fees,refunds,taxes,net) VALUES ('Amazon','default','ST1',?,?,6000,0,0,0,5500)", (d(60), d(1)))
    st.db.commit()
    rep = P.reconciliation_report(st, "Amazon", days=30)
    blk = rep["settlements_overlapping_window"]
    assert blk["gross_full"] == 6000 and "NON_FINAL" in blk["comparison_status"]
    assert blk["gross_prorated_estimate"] < 6000, "60-din ke settlement ka 30-din hissa anumaan se kam hona chahiye"
    st.close()

def test_seller_account_isolation():
    import analytics as AN
    st = Store(":memory:"); ensure_v12(st.db)
    # do seller accounts, ek hi order-id dono me — join seller_account bina mile to rakam double/mix hogi
    _o(st, "DUP", 1, "SKU-A", 100, account="acc1")
    _o(st, "DUP", 1, "SKU-A", 999, account="acc2")
    t = AN.sales_totals(st.db)
    assert t["revenue"] == 1099 and t["orders"] == 2, t  # har khaate ka order alag gina jayega
    rows = AN.sku_sales(st.db)
    assert rows[0]["revenue"] == 1099, rows
    st.close()

if __name__ == "__main__":
    for t in [test_velocity_trailing_only, test_finance_matching_gross_refund_split, test_capability_name_consistent,
              test_product360_channel_stock, test_settlement_nonfinal_label, test_seller_account_isolation]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V19 TESTS PASS")
