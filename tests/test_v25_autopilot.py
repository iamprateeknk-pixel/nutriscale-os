"""V25 TESTS — Growth Autopilot (findings -> approval-gated proposals), the full learning cycle,
weekly report, scheduler additions, inbox summary."""
import os, sys, json, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from platform_core import now_utc

def _seed(st):
    for term, camp, cl, pu, sp, sa in [("kaju w240", "SP | Kaju | AUTO", 100, 6, 500, 3000),
                                       ("kaju w240", "SP | Kaju | EXACT", 80, 8, 400, 4000),
                                       ("cashew cheap", "SP | Kaju | AUTO", 60, 0, 300, 0),
                                       ("cashew 1kg", "SP | Kaju | AUTO", 40, 3, 200, 1500)]:
        st.add_search_term(term, camp, sp, sa, cl, pu)

def test_autopilot_creates_safe_proposals():
    import growth_autopilot as GA
    st = Store(":memory:"); _seed(st)
    pre = GA.run(st, dry_run=True)
    assert st.db.execute("SELECT COUNT(*) c FROM action_v12").fetchone()["c"] == 0, "a dry run creates nothing"
    kinds = sorted(c["kind"] for c in pre["created"])
    assert kinds == ["ADD_NEGATIVE_EXACT", "ADD_NEGATIVE_EXACT", "HARVEST_TO_EXACT"], kinds
    r = GA.run(st)
    assert len(r["created"]) == 3
    rows = [dict(x) for x in st.db.execute("SELECT kind, state, tier, payload FROM action_v12")]
    assert all(x["state"] == "APPROVAL_PENDING" and x["tier"] == "ONE_TAP" for x in rows), "never goes live by itself"
    for x in rows:
        p = json.loads(x["payload"])
        assert p["rule_ids"] and p["campaign"] and p["source"] == "growth_autopilot", "campaign/rule_ids for measuring + learning"
    negs = {json.loads(x["payload"])["term"] for x in rows if x["kind"] == "ADD_NEGATIVE_EXACT"}
    assert negs == {"cashew cheap", "kaju w240"}, "waste term + self-competition (in the Auto campaign)"
    neg_kaju = [json.loads(x["payload"]) for x in rows if json.loads(x["payload"]).get("term") == "kaju w240"][0]
    assert neg_kaju["campaign"] == "SP | Kaju | AUTO", "a winning term in our own Exact campaign is never made negative"
    again = GA.run(st)
    assert again["created"] == [] and again["already_proposed_this_week"] == 3, "no duplicates when run daily"
    nxt = GA.run(st, today=datetime.date.today() + datetime.timedelta(days=7))
    assert len(nxt["created"]) == 3, "next week (findings still open) it reminds again"
    st.close()

def test_converted_term_never_negated_and_cap():
    import growth_autopilot as GA
    st = Store(":memory:")
    st.add_search_term("badam", "SP | Badam | AUTO", 300, 0, 40, 0)
    st.add_search_term("badam", "SP | Badam | BROAD", 100, 900, 20, 3)
    for i in range(30):
        st.add_search_term(f"junk term {i}", "SP | Badam | AUTO", 150, 0, 10, 0)
    r = GA.run(st)
    rows = [(x["kind"], json.loads(x["payload"]).get("term")) for x in st.db.execute("SELECT kind, payload FROM action_v12")]
    assert ("ADD_NEGATIVE_EXACT", "badam") not in rows, "a term that converted anywhere is NEVER made negative"
    assert ("HARVEST_TO_EXACT", "badam") in rows, "despite the cap, revenue-growing harvests are not crowded out by negatives"
    assert len(r["created"]) == GA.MAX_PER_RUN and r["capped"] > 0, "no flood in the inbox"
    st.close()

def test_disabled_rule_stops_proposals():
    import growth_autopilot as GA, agent_brain as AB
    st = Store(":memory:"); _seed(st)
    AB.seed_playbook(st.db)
    st.db.execute("UPDATE playbook_rules SET status='DISABLED' WHERE rule_id='AMZ-A-03'"); st.db.commit()
    r = GA.run(st, dry_run=True)
    kinds = [c["kind"] for c in r["created"]]
    assert all(c["ident"] != "SP | Kaju | AUTO|cashew cheap" for c in r["created"]), "AMZ-A-03 disabled = no waste negatives"
    assert any(s["ident"].endswith("cashew cheap") for s in r["skipped_disabled_rules"])
    assert "HARVEST_TO_EXACT" in kinds, "the other rules keep running"
    st.close()

