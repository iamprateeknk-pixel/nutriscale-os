"""V14 AUDIT-3 TESTS — khidki-maap, overlap niyam, platform pehchan, scheduled sync jod, publish endpoint."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

def test_platform_identity():
    st = Store(":memory:")
    st.upsert_product("SKU-DUAL", "Amazon wala", "Amazon", 300)
    st.upsert_product("SKU-DUAL", "Flipkart wala", "Flipkart", 280)
    rows = st.db.execute("SELECT platform, price FROM products WHERE sku='SKU-DUAL' ORDER BY platform").fetchall()
    assert len(rows) == 2 and rows[0]["price"] == 300 and rows[1]["price"] == 280, "ek SKU dono bazaaro par alag rahega"
    st.upsert_campaign("Fest", "Amazon", 100, 500); st.upsert_campaign("Fest", "Flipkart", 50, 200)
    assert st.db.execute("SELECT COUNT(*) c FROM campaigns WHERE name='Fest'").fetchone()["c"] == 2
    st.close()

def test_velocity_span():
    import analytics as AN
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    # 10 units, pehli-aakhri bikri 10 din ke antar par — sirf 2 selling-days ginne se 5/din galat aata tha
    for i, d in enumerate(["2026-10-01", "2026-10-10"]):
        st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default',?,?,'Shipped',500,'INR')", (f"V{i}", d))
        st.db.execute("INSERT INTO order_items VALUES ('Amazon','default',?,?, 'SKU-V','B0',5,500,0)", (f"V{i}", f"L{i}"))
    st.db.commit()
    v = AN.sku_velocity_per_day(st.db, "SKU-V")
    assert abs(v - 1.0) < 0.01, f"span 10 din par 10 units = 1/din hona chahiye, mila {v}"
    st.close()

def test_period_overlap_rules():
    from connectors.periods import apply_period_rows
    st = Store(":memory:")
    ins = lambda n: (lambda: n)
    r1 = apply_period_rows(st.db, "SRC", "2026-10-01", "2026-10-07",
                           lambda: (st.add_search_term("kaju", "C", 100, 200, 5, 1, source="SRC", period_start="2026-10-01", period_end="2026-10-07"), 1)[1])
    assert r1["status"] == "INSERTED"
    # chhota period bade ke andar — skip (dohra hisaab nahi)
    r2 = apply_period_rows(st.db, "SRC", "2026-10-02", "2026-10-03", ins(1))
    assert r2["status"] == "SKIPPED_CONTAINED"
    # aadha takraav — block
    r3 = apply_period_rows(st.db, "SRC", "2026-10-05", "2026-10-12", ins(1))
    assert r3["status"] == "BLOCKED_PARTIAL_OVERLAP"
    # bada period purane ko supersede karega
    def ins_big():
        st.add_search_term("kaju", "C", 300, 600, 9, 2, source="SRC", period_start="2026-10-01", period_end="2026-10-14"); return 1
    r4 = apply_period_rows(st.db, "SRC", "2026-10-01", "2026-10-14", ins_big)
    assert r4["status"] == "INSERTED" and len(r4["replaced_periods"]) == 1
    tot = st.db.execute("SELECT SUM(spend) s FROM search_terms WHERE source='SRC'").fetchone()["s"]
    assert tot == 300, f"supersede ke baad sirf nayi khidki ginegi, mila {tot}"
    st.close()

def test_outcome_windowed():
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
        st.db.execute("INSERT INTO order_items VALUES ('Amazon','default',?,?,'SKU-W','B0',1,?,0)", (oid, oid + "L", gross))
    order("B1", 10, 1000)   # lagne se pehle ki khidki
    order("B2", 11, 500)
    order("A1", 3, 3000)    # lagne ke baad ki khidki
    order("A2", 4, 500)
    st.db.commit()
    p = create_proposal(st.db, "PRICE_TEST", "Amazon", "acc", {"sku": "SKU-W"}, "ONE_TAP", "t", "ow-1")
    approve(st.db, p["id"], owner); queue_action(st.db, p["id"], owner)
    class OK:
        def execute(self, payload, action): return {"vendor_ref": "manual:ok"}
    execute(st.db, p["id"], owner, OK())
    applied = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
    st.db.execute("UPDATE action_events SET at=? WHERE action_id=? AND to_state='APPLIED_VERIFIED'", (applied, p["id"])); st.db.commit()
    out = OE.measure_due(st.db, windows=(7,))
    assert out["measured"] == 1, f"khidki-maap hona chahiye: {out}"
    row = st.db.execute("SELECT * FROM outcomes WHERE action_id=?", (p["id"],)).fetchone()
    assert row["metric"] == "sku_revenue_window" and row["before_val"] == 1500 and row["after_val"] == 3500 and row["success"] == 1
    st.close()

def test_fees_in_data_sync_and_publish_endpoint():
    import sync_service as SS
    import finance as F
    st = Store(":memory:")
    from platform_core import ensure_v12; ensure_v12(st.db)
    st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default','OF1', date('now'), 'Shipped', 400, 'INR')"); st.db.commit()
    class FakeSP:
        def get_order_financials(self, oid):
            return [{"order_id": oid, "sku": "SKU-F1", "gross": 400, "fees": 90}]
    r = SS.sync_order_fees(st, days=3, sp=FakeSP())
    assert r["fee_rows"] == 1 and F.sku_fee_rate(st.db, "SKU-F1")["gross_basis"] == 400
    app = open(os.path.join(os.path.dirname(__file__), "..", "backend", "app.py")).read()
    assert "/api/v1/listings/publish" in app
    comp = open(os.path.join(os.path.dirname(__file__), "..", "docker-compose.yml")).read()
    assert "127.0.0.1:8765" in comp, "backend port sirf localhost par khulega"
    st.close()

if __name__ == "__main__":
    for t in [test_platform_identity, test_velocity_span, test_period_overlap_rules,
              test_outcome_windowed, test_fees_in_data_sync_and_publish_endpoint]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V14 TESTS PASS")
