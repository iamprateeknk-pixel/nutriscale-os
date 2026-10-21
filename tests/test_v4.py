import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from architecture_v4 import AGENTS, FLOWS, classify, summary
from algorithm_intel import rank_readiness, buybox_score_amazon, assess_algorithm_change, rank_probe_insight
from flow_pipelines import Flow, retention_trigger, seller_health_check

def test_rationalization():
    s = summary(); assert s["agents"] == 9 and s["flows"] == 10
    assert "A13" not in AGENTS and "F2" in FLOWS          # Unicommerce ab flow hai, agent nahi
    assert classify("copy_writing") == "AGENT" and classify("stock_sync") == "FLOW"

def test_rank_models():
    a = rank_readiness({"relevance_indexing": 90, "sales_velocity": 40, "conversion_rate": 30,
                        "ctr": 35, "price_competitiveness": 60, "prime_fba": 100,
                        "stock_availability": 100, "rating_reviews": 50}, "amazon")
    assert 0 < a["rank_readiness_score"] < 100 and a["weakest_factor"] == "conversion_rate"
    f = rank_readiness({"relevance_indexing": 80, "price_competitiveness": 70, "rating_reviews": 60,
                        "flipkart_assured": 0, "sales_velocity": 50, "seller_rating": 70,
                        "dispatch_speed": 80, "low_returns": 90}, "flipkart")
    assert f["weakest_factor"] == "flipkart_assured"      # Assured nahi to Flipkart rank nahi

def test_buybox_and_algo_change():
    b = buybox_score_amazon(price_rank=1, total_sellers=5, is_fba=True, seller_rating=4.6, in_stock=True)
    assert b["buybox_chance_pct"] > 90
    assert buybox_score_amazon(1, 5, True, 4.6, in_stock=False)["buybox_chance_pct"] == 0
    ch = assess_algorithm_change("Amazon referral fee for grocery category revised from next month")
    assert ch["impact"] == "HIGH" and any("F4" in str(h) for h in ch["hits"])
    ch2 = assess_algorithm_change("Rufus AI shopping assistant rollout for search ranking")
    assert ch2["impact"] == "HIGH"

def test_rank_probe_and_flows():
    ins = rank_probe_insight([0.3, 0.4, 0.5, 0.6, 0.7], [22, 18, 14, 10, 6])
    assert ins["correlation_ctr_rank"] < -0.9 and "CTR" in ins["insight"]
    fl = Flow("F6-test").step(lambda c: {**c, "a": 1}).step(lambda c: {**c, "b": c["a"] + 1})
    assert fl.run({})["ctx"]["b"] == 2
    bad = Flow("bad").step(lambda c: 1 / 0)
    assert bad.run({})["status"].startswith("FAILED")
    assert retention_trigger("500g", 22)["send"] is True and retention_trigger("500g", 10)["send"] is False
    h = seller_health_check({"odr_pct": 1.2, "cancellation_pct": 1.0, "late_dispatch_pct": 2.0})
    assert not h["healthy"]

if __name__ == "__main__":
    for t in [test_rationalization, test_rank_models, test_buybox_and_algo_change, test_rank_probe_and_flows]:
        t(); print("PASS", t.__name__)
    print("ALL V4 TESTS PASS")
