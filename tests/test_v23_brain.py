"""V23 TESTS — marketplace knowledge, listing rules (75-char title, 200-byte backend, FSSAI),
keyword intel (SQP funnel + placement), agent brain (learning from outcomes, lessons from your own data)."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from platform_core import ensure_v12, now_utc

def test_knowledge_has_sources_and_status():
    import marketplace_knowledge as MK
    ids = [r["id"] for r in MK.KNOWLEDGE]
    assert len(ids) == len(set(ids)), "rule ids must not repeat"
    for r in MK.KNOWLEDGE:
        assert r["status"] in ("OFFICIAL", "MULTI_SOURCE", "SINGLE_SOURCE", "HEURISTIC")
        assert 0 < r["reliability"] <= 1
        if r["status"] != "HEURISTIC": assert r["sources"], f"{r['id']} without a source"
    assert MK.rule("AMZ-T-01")["value"]["max_chars"] == 75
    assert MK.rule("AMZ-K-01")["value"]["max_bytes"] == 200
    import datetime
    assert MK.stale_rules(today=datetime.date(2027, 6, 1)), "rules older than 90 days must show as stale"
    st = Store(":memory:")
    a = MK.seed_knowledge(st); b = MK.seed_knowledge(st)
    assert a["added"] > 0 and b["added"] == 0, "no duplicates on a second seed"
    st.close()

def test_title_rules():
    import listing_rules as LR
    long_t = "Dry Fruit Farm California Almonds Badam 500g | Premium Quality, Fresh & Hygienically Packed | Ideal for Snacking"
    ids = {i["rule_id"] for i in LR.audit_title(long_t)}
    assert "AMZ-T-01" in ids, "75 se lamba title BLOCK"
    rep = LR.audit_title("Almonds Almond Badam Almonds 500g")
    assert any(i["rule_id"] == "AMZ-T-03" for i in rep), "plurals count as repeats too"
    assert any(i["rule_id"] == "AMZ-T-04" for i in LR.audit_title("Best Almonds!! 500g"))
    t = LR.build_title_amazon("Dry Fruit Farm", "California Almonds", "Jumbo", "500g", "badam almonds")
    assert t["chars"] <= 75 and t["title"].endswith("500g") and "Badam" in t["title"]
    assert not [i for i in t["issues"] if i["severity"] == "BLOCK"], t
    # Even a very long input is not cut mid-way; the weight is kept
    t2 = LR.build_title_amazon("Dry Fruit Farm Premium Foods", "California Almonds Badam Giri", "Extra Jumbo Size Grade", "1kg", "almond nuts")
    assert t2["chars"] <= 75 and t2["title"].endswith("1kg")

def test_backend_packing_bytes_and_dedup():
    import listing_rules as LR
    title = "Dry Fruit Farm California Almonds Jumbo 500g"
    cands = ["badam", "almonds", "badaam giri", "बादाम", "happilo", "best", "mamra gurbandi"] + [f"word{i}" for i in range(60)]
    r = LR.pack_backend_terms(cands, title, competitor_brands=["Happilo"])
    assert r["bytes"] <= 200
    w = r["backend_terms"].split()
    assert "almonds" not in w, "no title word in the backend"
    assert "happilo" not in w and "best" not in w, "competitor brand / subjective bahar"
    assert "बादाम" in w and "badam" in w
    assert r["dropped_for_space"], "words left out when space runs out are recorded"
    a = LR.audit_backend("badam, kaju " + "x" * 300, title)
    assert any(i["rule_id"] == "AMZ-K-01" and i["severity"] == "BLOCK" for i in a)
    assert any(i["rule_id"] == "AMZ-K-02" for i in a)

def test_bullets_fssai_images():
    import listing_rules as LR
    bad = ["Tasty 😀 snack", "Brand™ quality", "Full refund if not satisfied", "Visit www.example.com", "Cures diabetes, natural taste"]
    a = LR.audit_listing("Amazon", "Dry Fruit Farm Almonds 500g", bad, "badam",
                         images=[{"role": "main", "width": 800, "height": 800, "bg_rgb": (250, 250, 250), "has_text": True}])
    ids = [(i["rule_id"], i["severity"]) for i in a["issues"]]
    assert ("AMZ-B-01", "BLOCK") in ids and ("AMZ-B-02", "BLOCK") in ids and ("FS-C-01", "BLOCK") in ids
    assert ("AMZ-I-01", "BLOCK") in ids, "off-white main image BLOCK"
    assert any(r == "FS-C-02" for r, _ in ids), "'natural' is an FSSAI conditional word — warning"
    assert not a["can_publish"] and a["compliance_score"] < 50

def test_sqp_funnel_diagnosis():
    import keyword_intel as KI
    st = Store(":memory:"); ensure_v12(st.db)
    def add(q, sv, im, bim, cl, bcl, ca, bca, pu, bpu):
        st.db.execute("""INSERT INTO brand_analytics(platform,seller_account,report_type,period_start,period_end,query,search_volume,
                         impressions,brand_impressions,clicks,brand_clicks,cart_adds,brand_cart_adds,purchases,brand_purchases,batch_id,imported_at)
                         VALUES ('Amazon','default','SQP','2026-10-01','2026-10-31',?,?,?,?,?,?,?,?,?,?, 'b', ?)""",
                      (q, sv, im, bim, cl, bcl, ca, bca, pu, bpu, now_utc()))
    add("almonds 1kg", 9000, 100000, 3000, 8000, 400, 2000, 150, 900, 80)       # 3% impr, ~9% purchase -> SCALE
    add("badam", 20000, 200000, 20000, 15000, 600, 3000, 200, 1500, 120)       # 10% impr, 4% click -> TILE
    add("kaju w240", 5000, 50000, 5000, 4000, 500, 900, 90, 400, 10)          # click 12.5%, purchase 2.5% -> OFFER
    add("pista", 3000, 30000, 100, 2000, 10, 300, 1, 100, 0)                   # 0.3% -> NOT_VISIBLE
    st.db.commit()
    f = KI.sqp_funnel(st.db)
    d = {q["query"]: q["diagnosis"] for q in f["queries"]}
    assert d == {"almonds 1kg": "SCALE_OPPORTUNITY", "badam": "TILE_PROBLEM",
                 "kaju w240": "OFFER_PROBLEM", "pista": "NOT_VISIBLE"}, d
    assert f["queries"][0]["priority"] == 1
    st.close()
    st2 = Store(":memory:")
    assert KI.sqp_funnel(st2.db)["available"] is False, "honestly empty when there is no data"
    st2.close()

def test_placement_plan_and_listing_build():
    from agents.listing_agent import ListingAgent
    import keyword_intel as KI
    st = Store(":memory:")
    for term, cl, pu, sp, sa in [("california almonds 500g", 200, 30, 900, 9000), ("badam", 150, 12, 600, 3600),
                                 ("almonds wholesale", 50, 0, 300, 0), ("roasted almonds", 120, 0, 450, 0),
                                 ("mamra badam", 60, 6, 200, 2400)]:
        st.add_search_term(term, "C1", sp, sa, cl, pu)
    plan = KI.placement_plan(st, "almond")["plan"]
    assert plan["TITLE"] == ["california almonds 500g"]
    neg = [n["term"] for n in plan["NEGATIVE_ADS"]]
    assert "almonds wholesale" in neg and "roasted almonds" in neg
    assert "badaam" in plan["BACKEND"], "shabdkosh ke Hinglish roop backend me"
    facts = {"grade_detail": "Jumbo size badam", "origin": "California",
             "nutrition_line": "protein and fibre", "pack_line": "food-grade zip pouch"}
    # V24 NS-P-01: 'California' (origin) and 'mamra' (grade) claims without evidence are BLOCKED in the builder itself
    nofacts = ListingAgent(st).build_listing("SKU-ALM-500", "Dry Fruit Farm", "California Almonds", "almond", "Jumbo", "500g", facts=facts)
    assert nofacts["blocked"] and nofacts["proposal"] is None
    assert {"NS-P-01"} == {i["rule_id"] for i in nofacts["audit"]["issues"] if i["severity"] == "BLOCK"}
    import fact_registry as FR
    FR.add_fact(st.db, "SKU-ALM-500", "ORIGIN", "California", "supplier-invoice-123", "owner")
    FR.add_fact(st.db, "SKU-ALM-500", "ORIGIN_GRADE", "Mamra", "supplier-invoice-123", "owner")
    r = ListingAgent(st).build_listing("SKU-ALM-500", "Dry Fruit Farm", "California Almonds", "almond", "Jumbo", "500g", facts=facts)
    assert r["title_chars"] <= 75 and len(r["item_highlights"]) <= 125 and r["backend_bytes"] <= 200
    assert not r["blocked"], r["audit"]["issues"]
    a = st.db.execute("SELECT payload FROM action_v12 WHERE id=?", (r["proposal"]["id"],)).fetchone()
    assert "AMZ-T-01" in json.loads(a["payload"])["rule_ids"], "rule_ids in the proposal — only then can outcomes teach"
    again = ListingAgent(st).build_listing("SKU-ALM-500", "Dry Fruit Farm", "California Almonds", "almond", "Jumbo", "500g",
                                           facts={"grade_detail": "Jumbo size badam", "origin": "California",
                                                  "nutrition_line": "protein and fibre", "pack_line": "food-grade zip pouch"})
    assert again["proposal"]["duplicate"] is True, "the same listing does not become a proposal again"
    st.close()

def test_brain_learns_from_verified_outcomes_only():
    import agent_brain as AB
    st = Store(":memory:"); db = st.db
    AB.seed_playbook(db)
    prior = db.execute("SELECT confidence FROM playbook_rules WHERE rule_id='AMZ-Q-03'").fetchone()["confidence"]
    def outcome(success, attribution):
        cur = db.execute("INSERT INTO action_v12(idempotency_key,kind,platform,payload,state) VALUES (?,?,?,?,?)",
                         (os.urandom(6).hex(), "BID_CHANGE", "Amazon", json.dumps({"rule_ids": ["AMZ-Q-03"]}), "EXECUTED"))
        db.execute("INSERT INTO outcomes(action_id,kind,window_days,success,attribution,at) VALUES (?,?,?,?,?,?)",
                   (cur.lastrowid, "BID_CHANGE", 14, success, attribution, now_utc()))
        db.commit()
    outcome(1, "CONTAMINATED"); outcome(0, "LOW_COVERAGE")
    assert AB.learn_from_outcomes(db)["applied"] == 0, "learning only from VERIFIED"
    outcome(1, "VERIFIED"); outcome(1, "VERIFIED")
    r1 = AB.learn_from_outcomes(db); r2 = AB.learn_from_outcomes(db)
    assert r1["applied"] == 2 and r2["applied"] == 0, "one outcome is counted only once"
    up = db.execute("SELECT confidence FROM playbook_rules WHERE rule_id='AMZ-Q-03'").fetchone()["confidence"]
    assert up > prior
    for _ in range(3): outcome(0, "VERIFIED")
    AB.learn_from_outcomes(db)
    row = db.execute("SELECT status, wins, losses FROM playbook_rules WHERE rule_id='AMZ-Q-03'").fetchone()
    assert row["status"] == "DISABLED" and row["wins"] == 2 and row["losses"] == 3, dict(row)
    assert "AMZ-Q-03" not in [a["rule_id"] for a in AB.advise(db, agent="A03")], "a disabled rule is not in the advice"
    AB.seed_playbook(db)
    assert db.execute("SELECT status FROM playbook_rules WHERE rule_id='AMZ-Q-03'").fetchone()["status"] == "DISABLED", \
        "re-seeding does not erase what was learned"
    assert AB.reenable(db, "AMZ-Q-03", "owner")["ok"]
    st.close()

def test_brain_learns_from_own_data_and_job():
    import agent_brain as AB, job_handlers as JH
    st = Store(":memory:")
    assert AB.learn_from_data(st)["lessons_updated"] == 0, "no data, no lessons"
    for term, cl, pu, sp, sa in [("kaju w240", 100, 15, 500, 6000), ("cashew 1kg", 80, 6, 300, 2500),
                                 ("dry fruits cheap", 90, 0, 800, 0)]:
        st.add_search_term(term, "C", sp, sa, cl, pu)
    msg = JH.build_handlers(st)["learning_crawl"]()
    assert "Playbook" in msg and "lessons" in msg, msg
    w = AB.advise(st.db, agent="A03", topic="keyword_research")
    own = [a for a in w if a["rule_id"] == "OWN-KW-WINNERS"]
    assert own and "kaju w240" in own[0]["statement"]
    waste = [a for a in AB.advise(st.db, agent="A06") if a["rule_id"] == "OWN-KW-WASTE"]
    assert waste and waste[0]["evidence"]["total_wasted"] == 800
    n = st.db.execute("SELECT COUNT(*) c FROM playbook_rules").fetchone()["c"]
    JH.build_handlers(st)["learning_crawl"]()
    assert st.db.execute("SELECT COUNT(*) c FROM playbook_rules").fetchone()["c"] == n, "no duplicates when run daily"
    rep = AB.brain_report(st.db)
    assert rep["own_data_lessons"] >= 2 and "A03" in rep["per_agent"]
    assert JH.build_handlers(st)["backup_restore"]().startswith("SKIP"), "an in-memory DB backup must not litter the repo"
    st.close()

def test_v23_http_endpoints():
    import subprocess, time, urllib.request, socket, tempfile
    with socket.socket() as so: so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]
    dbf = tempfile.mktemp(suffix=".db")
    env = {**os.environ, "NUTRISCALE_DB": dbf, "PORT": str(port),
           "NUTRISCALE_OWNER_USER": "own", "NUTRISCALE_OWNER_PASSWORD": "pw-123456"}
    app = os.path.join(os.path.dirname(__file__), "..", "backend", "app.py")
    p = subprocess.Popen([sys.executable, app], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1); break
            except Exception: time.sleep(0.1)
        def call(path, body=None, tok=None):
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {tok}"} if tok else {})},
                                         method="POST" if body is not None else "GET")
            return json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
        tok = call("/api/v1/auth/login", {"username": "own", "password": "pw-123456"})["data"]["token"]
        assert call("/api/v1/knowledge?platform=Amazon", tok=tok)["data"]["rules"]
        assert "report" in call("/api/v1/brain", tok=tok)["data"]
        assert "plan" in call("/api/v1/keywords/plan?nut=cashew", tok=tok)["data"]
        a = call("/api/v1/listings/audit", {"title": "Best Almonds!!", "bullets": []}, tok)["data"]
        assert a["can_publish"] is False
    finally:
        p.terminate(); p.wait(5)
        if os.path.exists(dbf): os.remove(dbf)

def test_change_password_revokes_sessions():
    import auth
    st = Store(":memory:")
    auth.create_user(st.db, "malik", "oldpass123", "Owner")
    tok = auth.verify_login(st.db, "malik", "oldpass123")["token"]
    assert not auth.change_password(st.db, "malik", "short")["ok"], "a password shorter than 8 is refused"
    assert auth.change_password(st.db, "malik", "NewPass!2026")["ok"]
    assert auth.verify_login(st.db, "malik", "oldpass123") is None, "the old password no longer works"
    assert auth.verify_login(st.db, "malik", "NewPass!2026")["token"]
    assert auth.user_from_token(st.db, tok) is None, "purana login token band"
    assert not auth.change_password(st.db, "nobody", "NewPass!2026")["ok"]
    st.close()

if __name__ == "__main__":
    for t in [test_knowledge_has_sources_and_status, test_title_rules, test_backend_packing_bytes_and_dedup,
              test_bullets_fssai_images, test_sqp_funnel_diagnosis, test_placement_plan_and_listing_build,
              test_brain_learns_from_verified_outcomes_only, test_brain_learns_from_own_data_and_job, test_v23_http_endpoints,
              test_change_password_revokes_sessions]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V23 TESTS PASS")
