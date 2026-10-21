import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from action_planner import build_plan, render_markdown

def test_plan_logic():
    st = Store(":memory:")
    st.upsert_campaign("Dead Campaign", "Amazon", 500, 0, 100, 5000)
    st.upsert_campaign("Winner Campaign", "Amazon", 1000, 3000, 200, 9000)
    st.upsert_campaign("Weak Campaign", "Amazon", 800, 400, 150, 7000)
    st.add_search_term("bekar term xyz", "Dead Campaign", 150, 0, 20, 0, "t")
    st.add_search_term("achha term", "Winner Campaign", 100, 500, 15, 3, "t")
    p = build_plan(st)
    assert [x["campaign"] for x in p["pause"]] == ["Dead Campaign"] and p["savings_est"] == 500
    assert p["scale"] and p["scale"][0]["campaign"] == "Winner Campaign"
    assert p["watch"] and p["watch"][0]["campaign"] == "Weak Campaign"
    neg_terms = [t["term"] for g in p["negatives"] for t in g["terms"]]
    assert "bekar term xyz" in neg_terms and "achha term" not in neg_terms
    md = render_markdown(p, "test")
    assert "PAUSE" in md and "₹500" in md
    st.close()

def test_empty_plan_honest():
    st = Store(":memory:")
    p = build_plan(st)
    assert p["pause"] == [] and p["total_spend"] == 0
    st.close()

if __name__ == "__main__":
    test_plan_logic(); print("PASS test_plan_logic")
    test_empty_plan_honest(); print("PASS test_empty_plan_honest")
    print("ALL V10 TESTS PASS")
