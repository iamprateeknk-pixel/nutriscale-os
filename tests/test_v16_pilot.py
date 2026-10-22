"""V16 TESTS — Acceptance Gates Kit: preflight imaandaari, drill ke taale, poora drill saboot ke saath."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

def test_preflight_honest():
    import pilot as P
    st = Store(":memory:")
    pf = P.preflight(st.db)
    names = {c["check"]: c["ok"] for c in pf["checks"]}
    assert names["owner_user"] is False and pf["ready_for_pilot"] is False, "khaali DB par taiyaari HAAN nahi honi chahiye"
    assert names["https_pack"] is True
    import auth as A
    A.create_user(st.db, "boss", "pass1234", "Owner")
    pf2 = P.preflight(st.db)
    assert {c["check"]: c["ok"] for c in pf2["checks"]}["owner_user"] is True
    st.close()

def test_drill_gates():
    import pilot as P
    import auth as A
    st = Store(":memory:")
    A.create_user(st.db, "boss", "pass1234", "Owner"); owner = {"username": "boss", "role": "Owner"}
    plan = P.controlled_drill(st.db, {"kind": "PAUSE_CAMPAIGN", "campaign_id": "C1"}, owner, live=False)
    assert plan["verdict"] == "PLAN_ONLY"
    blocked = P.controlled_drill(st.db, {"kind": "PAUSE_CAMPAIGN", "campaign_id": "C1"}, owner, live=True, store=st)
    assert blocked["verdict"] == "BLOCKED" and "certified" in str(blocked["steps"])
    import actions as act
    act.set_kill(st.db, True, "boss", "test")
    k = P.controlled_drill(st.db, {"kind": "PAUSE_CAMPAIGN", "campaign_id": "C1"}, owner, live=True, store=st)
    assert k["verdict"] == "BLOCKED"
    act.set_kill(st.db, False, "boss", "")
    st.close()

def test_drill_full_pass():
    import pilot as P
    import auth as A, capabilities as caps
    from vendor_adapters import AmazonAdsWriteAdapter
    st = Store(":memory:")
    A.create_user(st.db, "boss", "pass1234", "Owner"); owner = {"username": "boss", "role": "Owner"}
    state = {"camp": {"campaignId": "C9", "name": "Drill", "state": "ENABLED"}}
    class FakeAds:
        def list_campaigns(self): return [dict(state["camp"])]
        def update_campaigns(self, camps): state["camp"]["state"] = camps[0]["state"]; return {"ok": True}
    caps.set_capability(st.db, "Amazon", "write_ads", "certified", "test sign-off")
    ad = AmazonAdsWriteAdapter(st, ads=FakeAds())
    r = P.controlled_drill(st.db, {"kind": "PAUSE_CAMPAIGN", "campaign_id": "C9", "platform": "Amazon"},
                           owner, live=True, adapter=ad, store=st)
    assert r["verdict"] == "DRILL_PASS", r
    assert state["camp"]["state"] == "ENABLED", "drill ke baad campaign purani halat par hona chahiye"
    assert all(s["ok"] for s in r["steps"])
    st.close()

def test_reconciliation_report():
    import pilot as P
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default','R1', date('now'), 'Shipped', 1000, 'INR')")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','R1','L1','SKU','B0',1,1000,0)")
    st.db.commit()
    rep = P.reconciliation_report(st)
    assert rep["orders_vs_settlements"]["order_gmv"] == 1000
    assert rep["orders_vs_settlements"]["status"] == "EXCEPTION", "settlement na ho to EXCEPTION saaf dikhna chahiye"
    st.close()

if __name__ == "__main__":
    for t in [test_preflight_honest, test_drill_gates, test_drill_full_pass, test_reconciliation_report]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V16 TESTS PASS")
