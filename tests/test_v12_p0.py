import sys, os, datetime, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db_store import Store
import auth as A, actions as ACT, finance as F, fact_registry as FR
from metrics import tacos, compare_windows
from platform_core import ensure_v12

def test_auth_rbac():
    st = Store(":memory:")
    assert A.create_user(st.db, "owner1", "password123", "Owner")["ok"]
    assert A.create_user(st.db, "agency1", "password123", "AgencyViewer")["ok"]
    assert not A.verify_login(st.db, "owner1", "galat-pass")
    lg = A.verify_login(st.db, "owner1", "password123"); assert lg and lg["role"] == "Owner"
    assert A.user_from_token(st.db, lg["token"])["username"] == "owner1"
    assert A.user_from_token(st.db, "nakli-token") is None
    assert A.can("AgencyViewer", "read") and not A.can("AgencyViewer", "execute")
    assert not A.can("GrowthLead", "approve_tier2") and A.can("Owner", "kill")
    user, err = A.require(st.db, {}, "read"); assert err and err[0] == 401
    user, err = A.require(st.db, {"Authorization": "Bearer " + lg["token"]}, "read"); assert user
    st.close()

def test_kill_and_state_machine():
    st = Store(":memory:")
    owner = {"username": "o1", "role": "Owner"}; owner2 = {"username": "o2", "role": "Owner"}
    p = ACT.create_proposal(st.db, "BID_CHANGE", "Amazon", "acc", {"term": "x", "bid": "-20%"}, "DOUBLE", "o1", "key-1")
    dup = ACT.create_proposal(st.db, "BID_CHANGE", "Amazon", "acc", {"term": "x"}, "DOUBLE", "o1", "key-1")
    assert dup["duplicate"] and dup["id"] == p["id"], "idempotency fail"
    r1 = ACT.approve(st.db, p["id"], owner)
    assert r1["state"] == "APPROVAL_PENDING" and r1["needed"] == 2, "double confirm ka pehla kadam"
    r1b = ACT.approve(st.db, p["id"], owner)   # wahi aadmi dobara — ginti nahi badhegi
    assert r1b["approvals"] == 1
    r2 = ACT.approve(st.db, p["id"], owner2)
    assert r2["state"] == "APPROVED"
    assert ACT.queue_action(st.db, p["id"], owner)["state"] == "QUEUED"
    # bina manual saboot ke execute -> FAILED, APPLIED kabhi nahi
    ex = ACT.execute(st.db, p["id"], owner, ACT.ManualAdapter())
    assert ex["state"] == "FAILED"
    # kill on: queue hi nahi hoga
    ACT.set_kill(st.db, True, "o1", "test")
    p2 = ACT.create_proposal(st.db, "PAUSE", "Amazon", "acc", {}, "ONE_TAP", "o1", "key-2")
    ACT.approve(st.db, p2["id"], owner)
    assert "KILL" in ACT.queue_action(st.db, p2["id"], owner)["error"]
    assert ACT.kill_status(st.db)["engaged"]  # persist (DB me hai, restart-safe)
    ACT.set_kill(st.db, False, "o1")
    # manual saboot ke saath verified
    ACT.queue_action(st.db, p2["id"], owner)
    ex2 = ACT.execute(st.db, p2["id"], owner, ACT.ManualAdapter({"key-2": "AMZ-CONSOLE-REF-123"}))
    assert ex2["state"] == "APPLIED_VERIFIED"
    tl = ACT.action_timeline(st.db, p2["id"]); assert len(tl) >= 3
    st.close()

def test_canonical_import_idempotent(tmp="/tmp/uc_orders.txt"):
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["order-id", "order-item-id", "purchase-date", "sku", "item-price", "quantity-purchased"])
        w.writerow(["111-1", "L1", "2026-10-01", "BADAM200", "499", "1"])
        w.writerow(["111-1", "L2", "2026-10-01", "KAJU200", "279", "2"])
    from connectors.csv_import import import_orders_canonical
    st = Store(":memory:")
    r1 = import_orders_canonical(tmp, st, period=("2026-10-01", "2026-10-01"))
    r2 = import_orders_canonical(tmp, st, period=("2026-10-01", "2026-10-01"))
    assert r1["rows_ok"] == 2 and r2["duplicate"]
    n = st.db.execute("SELECT COUNT(*) c FROM order_items").fetchone()["c"]
    assert n == 2, "do line items rehne chahiye, duplicate nahi"
    st.close()

def test_metrics_gating():
    ok = tacos(1000, 10000, ("2026-09-01", "2026-09-30"), ("2026-09-01", "2026-09-30"))
    assert ok["status"] == "OK" and ok["value"] == 10.0
    bad = tacos(1000, 10000, ("2026-08-22", "2026-10-21"), ("2026-07-23", "2026-09-30"))
    assert bad["value"] is None and bad["status"] == "NOT_COMPARABLE" or bad["overlap_ratio"] < 0.9

def test_finance_cost_gate():
    st = Store(":memory:")
    r = F.contribution_v2(st.db, "NAYA-SKU", 500)
    assert not r["known"] and not r["scale_allowed"], "cost unknown par scale band hona chahiye (QA-07)"
    F.set_cost(st.db, "BADAM500", 340, 20, approved_by="owner")
    r2 = F.contribution_v2(st.db, "BADAM500", 649)
    assert r2["known"] and r2["unit_cost"] == 360
    st.close()

def test_fact_registry():
    st = Store(":memory:")
    r = FR.check_copy(st.db, "KAJU200", "Cashew W320 nitrogen flush pack, diabetic friendly")
    assert r["status"] == "NEEDS_EVIDENCE" and not r["can_publish"]
    FR.add_fact(st.db, "KAJU200", "PROCESSING_NITROGEN", "Nitrogen flushed", "supplier-cert-1.pdf", "owner")
    FR.add_fact(st.db, "KAJU200", "GRADE_PROOF", "W320", "grade-report.pdf", "owner")
    r2 = FR.check_copy(st.db, "KAJU200", "Cashew nitrogen flush pack")
    assert r2["can_publish"]
    st.close()

def test_jobrunner_durable():
    from jobrunner import run_due_jobs, jobs_status, seed_jobs
    st = Store(":memory:")
    seed_jobs(st.db)
    st.db.execute("UPDATE job_state SET next_run='2020-01-01T00:00:00+05:30'"); st.db.commit()
    calls = {"n": 0}
    def ok_fn(): calls["n"] += 1; return "hua"
    def bad_fn(): raise RuntimeError("boom")
    from scheduler import DAILY_JOBS
    handlers = {j["job"]: ok_fn for j in DAILY_JOBS}
    handlers["data_sync"] = bad_fn
    out = run_due_jobs(st.db, handlers, now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))))
    by = {r["job"]: r["status"] for r in out}
    assert by["data_sync"] == "FAILED" and by["learning_crawl"] == "DONE" and calls["n"] >= 1
    assert jobs_status(st.db), "state DB me persist hona chahiye"
    st.close()

if __name__ == "__main__":
    for t in [test_auth_rbac, test_kill_and_state_machine, test_canonical_import_idempotent,
              test_metrics_gating, test_finance_cost_gate, test_fact_registry, test_jobrunner_durable]:
        t(); print("PASS", t.__name__)
    print("ALL V12-P0 TESTS PASS")
