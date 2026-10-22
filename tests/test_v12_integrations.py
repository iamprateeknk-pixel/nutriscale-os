import sys, os, gzip, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store

def test_sp_lwa_only_no_aws():
    from connectors.config import missing_keys
    assert "aws_access_key" not in missing_keys("amazon_sp"), "V12 me AWS keys lazmi nahi honi chahiye"
    from connectors.amazon_sp import AmazonSP
    seen = {}
    def transport(req):
        seen.update(req)
        if "auth/o2/token" in req["url"]: return 200, {"access_token": "tok-1"}
        return 200, {"payload": {"Orders": [{"AmazonOrderId": "1"}], "NextToken": None}}
    cfg = {"client_id": "c", "client_secret": "s", "refresh_token": "r", "marketplace_id": "A21TJRUUN4KGV"}
    sp = AmazonSP(cfg=cfg, transport=transport)
    orders = sp.get_orders("2026-10-01T00:00:00Z")
    assert len(orders) == 1 and "x-amz-access-token" in seen["headers"]
    assert "Authorization" not in seen["headers"] or "AWS4" not in str(seen["headers"]), "SigV4 nahi hona chahiye"

def test_ads_reporting_pipeline():
    from connectors.amazon_ads import AmazonAds
    gz = gzip.compress(json.dumps([{"searchTerm": "brazil nuts", "campaignName": "brazil", "cost": 100,
                                    "sales14d": 250, "clicks": 10, "purchases14d": 2}]).encode())
    def transport(req):
        if "auth/o2/token" in req["url"]: return 200, {"access_token": "t"}
        if req["url"].endswith("/reporting/reports"): return 200, {"reportId": "R1"}
        if "/reporting/reports/R1" in req["url"]: return 200, {"status": "COMPLETED", "url": "https://x/y.gz"}
        return 200, {}
    def raw_transport(req): return 200, gz
    cfg = {"client_id": "c", "client_secret": "s", "refresh_token": "r", "profile_id": "123"}
    ads = AmazonAds(cfg=cfg, transport=transport)
    st = Store(":memory:")
    out = ads.sync_search_terms(st, "2026-10-01", "2026-10-07", raw_transport=raw_transport)
    assert out["imported"] == 1
    r = st.db.execute("SELECT spend, sales FROM search_terms WHERE term='brazil nuts'").fetchone()
    assert r["spend"] == 100 and r["sales"] == 250
    st.close()

def test_csv_wizard():
    from import_wizard import preview_import, commit_import
    path = "/tmp/wiz_orders.txt"
    with open(path, "w") as f:
        f.write("order-id\torder-item-id\tsku\titem-price\tquantity-purchased\n")
        f.write("222-9\tL1\tKAJU200\t279\t1\n")
    st = Store(":memory:")
    pv = preview_import(st.db, path)
    assert pv["kind"] == "orders" and pv["rows"] == 1 and not pv["duplicate"]
    c1 = commit_import(st, path)
    assert c1["ok"] and c1["imported"] == 1
    pv2 = preview_import(st.db, path); assert pv2["duplicate"]
    c2 = commit_import(st, path); assert c2["duplicate"]
    st.close()

def test_capabilities_and_intel():
    from capabilities import capability, all_capabilities, IntelProvider
    st = Store(":memory:")
    fk = capability(st.db, "Flipkart", "write_ads")
    assert fk["status"] == "unavailable", "Flipkart ads write fictional nahi hona chahiye"
    ip = IntelProvider()
    v = ip.keyword_volume("kaju 1kg")
    assert v["status"] == "UNAVAILABLE" and v["volume"] is None, "provider bina volume kabhi invent nahi"
    rk = ip.reverse_keywords("B0XXXX")
    assert rk["status"] == "UNAVAILABLE" and rk["keywords"] == []
    assert len(all_capabilities(st.db)) >= 8
    st.close()

if __name__ == "__main__":
    for t in [test_sp_lwa_only_no_aws, test_ads_reporting_pipeline, test_csv_wizard, test_capabilities_and_intel]:
        t(); print("PASS", t.__name__)
    print("ALL V12 INTEGRATION TESTS PASS")
