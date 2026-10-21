import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from claim_checker import check_listing_text, check_label
from flipkart_calculator import flipkart_fees, flipkart_profit
from control_center import Controls

def test_claim_checker():
    bad = check_listing_text("Ye badam diabetes cure karega, 100% organic")
    assert not bad["can_go_live"] and len(bad["blocked_reasons"]) >= 2
    risky = check_listing_text("Diabetic logo ke liye behtar, immunity badhaye")
    assert risky["can_go_live"] and len(risky["warnings"]) >= 2
    lab = check_label(["FSSAI License Number", "Net Weight", "MRP"])
    assert not lab["label_ok"] and "nutrition facts" in lab["missing_on_label"]

def test_flipkart_math():
    f = flipkart_fees(649, 500)
    assert f["total_fees"] > 0 and f["you_receive"] < 649
    p = flipkart_profit(649, 340, 25, 500)
    assert p["profit_before_ads"] > 0 and p["break_even_roas"] is not None
    cheap = flipkart_fees(250); assert cheap["commission_pct"] == 14.0   # sasta = zyada slab

def test_control_center():
    c = Controls()
    assert c.can_run_ads(25, 100)["allowed"]
    assert not c.can_run_ads(10, 100)["allowed"]          # margin floor
    assert not c.can_run_ads(25, 0)["allowed"]            # stock zero
    c.emergency_stop()
    assert not c.can_run_ads(50, 500)["allowed"]          # kill switch sab par bhari
    c.resume(); assert c.can_run_ads(50, 500)["allowed"]
    assert "ab" in c.set_guardrail("daily_spend_cap", 5000)
    assert "Galat" in c.set_guardrail("kuch_bhi", 5)
    c.agents_enabled["A06"] = False
    assert not c.can_run_ads(50, 500)["allowed"]          # agent band = ads band

if __name__ == "__main__":
    for t in [test_claim_checker, test_flipkart_math, test_control_center]:
        t(); print("PASS", t.__name__)
    print("ALL V6 TESTS PASS")
