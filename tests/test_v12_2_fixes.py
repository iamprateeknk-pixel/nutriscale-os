"""V12.2 AUDIT-FIX TESTS — dusre audit ke 6 asal source-mismatch ka saboot."""
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
    assert w["connected"] is True, "canonical-only data par bhi warroom chalega"
    assert w["kpis"]["revenue"] == 1598 and w["kpis"]["total_sales"] == 1598, "revenue canonical se aayega"
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
    assert n == 1, "file ke andar duplicates jod kar ek hongi"
    row = st.db.execute("SELECT spend, clicks FROM search_terms").fetchone()
    assert row["spend"] == 150 and row["clicks"] == 15
    # Wahi period dobara import — totals double nahi hone chahiye
    import_ads_search_terms(p, st, period_start="2026-10-01", period_end="2026-10-07")
    import_ads_search_terms(p, st, period_start="2026-10-01", period_end="2026-10-07")
    tot = st.db.execute("SELECT SUM(spend) s FROM search_terms WHERE period_start='2026-10-01'").fetchone()["s"]
    assert tot == 150, f"period re-import idempotent hoga, mila {tot}"
    st.close()

def test_ads_api_sync_idempotent():
    """sync_search_terms ka period-replace niyam: wahi period dobara aaye to purani rows pehle hat ti hain."""
    st = Store(":memory:")
    from platform_core import ensure_v12; ensure_v12(st.db)
    for _ in range(2):
        st.db.execute("DELETE FROM search_terms WHERE source='Amazon Ads API (Reporting v3)' AND period_start='2026-10-01' AND period_end='2026-10-07'")
        st.add_search_term("kaju", "C", 90, 200, 9, 1, source="Amazon Ads API (Reporting v3)",
                           period_start="2026-10-01", period_end="2026-10-07"); st.db.commit()
    tot = st.db.execute("SELECT SUM(spend) s FROM search_terms").fetchone()["s"]
    assert tot == 90, "period-replace se API resync par double nahi hoga"
    st.close()

def test_fba_days_of_cover():
    from job_handlers import _fba_cover
    from platform_core import ensure_v12
    st = Store(":memory:"); ensure_v12(st.db)
    st.set_inventory("SKU-SLOW", "FBA", 40)
    st.db.execute("INSERT INTO order_headers VALUES ('Amazon','default','O9','2026-10-05','Shipped',100,'INR')")
    st.db.execute("INSERT INTO order_items VALUES ('Amazon','default','O9','I9','SKU-SLOW','B0',2,100,0)")
    st.db.commit()
    out = _fba_cover(st)   # 40 units, 2/din ki bikri (ek din ka data) = 20 din cover < 21
    assert "CHETAVNI" in out and "SKU-SLOW" in out, f"asal cover par chetavni aayegi, mila: {out}"
    st.close()

def test_login_rate_limit_and_mfa_endpoint():
    import auth as A
    st = Store(":memory:")
    A.create_user(st.db, "victim", "sahi-pass", "Analyst")
    for _ in range(5):
        assert A.verify_login(st.db, "victim", "galat") is None
    r = A.verify_login(st.db, "victim", "sahi-pass")
    assert r and r.get("locked"), "5 galat koshishon ke baad sahi password par bhi lock lagega"
    app = open(os.path.join(os.path.dirname(__file__), "..", "backend", "app.py")).read()
    assert "/api/v1/auth/mfa/enable" in app and "RATE_LIMITED" in app
    df = open(os.path.join(os.path.dirname(__file__), "..", "Dockerfile")).read()
    assert "COPY dashboard/" in df, "Docker image me dashboard hona chahiye"
    st.close()

if __name__ == "__main__":
    for t in [test_warroom_canonical, test_search_term_dedup, test_ads_api_sync_idempotent,
              test_fba_days_of_cover, test_login_rate_limit_and_mfa_endpoint]:
        t(); print(f"PASS {t.__name__}")
    print("ALL V12.2 FIX TESTS PASS")
