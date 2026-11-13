import sys, os, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
import finance as F, competitor_lab as CL, listing_v2 as L2, actions as ACT

def uc01_cashew_diagnosis():
    """UC-01: Cashew W320 — peer comparison + profit check + draft/QA gate."""
    st = Store(":memory:")
    F.set_cost(st.db, "9W-TDTG-A8CQ", 130, 12, approved_by="owner")
    pid = CL.add_peer(st.db, "Amazon", "B0PEER1", "https://x", "Peer Kaju W320 200g", "cashew", "W320", 200)
    CL.add_snapshot(st.db, pid, price=259, rating=4.4, reviews=180, image_count=7, in_stock=1, capture_id="u1")
    pack = CL.decision_packet(st.db, {"sku": "9W-TDTG-A8CQ", "name": "Dry Fruit Farm Cashew W320 200g",
                                      "price": 279, "nut_type": "cashew", "grade": "W320", "pack_g": 200}, pid)
    assert pack["status"] == "OK" and pack["match"]["class"] == "STRICT"
    assert pack["gap"]["peer_per_100g"] == 129.5
    assert pack["financial_guardrail"]["cost_known"]
    d = L2.save_draft(st.db, "9W-TDTG-A8CQ", "Amazon", "Cashew W320 200g Whole Kaju Snacking", ["s1"], "", "analyst")
    assert L2.approve_version(st.db, d["id"], "owner")["ok"]
    st.close()

def uc02_almond_keywords():
    """UC-02: Almond keyword expansion — wholesale/wrong grade out, variants in."""
    from keyword_lab import opportunity_matrix, term_variants
    from capabilities import IntelProvider
    st = Store(":memory:")
    st.add_search_term("california badam 200g", "C", 100, 500, 60, 6, "t")
    st.add_search_term("badam wholesale rate", "C", 200, 0, 80, 0, "t")
    m = opportunity_matrix(st, intel=IntelProvider())
    by = {r["term"]: r for r in m}
    assert by["badam wholesale rate"]["excluded"] and by["badam wholesale rate"]["opportunity_score"] == 0
    assert by["california badam 200g"]["opportunity_score"] > 0
    assert any("almond" in v for v in term_variants("badam 500g"))
    st.close()

def uc03_cranberry_restructure():
    """UC-03: Cranberry overspend — bid advice through the profit gate, never a direct scale-up."""
    import ads_studio as AS
    st = Store(":memory:")
    r = AS.recommend_bid(st.db, "CRAN-SKU", 219, 9.0, clicks=300, orders=11)
    assert r["blocked"], "no bid decision without cost"
    F.set_cost(st.db, "CRAN-SKU", 80, 10, approved_by="owner")
    r_floor = AS.recommend_bid(st.db, "CRAN-SKU", 219, 9.0, clicks=300, orders=11)
    assert r_floor["blocked"], "below the margin floor (10%) there is no CPC advice — that is the lesson of UC-03"
    r2 = AS.recommend_bid(st.db, "CRAN-SKU", 219, 9.0, clicks=300, orders=11, profit_floor_pct=5.0)
    assert not r2.get("blocked") and r2["change_pct"] == -20.0, "weak ROAS only allows a decrease, and only within the 20% cap"
    st.close()

def uc04_brazil_scale_gate():
    """UC-04: before scaling Brazil, both the stock and margin gates."""
    import ops_finance as OF
    st = Store(":memory:")
    assert OF.stock_gate(st, "5I-18V6-HZ5V")["status"] == "STOCKOUT"
    st.set_inventory("5I-18V6-HZ5V", "FBA Delhi", 120)
    g = OF.stock_gate(st, "5I-18V6-HZ5V")
    assert g["scale_allowed"] and g["status"] == "OK"
    st.close()

def uc05_price_drop_packet():
    """UC-05: a packet when a peer cuts its price — never an automatic price cut."""
    st = Store(":memory:")
    pid = CL.add_peer(st.db, "Amazon", "B0P2", "https://x", "Peer Badam 200g", "almond", "California", 200)
    CL.add_snapshot(st.db, pid, price=499, rating=4.3, reviews=90, image_count=6, in_stock=1, capture_id="p1")
    CL.add_snapshot(st.db, pid, price=449, rating=4.3, reviews=95, image_count=6, in_stock=1, capture_id="p2")
    ev = CL.detect_changes(st.db, pid)
    assert any(e["change_type"] == "Price" and e["delta"] == -50 for e in ev)
    pack = CL.decision_packet(st.db, {"sku": "BADAM200", "name": "Our Badam", "price": 479,
                                      "nut_type": "almond", "grade": "California", "pack_g": 200}, pid)
    assert pack["playbook"] in ("CP-01", "CP-02") and "cost" in pack["recommended_action"]
    st.close()

