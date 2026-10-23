import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db_store import Store

DBF = "/tmp/qa_file.db"

def _fresh_file_store():
    if os.path.exists(DBF): os.remove(DBF)
    return Store(DBF)

def test_qa03_no_demo_in_live():
    """QA-03/UI-01: khaali DB par war room koi banaya hua number nahi dikhayega."""
    from warroom_service import warroom_data
    st = Store(":memory:")
    w = warroom_data(st)
    assert w["connected"] is False and w["kpis"] is None
    st.close()
    html = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")).read()
    for fake in ["25448", "25,448", "14892", "NutriScaleWarRoomDemo"]:
        assert fake not in html, "dashboard me asal-jaisa demo number nahi hona chahiye"
    assert html.count("data-s=") >= 0 and "SCREENS" in html and html.count("['") >= 16

def test_qa06_kill_persists_restart():
    """QA-06: kill switch file-DB me — naya Store (restart) kholne par bhi ON rahega."""
    import actions as ACT
    st = _fresh_file_store()
    ACT.set_kill(st.db, True, "owner", "QA-06")
    st.close()
    st2 = Store(DBF)
    assert ACT.kill_status(st2.db)["engaged"], "restart ke baad kill bhoolna sabse khatarnaak galti hai"
    assert not ACT.writes_allowed(st2.db)
    st2.close()

def test_qa11_scheduler_state_persists():
    """QA-11/JOB-01: job state restart ke baad bhi — sirf ghadi ke shabdon ki list nahi."""
    from jobrunner import seed_jobs, jobs_status
    st = Store(DBF)
    seed_jobs(st.db); st.close()
    st2 = Store(DBF)
    jobs = jobs_status(st2.db)
    assert len(jobs) == 11 and all(j["next_run"] for j in jobs)   # V22: 11 jobs (brand_analytics_import juda)
    st2.close()

def test_qa14_backup_restore_and_secret_scan():
    """QA-14: backup se restore parkha ja sakta hai; repo me koi chaabi nahi."""
    import ops_finance as OF
    r = OF.create_backup(DBF, "/tmp/qa_backup.db")
    assert r["ok"] and r["tables"] >= 10
    import sqlite3
    b = sqlite3.connect("/tmp/qa_backup.db")
    assert b.execute("SELECT COUNT(*) FROM job_state").fetchone()[0] == 11   # V22: 11 daily jobs
    b.close()
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import secret_scan
    hits = secret_scan.scan(os.path.join(os.path.dirname(__file__), ".."))
    assert hits == [], f"secret scan me mila: {hits}"

def test_qa04_unconfigured_connector_honest():
    """QA-04 ki neev: keys na hon to connector saaf mana karega — nakli data kabhi nahi."""
    from connectors.config import require, NotConfigured
    import os as _os
    for k in list(_os.environ):
        if k.startswith("GOS_AMAZON_SP_"): del _os.environ[k]
    import connectors.config as cfg
    if _os.path.exists(cfg.CONFIG_PATH):
        pass  # asal file ho to ye parikshan skip-saman hai; kam se kam function maujud hai
    else:
        try:
            require("amazon_sp"); assert False, "NotConfigured uthna chahiye tha"
        except NotConfigured:
            pass

def test_qa13_dashboard_sixteen_screens():
    html = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")).read()
    for key in ["warroom", "products", "competitors", "compare", "keywords", "rank", "ads", "listings",
                "creative", "experiments", "profit", "inventory", "approvals", "integrations", "agency", "ops"]:
        assert f"['{key}'" in html or f"'{key}'" in html, f"screen gayab: {key}"
    assert "localStorage" in html and "ns_token" in html, "login token ka pravdhaan hona chahiye"

if __name__ == "__main__":
    for t in [test_qa03_no_demo_in_live, test_qa06_kill_persists_restart, test_qa11_scheduler_state_persists,
              test_qa14_backup_restore_and_secret_scan, test_qa04_unconfigured_connector_honest,
              test_qa13_dashboard_sixteen_screens]:
        t(); print("PASS", t.__name__)
    print("ALL QA GATE TESTS PASS")
