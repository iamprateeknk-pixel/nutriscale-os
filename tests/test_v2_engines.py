import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from approval_engine import Proposal, ApprovalEngine, decide_tier, Tier, guardrail_check
from organic_flywheel import flywheel, ad_spend_for_target_blended, rank_mode
from fba_planner import days_of_cover, replenishment, fba_vs_selfship, warehouse_decision
from unicommerce_agent import reconcile, allocate_stock, rto_report

def test_approval_tiers():
    assert decide_tier(Proposal("A06", "ADD_NEGATIVE", "waste term band")) == Tier.AUTO
    assert decide_tier(Proposal("A06", "BID_CHANGE", "bid +8%", change_pct=8)) == Tier.AUTO
    assert decide_tier(Proposal("A04", "LISTING_PATCH", "title upgrade")) == Tier.ONE_TAP
    assert decide_tier(Proposal("A06", "BUDGET_CHANGE", "budget +80%", change_pct=80)) == Tier.DOUBLE
    e = ApprovalEngine(daily_spend_cap=2000)
    r = e.submit(Proposal("A04", "LISTING_PATCH", "Badam title naya"))
    assert r["status"] == "WAITING_USER_APPROVAL"
    p = e.log[-1]; assert e.approve(p) == "APPROVED_EXECUTING"
    g = guardrail_check(stock_units=0, rating=4.5, proposed_daily_spend=500, cap=2000)
    assert not g["allowed"] and "STOCK_ZERO: ads auto-pause" in g["blocks"]

def test_flywheel_math():
    f = flywheel(ad_spend=25000, paid_sales=100000, organic_sales=100000)
    assert f["blended_roas"] == 8.0 and f["paid_roas"] == 4.0 and f["tacos_pct"] == 12.5
    assert ad_spend_for_target_blended(200000, 8) == 25000
    assert rank_mode(25, True) == "RANK_PUSH" and rank_mode(4, True) == "HARVEST"

def test_fba():
    assert days_of_cover(350, 10) == 35.0
    r = replenishment(stock=50, daily_sales=10)
    assert r["reorder_qty"] > 0 and "REPLENISH" in r["status"]
    c = fba_vs_selfship(649, fba_fee=75, self_courier=95, self_packing=20, self_rto_loss=18)
    assert c["cheaper"] == "FBA"
    assert "MARKETPLACE" in warehouse_decision(8, 180)

def test_unicommerce():
    rec = reconcile({"BADAM500": 100}, {"Amazon": {"BADAM500": 120}, "Flipkart": {"BADAM500": 100}})
    assert not rec["ok"] and any("OVERSELL" in i for i in rec["issues"])
    alloc = allocate_stock("BADAM500", 100, {"Amazon": 70, "Flipkart": 30})
    assert sum(alloc["BADAM500"].values()) == 100
    r = rto_report([{"sku": "KAJU500", "cost": 300}, {"sku": "KAJU500", "cost": 200}, {"sku": "BADAM500", "cost": 100}])
    assert r["worst_sku"] == "KAJU500" and r["total_return_loss"] == 600

if __name__ == "__main__":
    for t in [test_approval_tiers, test_flywheel_math, test_fba, test_unicommerce]:
        t(); print("PASS", t.__name__)
    print("ALL V2 TESTS PASS")