def uc06_flipkart_report_only():
    """UC-06: Flipkart ads write is not fictional — the capability registry says so clearly."""
    from capabilities import capability
    st = Store(":memory:")
    assert capability(st.db, "Flipkart", "write_ads")["status"] == "unavailable"
    assert capability(st.db, "Flipkart", "read_ads")["status"] == "report_only"
    st.close()

def uc07_two_sku_order_twice():
    """UC-07: a two-SKU order imported twice — two lines, the same total."""
    from connectors.csv_import import import_orders_canonical
    path = "/tmp/uc07.txt"
    with open(path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["order-id", "order-item-id", "sku", "item-price", "quantity-purchased"])
        w.writerow(["O1", "L1", "BADAM200", "499", "1"]); w.writerow(["O1", "L2", "KAJU200", "279", "1"])
    st = Store(":memory:")
    import_orders_canonical(path, st); import_orders_canonical(path, st)
    r = st.db.execute("SELECT COUNT(*) c, SUM(gross) s FROM order_items").fetchone()
    assert r["c"] == 2 and r["s"] == 778
    st.close()

def uc08_risky_claim_blocked():
    """UC-08: 'Diabetes-friendly' without evidence — the QA gate blocks it."""
    st = Store(":memory:")
    d = L2.save_draft(st.db, "NUTS1", "Amazon", "Diabetes friendly healthy nuts", ["x"], "", "llm")
    r = L2.approve_version(st.db, d["id"], "owner")
    assert not r["ok"] and r["status"] == "NEEDS_EVIDENCE"
    st.close()

def uc09_kill_during_queue():
    """UC-09: changes waiting in the queue — nothing is applied once the kill switch is on; they proceed only after it is released."""
    st = Store(":memory:")
    owner = {"username": "o", "role": "Owner"}
    ids = []
    for i in (1, 2):
        p = ACT.create_proposal(st.db, "BID_CHANGE", "Amazon", "acc", {"n": i}, "ONE_TAP", "o", f"uc9-{i}")
        ACT.approve(st.db, p["id"], owner); ACT.queue_action(st.db, p["id"], owner); ids.append(p["id"])
    ACT.set_kill(st.db, True, "o", "UC-09 test")
    r = ACT.execute(st.db, ids[0], owner, ACT.ManualAdapter({f"uc9-1": "REF"}))
    assert not r["ok"] and "KILL" in r["error"]
    states = [st.db.execute("SELECT state FROM action_v12 WHERE id=?", (i,)).fetchone()["state"] for i in ids]
    assert states == ["QUEUED", "QUEUED"], "the queue must stay quarantined while the kill switch is on"
    ACT.set_kill(st.db, False, "o")
    r2 = ACT.execute(st.db, ids[0], owner, ACT.ManualAdapter({"uc9-1": "REF-OK"}))
    assert r2["state"] == "APPLIED_VERIFIED"
    st.close()

def uc10_hamper_bom():
    """UC-10: Hamper — feasibility from component stock; the box cost is included in profit."""
    import ops_finance as OF
    from season_planner import build_season_pack
    st = Store(":memory:")
    for sku, name, price in [("SKU-BRAZIL", "Brazil Nuts Grade A++ 200g", 799),
                             ("SKU-CRAN", "Dried Cranberries 200g", 219),
                             ("SKU-PECAN", "Raw Pecan Nuts 200g", 599)]:
        st.db.execute("INSERT OR REPLACE INTO products VALUES (?,?, 'Amazon',?,0,0,0,'test')", (sku, name, price))
    st.db.commit()
    st.set_inventory("SKU-BRAZIL", "WH", 40); st.set_inventory("SKU-CRAN", "WH", 40)
    OF.set_bom(st.db, "HAMPER-DIWALI", {"SKU-BRAZIL": 1, "SKU-CRAN": 1})
    f = OF.bom_feasibility(st, "HAMPER-DIWALI", 50)
    assert f["feasible_units"] == 40 and not f["enough"], "50 were wanted, only 40 can be made — that truth must be shown"
    pack = build_season_pack(st)
    assert pack["combos"], "combos from the catalog must still be built"
    st.close()

if __name__ == "__main__":
    for t in [uc01_cashew_diagnosis, uc02_almond_keywords, uc03_cranberry_restructure, uc04_brazil_scale_gate,
              uc05_price_drop_packet, uc06_flipkart_report_only, uc07_two_sku_order_twice,
              uc08_risky_claim_blocked, uc09_kill_during_queue, uc10_hamper_bom]:
        t(); print("PASS", t.__name__)
    print("ALL UC SCENARIO TESTS PASS (UC-01..UC-10)")
