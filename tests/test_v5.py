import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from scheduler import DAILY_JOBS, WEEKLY_JOBS, run_jobs
from warroom_service import warroom_data

def test_db_persistence():
    s = Store(":memory:")
    s.add_knowledge("Diwali se 30 din pehle coupon", "Helium10 Blog", 0.8, "A10")
    assert len(s.knowledge_for("A10")) == 1
    aid = s.log_action("A06", "BID_CHANGE", "bid +20% kaju", "ONE_TAP", "EXECUTED")
    s.record_result(aid, 12.5)
    aid2 = s.log_action("A06", "BID_CHANGE", "bid +20% badam", "ONE_TAP", "EXECUTED")
    s.record_result(aid2, -4.0)
    assert s.action_success_rate("A06") == 50.0
    for r in [22, 18, 12, 9]: s.log_rank("BADAM500", "california almonds", r, 0.4, 0.1)
    series = s.rank_series("california almonds")
    assert [x["rank"] for x in series] == [22, 18, 12, 9]
    s.save_rule("A06:BID_UP_20:Cashew", 0.61, 20, 10, True)
    assert s.load_rules()["A06:BID_UP_20:Cashew"]["confidence"] == 0.61
    s.close()

def test_scheduler():
    assert len(DAILY_JOBS) == 9 and len(WEEKLY_JOBS) == 2
    times = [j["time"] for j in DAILY_JOBS]; assert times == sorted(times)   # din ka kram sahi
    out = run_jobs({"learning_crawl": lambda: "12 nayi seekh mili",
                    "data_sync": lambda: 1 / 0})
    by = {r["job"]: r for r in out}
    assert by["learning_crawl"]["status"] == "DONE"
    assert by["data_sync"]["status"].startswith("FAILED") and by["data_sync"]["escalate"] == "A09 Governance"
    assert by["war_room_report"]["status"].startswith("SKIPPED")   # handler nahi = jhootha DONE nahi

def test_warroom_contract():
    # V7 contract: warroom ab SIRF asal data deta hai — khaali DB = connected False, koi nakli number nahi
    s = Store(":memory:")
    d = warroom_data(s)
    assert d["connected"] is False and d["demo_data"] is False and d["kpis"] is None
    s.add_order("O1", "Amazon", "BADAM500", 649)
    s.upsert_campaign("C1", "Amazon", spend=100, sales=400)
    d2 = warroom_data(s)
    assert d2["connected"] is True and d2["kpis"]["total_sales"] == 649
    s.close()

if __name__ == "__main__":
    for t in [test_db_persistence, test_scheduler, test_warroom_contract]:
        t(); print("PASS", t.__name__)
    print("ALL V5 TESTS PASS")
