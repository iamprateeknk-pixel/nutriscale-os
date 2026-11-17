"""V27 TESTS — a report's age comes from its own dates (not the upload day), overlapping periods are
explained instead of silently importing 0 rows, and a cost sheet can be uploaded in one go (validated per row,
only Owner/GrowthLead may set costs)."""
import os, sys, json, base64, datetime, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

TODAY = datetime.date.today()

def _csv(lines, name="r.csv"):
    d = tempfile.mkdtemp(); p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
    return p

def _days_ago(n, fmt="%Y-%m-%d"): return (TODAY - datetime.timedelta(days=n)).strftime(fmt)

def test_detect_period_formats():
    import import_wizard as IW
    def per(header, vals):
        return IW.detect_period([{header: v} for v in vals], [header], today=datetime.date(2026, 11, 17))
    assert per("Date", ["2026-10-01", "2026-10-31"]) == {"start": "2026-10-01", "end": "2026-10-31", "age_days": 17,
                                                         "columns": ["Date"], "assumed_day_first": False}
    assert per("Date", ["25/10/2026", "03/11/2026"])["end"] == "2026-11-03", "a day > 12 means DD/MM"
    assert per("Date", ["10/25/2026", "11/03/2026"])["end"] == "2026-11-03", "a second part > 12 means MM/DD"
    amb = per("Date", ["03/11/2026"]); assert amb["end"] == "2026-11-03" and amb["assumed_day_first"], "ambiguous → DD/MM, and it says so"
    assert per("Start Date", ["Oct 01, 2026", "Nov 02, 2026"])["end"] == "2026-11-02"
    assert per("Date", ["01 Nov 2026", "02-Nov-2026"])["end"] == "2026-11-02", "day-month-name formats"
    assert per("purchase-date", ["2026-11-01T10:15:00+00:00", "01/11/2026 10:00"])["end"] == "2026-11-01", "time parts ignored"
    assert per("Date", ["", "n/a"]) == {}, "no usable dates → no period"
    assert per("Date", ["2030-01-01"]) == {}, "future dates are not trusted"
    assert IW.detect_period([{"Expiry date": "2027-01-01"}], ["Expiry date"]) == {}, "only known report-date columns count"

def test_old_report_is_old_even_if_uploaded_today():
    import import_wizard as IW, growth_autopilot as GA
    st = Store(":memory:")
    old = _csv(["Date,Customer Search Term,Campaign Name,Clicks,Spend,Sales,Purchases",
                f"{_days_ago(65)},mamra almonds,Mamra Exact,40,480,5200,8",
                f"{_days_ago(60)},cheap combo,Broad,60,900,0,0"])
    pv = IW.preview_import(st.db, old)
    assert pv["kind"] == "search_terms" and pv["period"]["age_days"] == 60
    r = IW.commit_import(st, old)
    assert r["ok"] and r["imported"] == 2 and "period" in r["how"]
    assert GA.ads_data_age(st.db) == 60, "age = report end date, not today's upload"
    run = GA.run(st, dry_run=True)
    assert run["skipped_stale_data"], "the autopilot pauses on a 60-day-old report"
    # a fresh report next to it is fine and makes the data fresh again
    new = _csv(["Date,Customer Search Term,Campaign Name,Clicks,Spend,Sales,Purchases",
                f"{_days_ago(6)},mamra almonds,Mamra Exact,30,300,4000,6",
                f"{_days_ago(2)},kaju w240,Kaju Exact,20,200,0,0"])
    assert IW.commit_import(st, new)["ok"] and GA.ads_data_age(st.db) == 2
    # an undated file still counts from the upload day (unchanged behaviour)
    st2 = Store(":memory:")
    und = _csv(["Customer Search Term,Campaign Name,Clicks,Spend,Sales,Purchases", "badam,Exact,1,10,0,0"])
    assert IW.commit_import(st2, und)["ok"] and GA.ads_data_age(st2.db) == 0
    st.close(); st2.close()

