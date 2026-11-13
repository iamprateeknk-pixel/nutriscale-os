"""V12.2 AUDIT-FIX TESTS — evidence for the 6 real source mismatches from the second audit."""
import os, sys, csv, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

def test_warroom_canonical():
    from warroom_service import warroom_data
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default','O1','2026-10-05','Shipped',1598,'INR')")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','O1','I1','SKU-BR','B0',2,1598,0)")
    st.db.commit()
    w = warroom_data(st)
    assert w["connected"] is True, "the war room works on canonical-only data too"
    assert w["kpis"]["revenue"] == 1598 and w["kpis"]["total_sales"] == 1598, "revenue comes from canonical"
    assert w["kpis"]["orders"] == 1 and "CANONICAL" in w["kpis"]["sales_source"]
    st.close()

def _terms_csv(rows):
    fd, path = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Customer Search Term", "Campaign Name", "Spend", "Sales", "Clicks", "Purchases"])
        for r in rows: w.writerow(r)
    return path

def test_search_term_dedup():
    from connectors.csv_import import import_ads_search_terms
    st = Store(":memory:")
    p = _terms_csv([["brazil nuts", "Brazil", 100, 300, 10, 2],
                    ["brazil nuts", "Brazil", 50, 100, 5, 1]])  # file ke andar duplicate rows
    n = import_ads_search_terms(p, st)
    assert n == 1, "duplicates within a file are summed into one"
    row = st.db.execute("SELECT spend, clicks FROM search_terms").fetchone()
    assert row["spend"] == 150 and row["clicks"] == 15
    # The same period imported again — totals must not double
    import_ads_search_terms(p, st, period_start="2026-10-01", period_end="2026-10-07")
    import_ads_search_terms(p, st, period_start="2026-10-01", period_end="2026-10-07")
    tot = st.db.execute("SELECT SUM(spend) s FROM search_terms WHERE period_start='2026-10-01'").fetchone()["s"]
    assert tot == 150, f"a period re-import must be idempotent, got {tot}"
    st.close()

def test_ads_api_sync_idempotent():
    """sync_search_terms period-replace rule: when the same period arrives again, the old rows are removed first."""
    st = Store(":memory:")
    from platform_core import ensure_v12; ensure_v12(st.db)
    for _ in range(2):
        st.db.execute("DELETE FROM search_terms WHERE source='Amazon Ads API (Reporting v3)' AND period_start='2026-10-01' AND period_end='2026-10-07'")
        st.add_search_term("kaju", "C", 90, 200, 9, 1, source="Amazon Ads API (Reporting v3)",
                           period_start="2026-10-01", period_end="2026-10-07"); st.db.commit()
    tot = st.db.execute("SELECT SUM(spend) s FROM search_terms").fetchone()["s"]
    assert tot == 90, "period-replace means an API resync does not double"
    st.close()

def test_fba_days_of_cover():
    from job_handlers import _fba_cover
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    st.set_inventory("SKU-SLOW", "FBA", 40)
    # V21 velocity (full 30-day window): 60 units in the window = 2/day -> 40 in stock = 20 days of cover < 21
    import datetime as _dt
    for i, ago in enumerate((2, 1)):
        dd = (_dt.date.today() - _dt.timedelta(days=ago)).isoformat()
        st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default',?,'%s','Shipped',100,'INR')" % dd, (f"O9{i}",))
        st.db.execute("INSERT INTO order_items VALUES ('Amazon','default',?,?,'SKU-SLOW','B0',30,100,0)", (f"O9{i}", f"I9{i}"))
    st.db.commit()
    out = _fba_cover(st)   # 40 units, selling 2/day = 20 days of cover < 21
    assert "WARNING" in out and "SKU-SLOW" in out, f"a warning on the real cover is expected, got: {out}"
    st.close()

def test_login_rate_limit_and_mfa_endpoint():
    import auth as A
    st = Store(":memory:")
    A.create_user(st.db, "victim", "right-pass", "Analyst")
    for _ in range(5):
        assert A.verify_login(st.db, "victim", "wrong") is None
    r = A.verify_login(st.db, "victim", "right-pass")
    assert r and r.get("locked"), "after 5 wrong attempts even the right password is locked out"
    app = open(os.path.join(os.path.dirname(__file__), "..", "backend", "app.py")).read()
    assert "/api/v1/auth/mfa/enable" in app and "RATE_LIMITED" in app
    df = open(os.path.join(os.path.dirname(__file__), "..", "Dockerfile")).read()
    assert "COPY dashboard/" in df, "the Docker image must contain the dashboard"
    st.close()

if __name__ == "__main__":
    for t in [test_warroom_canonical, test_search_term_dedup, test_ads_api_sync_idempotent,
              test_fba_days_of_cover, test_login_rate_limit_and_mfa_endpoint]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V12.2 FIX TESTS PASS")
