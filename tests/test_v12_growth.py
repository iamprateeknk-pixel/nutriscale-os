import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
import finance as F

def test_ads_studio_profit_bid():
    import ads_studio as AS
    st = Store(":memory:")
    # cost unknown -> bid sifarish band
    r = AS.recommend_bid(st.db, "UNKNOWN-SKU", 500, 12.0, clicks=200, orders=10)
    assert r["blocked"] and "cost" in r["reason"].lower()
    # sample chhota -> band
    F.set_cost(st.db, "KAJU200", 90, 10, approved_by="o")
    r2 = AS.recommend_bid(st.db, "KAJU200", 279, 12.0, clicks=10, orders=1)
    assert r2["blocked"] and "Sample" in r2["reason"]
    # sahi case: margin healthy -> max_cpc hisaab se suggested <= current ka 20% band
    r3 = AS.recommend_bid(st.db, "KAJU200", 279, 12.0, clicks=200, orders=20)
    assert not r3.get("blocked") and abs(r3["change_pct"]) <= 20 and r3["max_cpc"] > 0
    # harvest: convert hua term negative NAHI banega
    st.add_search_term("kaju 1 kg", "BroadKaju", 300, 0, 50, 0, "t")
    st.add_search_term("kaju 1 kg", "ExactKaju", 200, 600, 30, 3, "t")
    st.add_search_term("bekar cheez", "BroadKaju", 150, 0, 40, 0, "t")
    h = AS.harvest_candidates(st)
    neg_terms = [n["term"] for n in h["negatives"]]
    assert "kaju 1 kg" not in neg_terms and "bekar cheez" in neg_terms
    assert any(x["term"] == "kaju 1 kg" for x in h["harvest"])
    st.close()

def test_keyword_honesty():
    from keyword_lab import opportunity_matrix, term_variants, rank_trend, record_rank
    from capabilities import IntelProvider
    st = Store(":memory:")
    st.add_search_term("badam 500g", "C1", 100, 300, 40, 4, "t")
    m = opportunity_matrix(st, intel=IntelProvider())
    row = m[0]
    assert row["search_volume"] is None and row["volume_status"] == "UNAVAILABLE", "volume invent nahi hona chahiye (QA-09)"
    assert any("almond" in v for v in term_variants("badam 500g"))
    record_rank(st.db, "Amazon", "brazil nuts", "SKU1", 12)
    t1 = rank_trend(st.db, "brazil nuts", "SKU1")
    assert t1["status"] == "INSUFFICIENT_DATA", "1 point par rank natija mana hai"
    record_rank(st.db, "Amazon", "brazil nuts", "SKU1", 9)
    record_rank(st.db, "Amazon", "brazil nuts", "SKU1", 6)
    t2 = rank_trend(st.db, "brazil nuts", "SKU1")
    assert t2["status"] == "OK" and t2["direction"] == "UP" and t2["delta"] == 6
    st.close()

def test_competitor_lab():
    import competitor_lab as CL
    own = {"nut_type": "cashew", "grade": "W320", "pack_g": 200, "processing": "raw"}
    assert CL.classify_peer(own, {"nut_type": "cashew", "grade": "W320", "pack_g": 200, "processing": "raw"})["class"] == "STRICT"
    w240 = CL.classify_peer(own, {"nut_type": "cashew", "grade": "W240", "pack_g": 200, "processing": "raw"})
    assert w240["class"] != "STRICT", "W240 ko W320 ka exact peer kehna galti hai (QA-08)"
    assert CL.price_per_100g(259, 200) == 129.5
    st = Store(":memory:")
    pid = CL.add_peer(st.db, "Amazon", "B0PEER", "https://x", "Peer Kaju W320 200g", "cashew", "W320", 200)
    CL.add_snapshot(st.db, pid, price=279, rating=4.2, reviews=100, image_count=5, in_stock=1, capture_id="c1")
    assert CL.detect_changes(st.db, pid) == [], "ek snapshot par change event nahi banta"
    CL.add_snapshot(st.db, pid, price=259, rating=4.2, reviews=110, image_count=5, in_stock=1, capture_id="c2")
    ev = CL.detect_changes(st.db, pid)
    assert any(e["change_type"] == "Price" and e["delta"] == -20 for e in ev)
    pack = CL.decision_packet(st.db, {"sku": "KAJU200", "name": "Apna Kaju W320 200g", "price": 279,
                                      "nut_type": "cashew", "grade": "W320", "pack_g": 200}, pid)
    assert pack["status"] == "OK" and not pack["financial_guardrail"]["cost_known"]
    assert "cost" in pack["recommended_action"], "cost unknown par price faisla nahi — packet yahi kahe"
    st.close()