def test_overlapping_period_is_explained():
    import import_wizard as IW
    st = Store(":memory:")
    a = _csv(["Date,Customer Search Term,Campaign Name,Clicks,Spend,Sales,Purchases",
              f"{_days_ago(20)},badam,Exact,10,100,500,1", f"{_days_ago(10)},badam,Exact,10,100,500,1"])
    b = _csv(["Date,Customer Search Term,Campaign Name,Clicks,Spend,Sales,Purchases",
              f"{_days_ago(15)},kaju,Exact,5,50,0,0", f"{_days_ago(1)},kaju,Exact,5,50,0,0"])
    assert IW.commit_import(st, a)["imported"] == 1
    r = IW.commit_import(st, b)
    assert r["ok"] is False and r["period_status"] == "BLOCKED_PARTIAL_OVERLAP" and "Overlaps" in r["note"], r
    total = st.db.execute("SELECT SUM(spend) s FROM search_terms").fetchone()["s"]
    assert total == 200, "nothing from the overlapping file was added"
    st.close()

def test_cost_sheet_import():
    import import_wizard as IW, finance as F
    st = Store(":memory:")
    p = _csv(["sku,cogs,packaging,shipping,other,effective_from",
              "BRZ-250,310,12,18,,2026-11-01",
              "CRN-200,\"₹1,250.50\",10,,,",
              ",100,1,1,,",
              "BAD-1,abc,1,1,,",
              "BAD-2,0,1,1,,",
              "BAD-3,100,-5,1,,",
              "BAD-4,100,1,1,,yesterday"])
    pv = IW.preview_import(st.db, p)
    assert pv["kind"] == "costs", pv
    r = IW.commit_import(st, p, imported_by="owner1")
    assert r["ok"] and r["imported"] == 2 and len(r["exceptions"]) == 5, r
    assert {e["row"] for e in r["exceptions"]} == {4, 5, 6, 7, 8}
    c = F.get_cost(st.db, "BRZ-250")
    assert c["known"] and c["cogs"] == 310 and c["packaging"] == 12 and c["other_variable"] == 18 and c["effective_from"] == "2026-11-01"
    c2 = F.get_cost(st.db, "CRN-200")
    assert c2["known"] and c2["unit_cost"] == 1260.5, "₹ and thousands separators are understood"
    assert not F.get_cost(st.db, "BAD-1")["known"], "a bad row never becomes a cost"
    # an inventory file is still an inventory file
    inv = _csv(["sku,quantity", "BRZ-250,40"])
    assert IW.preview_import(st.db, inv)["kind"] == "inventory"
    # a sheet with no valid rows says so
    none = _csv(["sku,cost", "X,abc"])
    rr = IW.commit_import(st, none)
    assert rr["ok"] is False and rr["exceptions"], rr
    st.close()

def test_cost_sheet_needs_cost_permission_over_http():
    import subprocess, time, urllib.request, urllib.error, socket, auth
    with socket.socket() as so: so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]
    d = tempfile.mkdtemp(); dbf = os.path.join(d, "g.db")
    s0 = Store(dbf); auth.create_user(s0.db, "ops1", "ops-password-1", "Operations"); s0.close()
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
        sheet = base64.b64encode(b"sku,cogs,packaging\nBRZ-250,310,12\n").decode()
        _, lg = call("/api/v1/auth/login", {"username": "ops1", "password": "ops-password-1"}); ops = lg["data"]["token"]
        code, up = call("/api/v1/imports/upload", {"filename": "costs.csv", "content_b64": sheet}, ops)
        assert code == 200 and up["data"]["preview"]["kind"] == "costs"
        assert call("/api/v1/imports/commit", {"upload": up["data"]["upload"]}, ops)[0] == 403, "Operations may import reports, not set costs"
        assert call("/api/v1/imports/commit", {"upload": up["data"]["upload"], "kind": "costs"}, ops)[0] == 403
        _, lg = call("/api/v1/auth/login", {"username": "own", "password": "pw-123456"}); own = lg["data"]["token"]
        code, cm = call("/api/v1/imports/commit", {"upload": up["data"]["upload"]}, own)
        assert code == 200 and cm["data"]["ok"] and cm["data"]["imported"] == 1, cm
        code, costs = call("/api/v1/costs", tok=own)
        assert code == 200 and costs["data"]["costs"][0]["sku"] == "BRZ-250"
    finally:
        p.terminate(); p.wait(5)

if __name__ == "__main__":
    for t in [test_detect_period_formats, test_old_report_is_old_even_if_uploaded_today, test_overlapping_period_is_explained,
              test_cost_sheet_import, test_cost_sheet_needs_cost_permission_over_http]:
        t(); print("PASS", t.__name__)
    print("ALL V27 TESTS PASS")
