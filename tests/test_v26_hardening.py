"""V26 TESTS — dashboard se upload, import path suraksha (koi bhi server file nahi), purane ads data par
autopilot ka rukna, proposal expiry, asal HTTP par upload->preview->commit."""
import os, sys, json, base64, datetime, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
from platform_core import now_utc

FIX = os.path.join(os.path.dirname(__file__), "fixtures")

def test_upload_and_path_safety():
    import import_wizard as IW
    d = tempfile.mkdtemp(); dbp = os.path.join(d, "g.db")
    raw = open(os.path.join(FIX, "search_terms.csv"), "rb").read()
    up = IW.save_upload(dbp, "../../etc/My Report!.csv", base64.b64encode(raw).decode())
    assert up["ok"] and up["upload"].endswith("-My_Report_.csv") and "/" not in up["upload"], "naam saaf, folder se bahar nahi"
    assert os.path.dirname(up["path"]) == os.path.join(d, "uploads")
    assert IW.resolve_upload(dbp, up["upload"]) == up["path"]
    for bad in ("../g.db", "../../etc/passwd", "", "x/../../y.csv"):
        assert IW.resolve_upload(dbp, bad) is None, bad
    assert IW.allowed_path(dbp, up["path"])
    secret = os.path.join(tempfile.mkdtemp(), "owner.csv"); open(secret, "w").write("a,b\n1,2\n")
    assert not IW.allowed_path(dbp, secret), "data/ ke bahar ki file import nahi"
    assert not IW.allowed_path(dbp, "/etc/passwd")
    link = os.path.join(d, "uploads", "link.csv"); os.symlink(secret, link)
    assert not IW.allowed_path(dbp, link), "symlink se bahar jaana bhi band"
    assert not IW.save_upload(dbp, "report.xlsx", base64.b64encode(b"x").decode())["ok"], "sirf CSV/TSV"
    assert not IW.save_upload(dbp, "a.csv", "%%%not-b64")["ok"]
    assert not IW.save_upload(dbp, "a.csv", "")["ok"], "khaali file nahi"

def test_autopilot_stops_on_stale_ads_data():
    import growth_autopilot as GA, growth_playbook as GP
    st = Store(":memory:")
    old = (datetime.date.today() - datetime.timedelta(days=40)).isoformat()
    st.add_search_term("junk", "SP | X | AUTO", 900, 0, 50, 0, "", "b1", old, old)
    assert GA.ads_data_age(st.db) == 40
    r = GA.run(st)
    assert r["created"] == [] and r["skipped_stale_data"], "40 din purane data par negative nahi"
    assert any(t["area"] == "data" and t["priority"] == 1 for t in GP.today(st)["tasks"]), "Aaj screen par chetaavni"
    fresh = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    st.add_search_term("junk2", "SP | X | AUTO", 900, 0, 50, 0, "", "b2", fresh, fresh)
    r2 = GA.run(st)
    assert r2["created"] and r2["ads_data_age_days"] == 3
    p = json.loads(st.db.execute("SELECT payload FROM action_v12 LIMIT 1").fetchone()["payload"])
    assert p["data_freshness"] == "3 days old", "proposal par data ki umar likhi ho"
    st.close()
    st2 = Store(":memory:")
    st2.add_search_term("junk", "SP | X | AUTO", 900, 0, 50, 0)
    r3 = GA.run(st2)
    assert r3["ads_data_age_days"] is None and r3["created"], "bina-tareekh data: chalega, AGE_UNKNOWN label ke saath"
    assert json.loads(st2.db.execute("SELECT payload FROM action_v12").fetchone()["payload"])["data_freshness"] == "AGE_UNKNOWN"
    st2.close()

def test_proposal_expiry():
    import actions as ACT, growth_autopilot as GA
    st = Store(":memory:"); db = st.db
    r = ACT.create_proposal(db, "ADD_NEGATIVE_EXACT", "Amazon", "default", {"term": "x"}, "ONE_TAP", "t", "k1")
    db.execute("UPDATE action_v12 SET expires_at=? WHERE id=?", ("2000-01-01T00:00:00+00:00", r["id"])); db.commit()
    keep = ACT.create_proposal(db, "ADD_NEGATIVE_EXACT", "Amazon", "default", {"term": "y"}, "ONE_TAP", "t", "k2")
    e = ACT.expire_stale(db)
    assert e["expired"] == 1 and e["ids"] == [r["id"]]
    assert db.execute("SELECT state FROM action_v12 WHERE id=?", (r["id"],)).fetchone()["state"] == "EXPIRED"
    assert db.execute("SELECT state FROM action_v12 WHERE id=?", (keep["id"],)).fetchone()["state"] == "APPROVAL_PENDING"
    assert not ACT.approve(db, r["id"], {"username": "o", "role": "Owner"})["ok"], "expired approve nahi hota"
    assert any(x["to_state"] == "EXPIRED" for x in ACT.action_timeline(db, r["id"])), "itihaas bana rehta hai"
    assert GA.run(st, dry_run=True)["expired_old_proposals"] == 0, "dry run kuch nahi badalta"
    st.close()

def test_v26_http_upload_flow():
    import subprocess, time, urllib.request, urllib.error, socket
    with socket.socket() as so: so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]
    d = tempfile.mkdtemp(); dbf = os.path.join(d, "g.db")
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
            try: return 200, json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
            except urllib.error.HTTPError as e: return e.code, json.loads(e.read().decode() or "{}")
        _, lg = call("/api/v1/auth/login", {"username": "own", "password": "pw-123456"}); tok = lg["data"]["token"]
        raw = open(os.path.join(FIX, "search_terms.csv"), "rb").read()
        code, up = call("/api/v1/imports/upload", {"filename": "st.csv", "content_b64": base64.b64encode(raw).decode()}, tok)
        assert code == 200 and up["data"]["preview"]["kind"] == "search_terms", up
        code, cm = call("/api/v1/imports/commit", {"upload": up["data"]["upload"]}, tok)
        assert code == 200 and cm["data"]["ok"] and cm["data"]["imported"] >= 1
        code, again = call("/api/v1/imports/commit", {"upload": up["data"]["upload"]}, tok)
        assert again["data"]["duplicate"] is True, "wahi file dobara nahi"
        # hamle: server ki koi bhi file / folder se bahar ka naam
        assert call("/api/v1/imports/preview", {"path": "/etc/passwd"}, tok)[0] == 400
        assert call("/api/v1/imports/commit", {"upload": "../g.db"}, tok)[0] == 400
        assert call("/api/v1/imports/upload", {"filename": "x.exe", "content_b64": "eA=="}, tok)[0] == 400
        assert call("/api/v1/imports/upload", {"filename": "a.csv", "content_b64": "eA=="})[0] == 401, "bina login upload nahi"
    finally:
        p.terminate(); p.wait(5)

def test_dashboard_upload_widget():
    html = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")).read()
    assert "/api/v1/imports/upload" in html and 'type="file"' in html and "uploadFile" in html and "commitUpload" in html
    assert "Server par file ka poora path" not in html, "purana path-wala form hata"
    assert "skipped_stale_data" in html and "'EXPIRED'" in html

if __name__ == "__main__":
    for t in [test_upload_and_path_safety, test_autopilot_stops_on_stale_ads_data, test_proposal_expiry,
              test_v26_http_upload_flow, test_dashboard_upload_widget]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V26 TESTS PASS")
