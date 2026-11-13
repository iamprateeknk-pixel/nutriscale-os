"""V24 TESTS — market research niyam (ads/reviews/A+/events/q-commerce/Flipkart ads), growth playbook
(break-even ACOS, campaign structure, sale calendar, review plan, today), manual cycle me brain, naya dashboard."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

def test_v24_knowledge_rules():
    import marketplace_knowledge as MK
    for rid in ("AMZ-A-01", "AMZ-A-02", "AMZ-A-03", "AMZ-A-04", "AMZ-A-05", "AMZ-R-01", "AMZ-R-02", "AMZ-C-01",
                "IN-E-01", "IN-E-02", "IN-M-01", "IN-Q-01", "FK-A-01", "FK-A-02", "NS-P-01"):
        r = MK.rule(rid)
        if r["status"] != "HEURISTIC": assert len(r["sources"]) >= 1, rid
    assert MK.rule("AMZ-A-06")["status"] == "SINGLE_SOURCE" and MK.rule("AMZ-A-06")["reliability"] <= 0.5, \
        "ek-source wali salah ko kam bharosa"
    assert len(MK.rules_for(agent="A06")) >= 8, "Ads agent ke paas ab apna playbook hai"

def test_break_even_acos():
    import growth_playbook as GP, finance as F
    st = Store(":memory:")
    st.upsert_product("SKU-K", "Kaju", "Amazon", 650)
    assert GP.break_even(st.db, "SKU-K")["status"] == "DATA_NEEDED", "cost bina break-even ka number nahi"
    F.set_cost(st.db, "SKU-K", 300, 20, 0, "test", approved_by="o")
    b = GP.break_even(st.db, "SKU-K")
    assert b["status"] == "OK" and 0 < b["break_even_acos_pct"] < 60
    assert abs(b["target_acos_pct"] - (b["break_even_acos_pct"] - 10)) < 0.11, "target = break-even − 10% munafa"
    assert abs(b["break_even_roas"] - 100 / b["break_even_acos_pct"]) < 0.05
    F.set_cost(st.db, "SKU-L", 700, 0, 0, "test", approved_by="o")
    loss = GP.break_even(st.db, "SKU-L", price=500)
    assert loss["break_even_acos_pct"] < 0 and "Loss-making" in loss["note"]
    st.close()

def test_ads_structure_findings():
    import growth_playbook as GP
    st = Store(":memory:")
    assert GP.ads_structure(st)["status"] == "DATA_NEEDED"
    for term, camp, cl, pu, sp, sa in [("kaju w240", "SP | Kaju | AUTO", 100, 6, 500, 3000),
                                       ("kaju w240", "SP | Kaju | EXACT", 80, 8, 400, 4000),
                                       ("cashew cheap", "SP | Kaju | AUTO", 60, 0, 300, 0),
                                       ("cashew 1kg", "SP | Kaju | AUTO", 40, 3, 200, 1500)]:
        st.add_search_term(term, camp, sp, sa, cl, pu)
    a = GP.ads_structure(st)
    assert a["campaign_types"] == {"AUTO": 1, "EXACT": 1}
    msgs = " | ".join(f["message"] for f in a["findings"])
    assert "bidding against yourself" in msgs, "Exact + Auto dono me ek term = self-competition"
    assert a["harvest_pending"] == 1, "cashew 1kg (3 orders, sirf Auto me) harvest-yogya; kaju w240 pehle se Exact me"
    assert a["wasted_spend"] == 300
    assert 0 <= a["structure_score"] < 100
    st.close()
    st2 = Store(":memory:")
    st2.add_search_term("x", "Campaign 1", 10, 0, 1, 0)
    rids = {f["rule_id"] for f in GP.ads_structure(st2)["findings"]}
    assert {"AMZ-A-01", "AMZ-A-02"} <= rids, "na Auto na Exact — dono chetaavni"
    st2.close()

def test_event_calendar():
    import growth_playbook as GP
    c = GP.event_calendar("2026-11-11")
    names = [e["event"] for e in c["events"]]
    assert names[0] == "Wedding season" and "Christmas / New Year gifting" in names
    assert all(e["days_to_start"] <= 120 for e in c["events"])
    w = c["events"][0]
    assert w["fba_stock_by"] < w["ready_by"] < w["start"], "FBA stock pehle, phir taiyaari, phir sale"
    assert "ESTIMATES" in c["note"], "tareekhein anumaan hain — saaf likha ho"
    conf = GP.event_calendar("2026-11-11", confirmed={"Republic Day Sale": "2027-01-15"})
    rd = [e for e in conf["events"] if e["event"] == "Republic Day Sale"][0]
    assert rd["start"] == "2027-01-15" and rd["confirmed"] is True

def test_review_plan_policy_safe():
    import growth_playbook as GP
    st = Store(":memory:")
    st.upsert_product("A", "Naya", "Amazon", 500, 0, 4.5, 8)
    st.upsert_product("B", "Purana", "Amazon", 500, 0, 3.6, 400)
    st.upsert_product("C", "Flipkart wala", "Flipkart", 500, 0, 4.6, 3)
    r = GP.review_plan(st.db)
    by = {(i["sku"], i["action"][:4]) for i in r["items"]}
    assert ("A", "Vine") in by and ("B", "Rati") in by and not any(s == "C" for s, _ in by), "Vine sirf Amazon"
    assert "suspend" in r["policy"], "incentive-review ka khatra saaf likha ho"
    st.close()

def test_today_aggregator_and_cycle():
    import growth_playbook as GP
    from agents.governance import GovernanceAgent
    st = Store(":memory:")
    t = GP.today(st)
    assert t["setup_pct"] == 0 and t["tasks"] and t["tasks"][-1]["area"] in ("setup", "events")
    st.add_search_term("badam", "SP | Badam | AUTO", 900, 0, 50, 0)
    t2 = GP.today(st)
    assert any(x["area"] == "ads" and x["rule_id"] == "AMZ-A-03" for x in t2["tasks"])
    assert t2["tasks"][0]["priority"] == 1, "zaroori kaam sabse upar"
    rep = GovernanceAgent(st).daily_cycle()
    jobs = {j["job"]: j for j in rep["jobs"]}
    assert "Playbook" in jobs["learning_crawl"]["output"], "manual cycle bhi asal seekh-chakra chalaye"
    assert jobs["backup_restore"]["status"] == "DONE" and "SKIP" in jobs["backup_restore"]["output"], \
        "backup handler ab manual cycle me bhi (in-memory par imaandaar SKIP)"
    assert st.db.execute("SELECT COUNT(*) c FROM playbook_rules").fetchone()["c"] >= 40
    st.close()

def test_listing_evidence_gate_and_safe_defaults():
    from agents.listing_agent import ListingAgent, generate_bullets
    b = " ".join(generate_bullets({}))
    for claim in ("nitrogen", "FSSAI", "replacement"):
        assert claim not in b, f"default bullets me bina-saboot dawa '{claim}' nahi hona chahiye"
    assert "FSSAI lic. 123" in " ".join(generate_bullets({"fssai": "123"})), "tathya diya ho to hi"
    st = Store(":memory:")
    r = ListingAgent(st).build_listing("S", "Dry Fruit Farm", "Cashew Nuts", "cashew", "W240", "500g",
                                       facts={"pack_line": "nitrogen-flushed pouch"})
    assert r["blocked"] and any(i["rule_id"] == "NS-P-01" for i in r["audit"]["issues"])
    st.close()

def test_dashboard_v24():
    html = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")).read()
    for key in ["today", "listingbuilder", "keywordplan", "sqp", "growth", "brain", "knowledge"]:
        assert f"['{key}'" in html, f"naya screen gayab: {key}"
    for api in ["/api/v1/today", "/api/v1/listings/build", "/api/v1/keywords/plan", "/api/v1/keywords/sqp",
                "/api/v1/growth/ads-structure", "/api/v1/growth/events", "/api/v1/growth/break-even", "/api/v1/brain", "/api/v1/knowledge"]:
        assert api in html, f"dashboard {api} se nahi judta"
    assert "prefers-color-scheme: dark" in html and 'data-theme="dark"' in html, "dark mode"
    assert "alert(" not in html and "prompt(" not in html and "confirm(" not in html, "browser popups ki jagah toast/modal"
    assert "@media (max-width:860px)" in html, "mobile layout"
    import re
    assert not re.search(r'class="grid g2" style="grid-template-columns', html), "inline grid mobile ko todta hai"

def test_v24_http():
    import subprocess, time, urllib.request, socket, tempfile
    with socket.socket() as so: so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]
    dbf = tempfile.mktemp(suffix=".db")
    env = {**os.environ, "NUTRISCALE_DB": dbf, "PORT": str(port),
           "NUTRISCALE_OWNER_USER": "own", "NUTRISCALE_OWNER_PASSWORD": "pw-123456"}
    p = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "..", "backend", "app.py")],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1); break
            except Exception: time.sleep(0.1)
        def call(path, body=None, tok=None):
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {tok}"} if tok else {})})
            return json.loads(urllib.request.urlopen(req, timeout=5).read().decode())["data"]
        tok = call("/api/v1/auth/login", {"username": "own", "password": "pw-123456"})["token"]
        assert "tasks" in call("/api/v1/today", tok=tok)
        assert call("/api/v1/growth/ads-structure", tok=tok)["status"] == "DATA_NEEDED"
        assert call("/api/v1/growth/events", tok=tok)["events"] is not None
        assert call("/api/v1/growth/break-even?sku=NOPE", tok=tok)["status"] == "DATA_NEEDED"
        assert "items" in call("/api/v1/growth/reviews", tok=tok)
        assert call("/api/v1/products", tok=tok)["products"] == []
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/today", timeout=5); assert False, "bina login 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401
    finally:
        p.terminate(); p.wait(5)
        if os.path.exists(dbf): os.remove(dbf)

if __name__ == "__main__":
    for t in [test_v24_knowledge_rules, test_break_even_acos, test_ads_structure_findings, test_event_calendar,
              test_review_plan_policy_safe, test_today_aggregator_and_cycle, test_listing_evidence_gate_and_safe_defaults,
              test_dashboard_v24, test_v24_http]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V24 TESTS PASS")