def test_stockout_pause_only_when_campaign_names_sku():
    import growth_autopilot as GA
    st = Store(":memory:")
    st.set_inventory("SKU-PISTA", "Amazon FBA", 0, sellable=0)
    st.set_inventory("SKU-AKHROT", "Amazon FBA", 0, sellable=0)
    st.upsert_campaign("SP | SKU-PISTA | EXACT", "Amazon", 500, 1000)
    st.upsert_campaign("SP | Walnuts generic", "Amazon", 300, 600)
    r = GA.run(st, dry_run=True)
    pauses = [c for c in r["created"] if c["kind"] == "PAUSE_CAMPAIGN"]
    assert [p["ident"] for p in pauses] == ["SP | SKU-PISTA | EXACT|stockout"], "never pause the wrong campaign by guessing"
    st.close()

def test_full_learning_loop_from_autopilot():
    """Autopilot proposal -> VERIFIED outcome -> that rule's confidence changes in the brain."""
    import growth_autopilot as GA, agent_brain as AB
    st = Store(":memory:"); _seed(st); db = st.db
    AB.seed_playbook(db)
    before = db.execute("SELECT confidence FROM playbook_rules WHERE rule_id='AMZ-A-03'").fetchone()["confidence"]
    GA.run(st)
    aid = db.execute("SELECT id FROM action_v12 WHERE payload LIKE '%cashew cheap%'").fetchone()["id"]
    db.execute("INSERT INTO outcomes(action_id,kind,window_days,success,attribution,at,measured_at) VALUES (?,?,?,?,?,?,?)",
               (aid, "ADD_NEGATIVE_EXACT", 14, 1, "VERIFIED", now_utc(), now_utc())); db.commit()
    assert AB.learn_from_outcomes(db)["applied"] == 1
    after = db.execute("SELECT confidence, wins FROM playbook_rules WHERE rule_id='AMZ-A-03'").fetchone()
    assert after["wins"] == 1 and after["confidence"] > before, "an autopilot outcome strengthens the rule"
    st.close()

def test_weekly_report_and_scheduler():
    import growth_autopilot as GA, job_handlers as JH
    from scheduler import DAILY_JOBS
    jobs = [j["job"] for j in DAILY_JOBS]
    assert "growth_autopilot" in jobs and "weekly_report" in jobs
    assert jobs.index("measure_results") < jobs.index("growth_autopilot"), "measure outcomes first, then new proposals"
    st = Store(":memory:"); _seed(st)
    rep = GA.weekly_report(st, datetime.date(2026, 11, 15))
    md = rep["markdown"]
    for part in ("Weekly Growth Report", "Ads structure", "Agent Brain", "ESTIMATED"):
        assert part in md, part
    assert rep["saved_to"] is None, "no file for an in-memory DB"
    assert JH._weekly_report(st, datetime.date(2026, 11, 12)).startswith("SKIP"), "not on a Thursday"
    assert "Weekly report created" in JH._weekly_report(st, datetime.date(2026, 11, 15))
    msg = JH.build_handlers(st)["growth_autopilot"]()
    assert msg.startswith("Autopilot: 3 new")
    st.close()
    import tempfile
    d = tempfile.mkdtemp(); stf = Store(os.path.join(d, "g.db")); _seed(stf)
    r = GA.weekly_report(stf, datetime.date(2026, 11, 15))
    assert r["saved_to"].endswith("reports/weekly-2026-11-15.md") and os.path.exists(r["saved_to"])
    stf.close()

def test_today_mentions_autopilot_and_inbox_summary():
    import growth_playbook as GP
    st = Store(":memory:"); _seed(st)
    t = GP.today(st)
    assert any(x["area"] == "autopilot" for x in t["tasks"])
    st.close()
    app = open(os.path.join(os.path.dirname(__file__), "..", "backend", "app.py")).read()
    assert '"/api/v1/autopilot/run"' in app and '"/api/v1/autopilot/preview"' in app and '"/api/v1/reports/weekly"' in app
    assert 'd["summary"]' in app, "what & why in the inbox"
    html = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")).read()
    assert "runAutopilot" in html and "/api/v1/autopilot/preview" in html and "What & why" in html

if __name__ == "__main__":
    for t in [test_autopilot_creates_safe_proposals, test_converted_term_never_negated_and_cap,
              test_disabled_rule_stops_proposals, test_stockout_pause_only_when_campaign_names_sku,
              test_full_learning_loop_from_autopilot, test_weekly_report_and_scheduler,
              test_today_mentions_autopilot_and_inbox_summary]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V25 TESTS PASS")
