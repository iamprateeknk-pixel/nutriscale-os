import sys, os, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from agents.market_agent import MarketAgent, season_for_date
from agents.competitor_agent import CompetitorAgent
from agents.keyword_agent import KeywordAgent, intent_of
from agents.creative_agent import CreativeAgent, main_image_brief
from agents.pricing_agent import PricingAgent
from agents.review_agent import ReviewAgent, analyze_reviews

def test_market_seasons():
    diwali = season_for_date(datetime.date(2026, 10, 15))
    assert diwali["in_window"] and "Diwali" in diwali["season"]
    normal = season_for_date(datetime.date(2026, 3, 10))   # March — Ramadan window ya normal, dono chalega lekin structure sahi ho
    assert "season" in normal and "prep" in normal
    st = Store(":memory:"); assert "season" in MarketAgent(st).today_brief(datetime.date(2026, 10, 15)); st.close()

def test_competitor_moves():
    st = Store(":memory:"); ag = CompetitorAgent(st)
    moves = ag.detect_price_moves({"FarmVedha Kaju": 1600, "Nutraj Anjeer": 1400},
                                  {"FarmVedha Kaju": 1470, "Nutraj Anjeer": 1520})
    types = {m["sku"]: m["type"] for m in moves}
    assert types["FarmVedha Kaju"] == "PRICE_ATTACK" and types["Nutraj Anjeer"] == "PRICE_UP"
    g = ag.gap_report({"price_per_kg": 1598, "rating": 4.1, "reviews": 86},
                      {"price_per_kg": 1470, "rating": 4.2, "reviews": 1240})
    assert g["gaps"]; st.close()

def test_keyword_bank():
    assert intent_of("buy almonds 500g online") == "BUY_INTENT"
    assert intent_of("dry fruit wholesale mandi rate") == "B2B_SKIP"
    st = Store(":memory:")
    assert KeywordAgent(st).build_bank()["bank"] == []
    st.add_search_term("mamra almonds 500g", "Exact", 500, 5200, 50, 9, "t")
    st.add_search_term("random gift ideas", "Broad", 300, 100, 40, 0, "t")
    bank = KeywordAgent(st).build_bank()
    assert bank["heroes"] and bank["heroes"][0]["term"].startswith("mamra")
    st.close()

def test_creative_brief():
    b = main_image_brief("Cashew Kaju", "W240", "500g")
    assert len(b["shots"]) == 7 and b["claims_ok"] and "30-sec" in b["video_script"]
    st = Store(":memory:"); CreativeAgent(st).brief_for("Cashew Kaju", "W240", "500g"); st.close()

def test_pricing_agent():
    st = Store(":memory:")
    assert PricingAgent(st).evaluate_products()["evaluations"] == []
    st.upsert_product("BADAM500", "Almonds 500g", "Amazon", 649, cost=340)
    st.upsert_product("GHATA500", "Cheap Mix 500g", "Amazon", 299, cost=230)   # patla/ghata margin
    ev = PricingAgent(st).evaluate_products()["evaluations"]
    by = {e["sku"]: e for e in ev}
    assert by["GHATA500"]["verdict"] in ("THIN", "LOSS_RISK")
    st.close()

def test_review_mining():
    reviews = [{"rating": 2, "text": "badam bahut chhota size hai, packing bhi kharab"},
               {"rating": 1, "text": "size chhota, stale taste"},
               {"rating": 5, "text": "bahut achha fresh badam, best quality"},
               {"rating": 3, "text": "price zyada hai, mehenga pada"}]
    r = analyze_reviews(reviews)
    assert r["top_complaint"] == "SIZE" and r["complaint_counts"]["SIZE"] == 2 and r["negative"] == 3
    st = Store(":memory:"); ReviewAgent(st).analyze(reviews); st.close()

if __name__ == "__main__":
    for t in [test_market_seasons, test_competitor_moves, test_keyword_bank, test_creative_brief, test_pricing_agent, test_review_mining]:
        t(); print("PASS", t.__name__)
    print("ALL V9 TESTS PASS")
