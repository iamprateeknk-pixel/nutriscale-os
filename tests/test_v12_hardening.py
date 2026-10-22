"""V12.1 AUDIT-FIX TESTS — bahari audit ki har sachi kami ka saboot-fix."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

def test_sync_v2_flipkart_and_sp():
    import sync_service as SS
    st = Store(":memory:")
    class FakeFK:
        def get_orders(self, f, t): return [{"orderId": "OD1", "orderItemId": "IT1", "sku": "FK-KAJU", "fsn": "FSN1",
                                             "price": 499, "quantity": 2, "orderDate": "2026-10-05"}]
        def get_listings(self): return [{"skuId": "FK-KAJU", "title": "Kaju 200g", "sellingPrice": 499}]
    r = SS.sync_flipkart(st, "2026-10-01", "2026-10-07", fk=FakeFK())
    assert r["orders_items"] == 1 and r["listings"] == 1
    from platform_core import ensure_v12; ensure_v12(st.db)
    assert st.db.execute("SELECT COUNT(*) c FROM order_items WHERE platform='Flipkart'").fetchone()["c"] == 1
    class FakeSP:
        def get_orders(self, since): return [{"AmazonOrderId": "A1", "PurchaseDate": "2026-10-06T00:00:00Z",
                                              "OrderStatus": "Shipped", "OrderTotal": {"Amount": "798"}}]
        def get_order_items(self, oid): return [{"OrderItemId": "OI1", "SellerSKU": "SKU-BR", "ASIN": "B0X",
                                                 "QuantityOrdered": 1, "ItemPrice": {"Amount": "798"}}]
    r2 = SS.sync_amazon_orders(st, "2026-10-01T00:00:00Z", sp=FakeSP())
    assert r2["orders"] == 1 and r2["items"] == 1, "SP sync ab items ke saath canonical hoga"
    st.close()

def test_job_handlers_dedicated():
    from job_handlers import build_handlers
    from jobrunner import DAILY_JOBS, run_due_jobs
    st = Store(":memory:")
    h = build_handlers(st)
    assert set(h) == {j["job"] for j in DAILY_JOBS}, "har job ka apna handler hona chahiye"
    from jobrunner import seed_jobs
    seed_jobs(st.db)
    st.db.execute("UPDATE job_state SET next_run='2020-01-01T00:00:00+00:00'"); st.db.commit()
    out = run_due_jobs(st.db, h)
    by = {o["job"]: o["status"] for o in out}
    assert by["data_sync"] == "SKIPPED", "connector bina data_sync imaandaar SKIP hoga, nakli DONE nahi"
    assert by["learning_crawl"] == "DONE"
    st.close()

def test_vendor_adapter_gate_verify_rollback():
    import capabilities as caps
    from vendor_adapters import AmazonAdsWriteAdapter
    from actions import create_proposal, approve, queue_action, execute, rollback
    import auth as A
    st = Store(":memory:")
    state = {"camp": {"campaignId": "C1", "name": "Brazil", "state": "ENABLED"}}
    class FakeAds:
        def list_campaigns(self): return [dict(state["camp"])]
        def update_campaigns(self, camps): state["camp"]["state"] = camps[0]["state"]; return {"ok": True}
        def list_keywords(self): return []
        def update_keywords(self, k): return {}
    A.create_user(st.db, "owner2", "pass1234", "Owner")
    owner = {"username": "owner2", "role": "Owner"}
    ad = AmazonAdsWriteAdapter(st, ads=FakeAds())
    p = create_proposal(st.db, "PAUSE_CAMPAIGN", "Amazon", "acc",
                        {"kind": "PAUSE_CAMPAIGN", "campaign_id": "C1", "adapter": "amazon_ads"},
                        "ONE_TAP", "test", "hk-1")
    approve(st.db, p["id"], owner); queue_action(st.db, p["id"], owner)
    r = execute(st.db, p["id"], owner, ad)
    assert r["state"] == "FAILED" and state["camp"]["state"] == "ENABLED", "certified bina vendor write NAHI hoga"
    caps.set_capability(st.db, "Amazon", "write_ads", "certified", "pilot sign-off test by owner2")
    p2 = create_proposal(st.db, "PAUSE_CAMPAIGN", "Amazon", "acc",
                          {"kind": "PAUSE_CAMPAIGN", "campaign_id": "C1", "adapter": "amazon_ads"},
                          "ONE_TAP", "test", "hk-2")
    approve(st.db, p2["id"], owner); queue_action(st.db, p2["id"], owner)
    r2 = execute(st.db, p2["id"], owner, ad)
    assert r2["state"] == "APPLIED_VERIFIED" and state["camp"]["state"] == "PAUSED", "asal write + refetch pushti"
    rb = rollback(st.db, p2["id"], owner, ad)
    assert rb["ok"] and state["camp"]["state"] == "ENABLED", "rollback purani halat wapas layega"
    st.close()

def test_totp_mfa():
    import auth as A
    st = Store(":memory:")
    A.create_user(st.db, "mfauser", "pass1234", "Owner")
    en = A.enable_totp(st.db, "mfauser")
    assert en["secret"]
    r = A.verify_login(st.db, "mfauser", "pass1234")
    assert r and r.get("mfa_required"), "code bina login nahi milega"
    code = next(iter(A._totp_codes(en["secret"])))
    r2 = A.verify_login(st.db, "mfauser", "pass1234", code)
    assert r2 and r2.get("token"), "sahi code par token milega"
    st.close()

def test_realized_fees_pipeline():
    import finance as F
    from ops_finance import import_settlements
    st = Store(":memory:")
    st.db.execute("INSERT OR REPLACE INTO products VALUES ('SKU-F','Fee Wala','Amazon',300,0,0,0,'t')"); st.db.commit()
    F.set_cost(st.db, "SKU-F", 100, 20, approved_by="owner")
    before = F.contribution_v2(st.db, "SKU-F", 300)
    assert "ESTIMATE" in before["fee_source"]
    import tempfile, csv as _csv
    fd, path = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    with open(path, "w", newline="") as f:
        w = _csv.writer(f); w.writerow(["settlement id", "period start", "period end", "gross", "fees", "tax", "net"])
        w.writerow(["S1", "2026-09-01", "2026-09-15", 50000, 15000, 5000, 30000])
    import_settlements(st, path)
    after = F.contribution_v2(st.db, "SKU-F", 300)
    assert "REALIZED" in after["fee_source"] and abs(after["platform_fees"] - 120.0) < 0.01, "40% asal dar se 300 par 120 fee"
    st.close()

def test_dashboard_hardening():
    html = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")).read()
    assert "location.origin" in html and "esc=" in html or "const esc" in html
    assert "sparkSVG" in html, "rank chart hona chahiye"
    app = open(os.path.join(os.path.dirname(__file__), "..", "backend", "app.py")).read()
    assert "_serve_dashboard" in app and "MFA_REQUIRED" in app
    print("  Dashboard: same-origin + escaping + charts + MFA ✔")

if __name__ == "__main__":
    for t in [test_sync_v2_flipkart_and_sp, test_job_handlers_dedicated, test_vendor_adapter_gate_verify_rollback,
              test_totp_mfa, test_realized_fees_pipeline, test_dashboard_hardening]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V12.1 HARDENING TESTS PASS")
