import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from agents.base import LLMProvider, LLMNotConfigured
from agents.listing_agent import ListingAgent
from listing_scorer import Listing
from season_planner import build_season_pack, render_markdown

def test_llm_mock_transport():
    os.environ.pop("GOS_LLM_API_KEY", None); os.environ.pop("GOS_LLM_MODEL", None)
    try: LLMProvider().generate("namaste"); assert False, "key bina error aana chahiye"
    except LLMNotConfigured: pass
    os.environ["GOS_LLM_API_KEY"] = "test-key"; os.environ["GOS_LLM_MODEL"] = "test-model"
    def fake(url, payload, headers):
        assert url.endswith("/chat/completions") and headers["Authorization"] == "Bearer test-key"
        return {"choices": [{"message": {"content": "jawab taiyaar"}}]}
    assert LLMProvider(transport=fake).generate("sawal") == "jawab taiyaar"
    os.environ.pop("GOS_LLM_API_KEY"); os.environ.pop("GOS_LLM_MODEL")

def test_listing_llm_path_and_fallback():
    st = Store(":memory:")
    cur = Listing(title="Purana title", bullets=2, image_count=4, has_video=False, has_a_plus=False,
                  rating=3.9, review_count=5, price_per_kg=1000, top3_avg_price_per_kg=1000,
                  backend_terms_filled=False, main_keywords_in_title=0)
    ag = ListingAgent(st)
    r = ag.improve_with_llm(cur, "Dried Cranberries", "Premium", "200g", ["cranberry"],
                            {"grade_detail": "x", "origin": "y", "nutrition_line": "z", "pack_line": "p"})
    assert r["source"].startswith("RULES") and not r["blocked"]  # key nahi -> rules fallback
    # LLM mock: achhi copy
    os.environ["GOS_LLM_API_KEY"] = "k"; os.environ["GOS_LLM_MODEL"] = "m"
    good = json.dumps({"title": "Dried Cranberries Premium 200g | Unsweetened | Snacking Baking ke liye",
                       "bullets": ["b1 poshak", "b2 taaza", "b3 upyog", "b4 packing", "b5 bharosa"]})
    ag.llm = LLMProvider(transport=lambda u, p, h: {"choices": [{"message": {"content": good}}]})
    r2 = ag.improve_with_llm(cur, "Dried Cranberries", "Premium", "200g", ["cranberry"],
                             {"grade_detail": "x", "origin": "y", "nutrition_line": "z", "pack_line": "p"})
    assert r2["source"] == "LLM" and r2["title"].startswith("Dried Cranberries")
    # LLM mock: dawaa wala dawa -> claim-check rokega -> rules fallback
    bad = json.dumps({"title": "Cranberry diabetes cure karega 200g", "bullets": ["ilaaj pakka"] * 5})
    ag.llm = LLMProvider(transport=lambda u, p, h: {"choices": [{"message": {"content": bad}}]})
    r3 = ag.improve_with_llm(cur, "Dried Cranberries", "Premium", "200g", ["cranberry"],
                             {"grade_detail": "x", "origin": "y", "nutrition_line": "z", "pack_line": "p"})
    assert r3["source"].startswith("RULES"), "bure dawe wali LLM copy live nahi jani chahiye"
    os.environ.pop("GOS_LLM_API_KEY"); os.environ.pop("GOS_LLM_MODEL")
    st.close()

def test_season_pack():
    st = Store(":memory:")
    assert build_season_pack(st)["combos"] == []
    for sku, name, price in [("S1", "Dry Fruit Farm Premium Dried Cranberries 200g", 219),
                             ("S2", "Dry Fruit Farm Premium Brazil Nuts Grade A++ 200g", 799),
                             ("S3", "Dry Fruit Farm Premium Raw Pecan Nuts 200g", 599)]:
        st.upsert_product(sku, name, "Amazon", price)
    pack = build_season_pack(st, current_aov=443)
    assert len(pack["combos"]) == 1 and pack["combos"][0]["name"] == "Diwali Delight Box"
    c = pack["combos"][0]
    assert c["parts_total"] == 1617 and c["gift_price"] == round(1617 * 0.93) and c["aov_multiple"] > 3
    assert "Diwali Delight" in render_markdown(pack)
    st.close()

if __name__ == "__main__":
    test_llm_mock_transport(); print("PASS test_llm_mock_transport")
    test_listing_llm_path_and_fallback(); print("PASS test_listing_llm_path_and_fallback")
    test_season_pack(); print("PASS test_season_pack")
    print("ALL V11 TESTS PASS")
