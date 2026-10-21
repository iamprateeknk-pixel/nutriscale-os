import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from self_learning import KnowledgeStore, OutcomeLearner, strength_score
from experiment_engine import evaluate_ab, daily_learning_cycle
from learning_sources import sources_for_agent, daily_crawl_plan

def test_knowledge_trust():
    ks = KnowledgeStore()
    k = ks.learn("Festival se 30 din pehle coupon lagao", "Helium 10 Blog", 0.8, "A10")
    assert k.trust == 0.4                      # naya gyaan = aadha bharosa
    for _ in range(4): ks.record_application(k, True)
    assert k.trust > 0.8                      # parakhne par bharosa badha
    assert ks.best_for_agent("A10")[0] is k

def test_outcome_learning_context():
    ol = OutcomeLearner()
    # BID_UP_20 Almonds par 3 baar fail -> disable; Cashew par kaam kiya -> confidence up
    for _ in range(3): r = ol.record("A06", "BID_UP_20", "Almonds", False)
    assert not r.enabled and not ol.should_use("A06", "BID_UP_20", "Almonds")
    for _ in range(3): r2 = ol.record("A06", "BID_UP_20", "Cashew", True)
    assert r2.enabled and r2.confidence > 0.5 and ol.should_use("A06", "BID_UP_20", "Cashew")

def test_ab_promote_and_wait():
    w = evaluate_ab({"views": 1000, "conversions": 80}, {"views": 1000, "conversions": 130})
    assert w["decision"] == "PROMOTE_TREATMENT" and w["lift_pct"] > 50
    small = evaluate_ab({"views": 100, "conversions": 10}, {"views": 100, "conversions": 20})
    assert small["decision"] == "WAIT"
    bad = evaluate_ab({"views": 1000, "conversions": 130}, {"views": 1000, "conversions": 80})
    assert bad["decision"] == "KEEP_CONTROL"

def test_sources_and_strength():
    plan = daily_crawl_plan()
    assert plan[0]["type"] == "official"                       # official sources pehle
    assert any(s["name"].startswith("Unicommerce") for s in sources_for_agent("A13"))
    s = strength_score(wins=80, losses=20, knowledge_count=60, days_active=90)
    assert s["strength_score"] >= 75 and s["grade"] == "STRONG"
    assert len(daily_learning_cycle()) == 5

if __name__ == "__main__":
    for t in [test_knowledge_trust, test_outcome_learning_context, test_ab_promote_and_wait, test_sources_and_strength]:
        t(); print("PASS", t.__name__)
    print("ALL V3 TESTS PASS")
