import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from agents.base import LLMProvider, LLMNotConfigured
from agents.listing_agent import ListingAgent, generate_title, generate_bullets
from agents.ads_agent import AdsAgent
from agents.governance import GovernanceAgent
from listing_scorer import Listing
from claim_checker import check_listing_text

def test_listing_generation():
    t = generate_title("California Almonds", "Premium Jumbo", "500g", ["almonds", "badam"])
    assert "Almonds" in t and "500g" in t and len(t) <= 200
    b = generate_bullets({"origin": "California ke bagh", "grade_detail": "Jumbo size badam",
                          "nutrition_line": "protein aur fiber", "pack_line": "nitrogen-flush pack",
                          "uses": ["snacking", "gifting", "baking"]})
    assert len(b) == 5 and check_listing_text(t + " " + " ".join(b))["can_go_live"]

def test_listing_agent_proposal():
    st = Store(":memory:")
    ag = ListingAgent(st)
    cur = Listing("Almonds 500g", bullets=2, image_count=5, rating=4.3, review_count=120,
                  price_per_kg=1298, top3_avg_price_per_kg=1350, main_keywords_in_title=1)
    r = ag.improve(cur, "California Almonds", "Premium Jumbo", "500g", ["almonds", "badam", "dry fruits"],
                   {"origin": "California", "grade_detail": "Jumbo badam", "nutrition_line": "protein, fiber",
                    "pack_line": "hygienic pack", "uses": ["snacking"]})
    assert not r["blocked"] and r["score_after_expected"]["score"] > r["score_before"]["score"]
    assert r["proposal"]["status"] == "WAITING_USER_APPROVAL" and r["proposal"]["tier"] == "ONE_TAP"
    st.close()

def test_ads_agent_real_data_only():
    st = Store(":memory:")
    empty = AdsAgent(st).analyze()
    assert empty["proposals"] == [] and "data nahi" in empty["note"]   # data nahi to proposal nahi — imaandari
    st.add_search_term("cheap combo offer", "Broad", 900, 0, 60, 0, "test")
    st.add_search_term("mamra almonds", "Exact", 500, 5200, 40, 8, "test")
    res = AdsAgent(st).analyze()
    acts = [p["action_type"] for p in res["proposals"]]
    assert "ADD_NEGATIVE" in acts and res["summary"]["action_counts"].get("SCALE_BID_UP_20", 0) >= 1
    neg = [p for p in res["proposals"] if p["action_type"] == "ADD_NEGATIVE"][0]
    assert neg["status"] == "EXECUTED_AUTO"        # Tier-0 khud lagu
    st.close()

def test_governance_cycle():
    st = Store(":memory:")
    rep = GovernanceAgent(st).daily_cycle()
    assert len(rep["jobs"]) == 10 and rep["warroom_connected"] is False
    st.add_search_term("waste term", "Broad", 900, 0, 50, 0, "test")
    rep2 = GovernanceAgent(st).daily_cycle()
    assert rep2["proposals_created"] >= 1
    waiting = st.db.execute("SELECT COUNT(*) c FROM actions").fetchone()["c"]
    assert waiting >= 1
    st.close()

def test_llm_honesty():
    p = LLMProvider()
    if not p.available:
        try: p.generate("namaste"); assert False
        except LLMNotConfigured as e: assert "RuleProvider" in str(e)

if __name__ == "__main__":
    for t in [test_listing_generation, test_listing_agent_proposal, test_ads_agent_real_data_only,
              test_governance_cycle, test_llm_honesty]:
        t(); print("PASS", t.__name__)
    print("ALL V8 TESTS PASS")