def test_listing_v2_and_versions():
    import listing_v2 as L2
    s = L2.score_v2({"title_len": 150, "keywords_in_title": 5, "attributes_filled": 0.9, "image_count": 7,
                     "has_size_proof": True, "bullets": 5, "rating": 4.3, "review_count": 120,
                     "price_per_100g": 139.5, "peer_median_per_100g": 135, "fba": True})
    assert s["score"] > 80 and s["version"].startswith("listing-score-v2")
    st = Store(":memory:")
    d = L2.save_draft(st.db, "KAJU200", "Amazon", "Kaju W320 200g | Snacking", ["b1"], "terms", "analyst")
    ap = L2.approve_version(st.db, d["id"], "owner")
    assert ap["ok"], "saaf copy approve honi chahiye"
    d2 = L2.save_draft(st.db, "KAJU200", "Amazon", "Kaju nitrogen flush pack", ["b1"], "terms", "analyst")
    ap2 = L2.approve_version(st.db, d2["id"], "owner")
    assert not ap2["ok"] and ap2["status"] == "NEEDS_EVIDENCE", "bina saboot ka dawa rukna chahiye (QA-10)"
    rb = L2.rollback_to(st.db, "KAJU200", "Amazon", 1, "owner")
    assert rb["version"] == 3 and rb["status"] == "DRAFT"
    st.close()

def test_experiments_and_learning():
    import experiments as EX
    st = Store(":memory:")
    e = EX.create_experiment(st.db, "Nayi main image", "KAJU200", "Amazon", "Size-proof photo CVR badhayegi", "CVR", "image change", "owner")
    r_small = EX.evaluate(st.db, e["id"], {"rate": 0.03, "n": 40}, {"rate": 0.06, "n": 40})
    assert r_small["verdict"] == "INCONCLUSIVE", "chhote sample par jeet ka elaan mana hai"
    e2 = EX.create_experiment(st.db, "Title test", "BRAZIL200", "Amazon", "h", "CVR", "title", "owner")
    r_big = EX.evaluate(st.db, e2["id"], {"rate": 0.03, "n": 2000}, {"rate": 0.05, "n": 2000})
    assert r_big["verdict"] == "WIN"
    assert not EX.record_outcome(st.db, "a1", 7, "CVR", 3.0, 5.0, executed=False)["recorded"]
    assert EX.record_outcome(st.db, "a1", 7, "CVR", 3.0, 5.0, executed=True)["recorded"]
    st.close()

def test_settlements_bom_agency_llm_ops():
    import ops_finance as OF, agency as AG
    st = Store(":memory:")
    st.set_inventory("BADAM100", "WH", 500); st.set_inventory("KAJU100", "WH", 300)
    OF.set_bom(st.db, "HAMPER1", {"BADAM100": 1, "KAJU100": 1})
    f = OF.bom_feasibility(st, "HAMPER1", 100)
    assert f["feasible_units"] == 300 and f["enough"]
    g = OF.stock_gate(st, "GHAYAB-SKU")
    assert not g["scale_allowed"] and g["status"] == "STOCKOUT"
    t = AG.add_task(st.db, "Cranberry listing update")
    assert not AG.complete_task(st.db, t["id"])["ok"], "saboot bina task done nahi"
    assert AG.complete_task(st.db, t["id"], "screenshot-ref-1")["ok"]
    AG.add_fee(st.db, "2026-10", 15000)
    sc = AG.scorecard(st.db)
    assert sc["tasks_done_with_evidence"] == 1 and sc["fees_total"] == 15000
    # LLM budget: chhota budget set karke block parkho
    OF.LLM_BUDGET["daily_inr"] = 1.0
    class FakeLLM:
        def generate(self, p, system=""): return "ok"
    r = OF.governed_llm_call(st.db, FakeLLM(), "A04", "prompt", est_cost_inr=5.0)
    assert not r["ok"] and r["blocked"] == "DAILY_BUDGET"
    h = OF.system_health(st)
    assert "kill_switch" in h and "capabilities" in h
    st.close()

def test_rank_diagnostic_and_funnel():
    from keyword_lab import rank_diagnostic, rank_funnel
    st = Store(":memory:")
    st.db.execute("INSERT OR REPLACE INTO products VALUES ('SKU-R','Rank Wala', 'Amazon', 300, 0, 3.8, 40, 't')"); st.db.commit()
    d = rank_diagnostic(st, "kaju", "SKU-R")
    hyps = " ".join(h["hypothesis"] for h in d["hypotheses"])
    assert "Stock" in hyps, "stockout sabse pehle parakhna chahiye"
    st.set_inventory("SKU-R", "WH", 100)
    d2 = rank_diagnostic(st, "kaju", "SKU-R")
    assert any("Rating" in h["hypothesis"] for h in d2["hypotheses"]), "3.8 rating par trust-wali parikalpana aani chahiye"
    st.add_search_term("kaju", "C", 50, 300, 25, 3, "t")
    f = rank_funnel(st, "kaju", "SKU-R")
    assert f["clicks"] == 25 and f["orders"] == 3 and "UNAVAILABLE" in f["rank_data"]
    st.close()

if __name__ == "__main__":
    for t in [test_ads_studio_profit_bid, test_keyword_honesty, test_competitor_lab, test_rank_diagnostic_and_funnel,
              test_listing_v2_and_versions, test_experiments_and_learning, test_settlements_bom_agency_llm_ops]:
        t(); print("PASS", t.__name__)
    print("ALL V12 GROWTH TESTS PASS")
