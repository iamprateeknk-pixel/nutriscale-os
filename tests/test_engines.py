import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from profit_calculator import SKU, contribution, max_cpc
from listing_scorer import Listing, score_listing
from ads_engine import TermStats, decide, blended_roas
from keyword_competitor import keyword_opportunity, competitor_gap

def test_profit():
    r = contribution(SKU("Badam 500g", 649, 340, 25, 500))
    assert r["profit_before_ads"] > 0 and 0 < r["target_roas"] < 20
    assert max_cpc(649, 0.12, r["target_acos_pct"]) > 0

def test_listing_block_and_pass():
    weak = score_listing(Listing("Almonds 500g", bullets=2, image_count=3, rating=3.8, review_count=12))
    assert weak["verdict"] == "FIX_FIRST_ADS_BLOCKED" and weak["issues"]
    strong = score_listing(Listing("California Almonds Badam 500g | Premium Grade | Protein Rich Healthy Snack for Daily Use and Gifting | Fresh", bullets=5, image_count=7, has_video=True, has_a_plus=True, rating=4.5, review_count=850, price_per_kg=1298, top3_avg_price_per_kg=1350, backend_terms_filled=True, main_keywords_in_title=5))
    assert strong["score"] >= 70 and strong["verdict"] == "SCALE_OK", strong

def test_ads_rules():
    kill = decide(TermStats("cheap dry fruits", spend=900, sales=0, clicks=60, impressions=5000, orders=0), target_roas=4, target_cpa=300)
    assert kill["action"] == "KILL_ADD_NEGATIVE"
    win = decide(TermStats("mamra almonds 500g", spend=500, sales=4500, clicks=40, impressions=3000, orders=7), target_roas=4, target_cpa=300)
    assert win["action"] == "SCALE_BID_UP_20"
    assert blended_roas([TermStats("a", 100, 400), TermStats("b", 100, 200)]) == 3.0

def test_keyword_competitor():
    k = keyword_opportunity(20000, 0.9, 0.6, current_rank=18)
    assert k["tier"] in ("HERO", "GROWTH")
    g = competitor_gap(1400, 1250, 4.1, 4.5, 90, 900)
    assert len(g["gaps"]) == 3

if __name__ == "__main__":
    for t in [test_profit, test_listing_block_and_pass, test_ads_rules, test_keyword_competitor]:
        t(); print("PASS", t.__name__)
    print("ALL TESTS PASS")
