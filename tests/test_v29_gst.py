"""V29 TESTS — GST rate per SKU cost: output GST is taken out of the (GST-inclusive) selling price everywhere
profit is used (contribution, break-even ACOS, bids), validated in the form, the API and the cost sheet;
old databases and costs without a rate keep working and are clearly flagged."""
import os, sys, json, tempfile, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

def _csv(lines):
    d = tempfile.mkdtemp(); p = os.path.join(d, "costs.csv")
    with open(p, "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
    return p

def test_check_gst_rate():
    import finance as F
    assert F.check_gst_rate(None) is None and F.check_gst_rate("") is None and F.check_gst_rate("  ") is None
    assert F.check_gst_rate("5%") == 5.0 and F.check_gst_rate(18) == 18.0 and F.check_gst_rate("0") == 0.0
    for bad in ("41", -1, "abc", "5 percent"):
        try: F.check_gst_rate(bad); raise AssertionError(f"{bad!r} should be refused")
        except ValueError: pass

def test_gst_taken_out_of_profit():
    import finance as F, growth_playbook as GP
    st = Store(":memory:"); db = st.db
    F.set_cost(db, "NO-GST", 200, 10, 5)
    F.set_cost(db, "GST-5", 200, 10, 5, gst_rate=5)
    a = F.contribution_v2(db, "NO-GST", 525.0)
    b = F.contribution_v2(db, "GST-5", 525.0)
    assert a["gst_rate"] is None and a["gst_per_unit"] == 0 and "NOT taken out" in a["gst_basis"]
    assert b["gst_rate"] == 5 and b["gst_per_unit"] == 25.0, "₹525 incl. 5% GST holds ₹25 of GST"
    assert round(a["contribution"] - b["contribution"], 2) == 25.0, "the only difference is the GST"
    assert b["margin_pct"] < a["margin_pct"]
    db.execute("INSERT OR REPLACE INTO products VALUES ('GST-5','Test','Amazon',525,0,4.2,50,'t')"); db.commit()
    be = GP.break_even(db, "GST-5")
    assert be["status"] == "OK" and be["gst_per_unit"] == 25.0 and be["pre_ad_profit"] == b["contribution"]
    # a version dated in the future is not used yet, so today's rate stays 5%
    F.set_cost(db, "GST-5", 200, 10, 5, effective_from="2099-01-01")   # future version is not used yet
    assert F.get_cost(db, "GST-5")["gst_rate"] == 5
    st.close()

def test_old_database_gets_the_column():
    import finance as F
    d = tempfile.mkdtemp(); p = os.path.join(d, "old.db")
    st = Store(p); st.db.execute("DROP TABLE IF EXISTS cost_versions")
    st.db.execute("""CREATE TABLE cost_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT, effective_from TEXT, cogs REAL,
                     packaging REAL, other_variable REAL, source TEXT, approved_by TEXT, created_at TEXT)""")
    st.db.execute("INSERT INTO cost_versions(sku,effective_from,cogs,packaging,other_variable) VALUES ('OLD','2026-11-01',100,5,0)")
    st.db.commit()
    c = F.get_cost(st.db, "OLD")
    assert c["known"] and c["gst_rate"] is None, "an existing cost keeps working, with no rate"
    assert F.set_cost(st.db, "OLD", 100, 5, 0, gst_rate=12)["gst_rate"] == 12
    st.close()

def test_cost_sheet_gst_column():
    import import_wizard as IW, finance as F
    st = Store(":memory:")
    p = _csv(["sku,cogs,packaging,shipping,other,gst_rate,effective_from",
              "BRZ-250,310,12,18,,5%,",
              "CRN-200,180,10,,,12,",
              "NO-RATE,100,5,,,,",
              "BAD-GST,100,5,,,50,"])
    r = IW.commit_import(st, p, imported_by="owner1")
    assert r["ok"] and r["imported"] == 3, r
    assert r["exceptions"] == [{"row": 5, "sku": "BAD-GST", "error": "GST rate must be a number from 0 to 40 (got 50)"}]
    assert "1 SKU(s) without a GST rate" in r["how"]
    assert F.get_cost(st.db, "BRZ-250")["gst_rate"] == 5 and F.get_cost(st.db, "CRN-200")["gst_rate"] == 12
    assert F.get_cost(st.db, "NO-RATE")["gst_rate"] is None and not F.get_cost(st.db, "BAD-GST")["known"]
    st.close()

def test_gst_over_http():
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
        code, err = call("/api/v1/costs", {"sku": "X", "cogs": 100, "gst_rate": 50}, tok)
        assert code == 400 and err["error"] == "BAD_GST_RATE" and "between 0 and 40" in err["message"]
        assert call("/api/v1/costs", {"sku": "X", "cogs": 100, "packaging": 5, "gst_rate": 5}, tok)[0] == 200
        assert call("/api/v1/costs", {"sku": "Y", "cogs": 100, "gst_rate": None}, tok)[0] == 200, "GST is optional"
        _, costs = call("/api/v1/costs", tok=tok)
        rates = {c["sku"]: c["gst_rate"] for c in costs["data"]["costs"]}
        assert rates == {"X": 5, "Y": None}, rates
    finally:
        p.terminate(); p.wait(5)

if __name__ == "__main__":
    for t in [test_check_gst_rate, test_gst_taken_out_of_profit, test_old_database_gets_the_column,
              test_cost_sheet_gst_column, test_gst_over_http]:
        t(); print("PASS", t.__name__)
    print("ALL V29 TESTS PASS")
