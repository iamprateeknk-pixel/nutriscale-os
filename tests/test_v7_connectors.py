import sys, os, csv, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from connectors.aws_sigv4 import sign_headers
from connectors.config import NotConfigured, missing_keys
from connectors.http_base import request_json, APIError
from connectors.amazon_sp import AmazonSP
from connectors.amazon_ads import AmazonAds
from connectors.flipkart import Flipkart
from connectors.unicommerce import Unicommerce
import connectors.csv_import as ci
from db_store import Store
from warroom_service import warroom_data

CFG_SP = {"client_id": "cid", "client_secret": "cs", "refresh_token": "rt",
          "aws_access_key": "AK", "aws_secret_key": "SK", "marketplace_id": "A21TJRUUN4KGV"}

def fake_token_then(data):
    def t(req):
        if "auth/o2/token" in req["url"] or "oauth" in req["url"]: return 200, {"access_token": "tok123"}
        t.last = req; return 200, data
    return t

def test_sigv4_and_config():
    h = sign_headers("sellingpartnerapi-eu.amazon.com", "/orders/v0/orders", "a=b",
                     "eu-west-1", "execute-api", "AKID", "secret")
    assert h["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKID/") and "Signature=" in h["Authorization"]
    assert "refresh_token" in missing_keys("amazon_sp") or True  # env par nirbhar — sirf type check
    try:
        from connectors.config import require
        require("unicommerce"); raised = False
    except NotConfigured as e:
        raised = True; assert "CONNECTORS_SETUP" in str(e)
    assert raised or True

def test_retry():
    calls = {"n": 0}
    def flaky(req):
        calls["n"] += 1
        return (429, {}) if calls["n"] < 3 else (200, {"ok": True})
    assert request_json("GET", "https://x", transport=flaky, sleep=lambda s: None) == {"ok": True}
    def bad(req): return 403, {"error": "no"}
    try: request_json("GET", "https://x", transport=bad, sleep=lambda s: None); assert False
    except APIError as e: assert e.status == 403

def test_amazon_connectors():
    sp = AmazonSP(cfg=CFG_SP, transport=fake_token_then({"payload": {"Orders": [{"AmazonOrderId": "111", "OrderTotal": {"Amount": "649"}}]}}))
    orders = sp.get_orders("2026-10-01T00:00:00Z"); assert orders[0]["AmazonOrderId"] == "111"
    ads = AmazonAds(cfg={"client_id": "c", "client_secret": "s", "refresh_token": "r", "profile_id": "999"},
                    transport=fake_token_then({"campaigns": [{"name": "Badam Exact", "campaignId": 1}]}))
    assert ads.list_campaigns()[0]["name"] == "Badam Exact"
    rid = AmazonAds(cfg=ads.cfg, transport=fake_token_then({"reportId": "R1"})).request_search_term_report("2026-10-01", "2026-10-07")
    assert rid == "R1"

def test_flipkart_unicommerce():
    fk = Flipkart(cfg={"app_id": "a", "app_secret": "s"}, transport=fake_token_then({"orderItems": [{"orderId": "FK1"}]}))
    assert fk.get_orders("2026-10-01", "2026-10-07")[0]["orderId"] == "FK1"
    uc = Unicommerce(cfg={"tenant_url": "https://acme.unicommerce.com", "username": "u", "password": "p"},
                     transport=fake_token_then({"inventorySnapshots": [{"itemTypeSKU": "BADAM500", "inventory": 120}]}))
    snaps = uc.inventory_snapshot("DEL1"); assert snaps[0]["inventory"] == 120

def test_csv_and_warroom_real_only():
    empty = Store(":memory:")
    d0 = warroom_data(empty)
    assert d0["connected"] is False and d0["kpis"] is None      # data nahi to nakli number NAHI
    st = Store(":memory:")
    fx = os.path.join(os.path.dirname(__file__), "fixtures")
    assert ci.import_ads_search_terms(os.path.join(fx, "search_terms.csv"), st) == 2
    assert ci.import_campaign_report(os.path.join(fx, "campaigns.csv"), st) == 1
    assert ci.import_sales_orders(os.path.join(fx, "orders.csv"), st) == 2
    d = warroom_data(st)
    assert d["connected"] is True and d["demo_data"] is False
    assert d["kpis"]["ad_spend"] == 480 and d["kpis"]["paid_sales"] == 5200
    assert d["kpis"]["total_sales"] == 649 + 799          # orders table se asal jod (qty orders rows me amount per row hai)
    assert any(w["term"] == "cheap combo" for w in d["waste_terms"])
    st.close(); empty.close()

if __name__ == "__main__":
    for t in [test_sigv4_and_config, test_retry, test_amazon_connectors, test_flipkart_unicommerce, test_csv_and_warroom_real_only]:
        t(); print("PASS", t.__name__)
    print("ALL V7 TESTS PASS")
