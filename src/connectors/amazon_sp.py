"""Amazon SP-API Connector (India = EU region endpoint).
Asal kaam: LWA refresh-token se access token, SigV4 sign karke —
Orders, Listings/Catalog, FBA Inventory, Reports (sales/traffic), Finances.
Docs: https://developer-docs.amazon.com/sp-api/
"""
from urllib.parse import urlencode, urlparse
from .config import require
from .http_base import request_json
from .aws_sigv4 import sign_headers

ENDPOINT = "https://sellingpartnerapi-eu.amazon.com"   # IN/EU region
REGION = "eu-west-1"
LWA_URL = "https://api.amazon.com/auth/o2/token"

class AmazonSP:
    def __init__(self, cfg: dict = None, transport=None):
        self.cfg = cfg if cfg is not None else require("amazon_sp")
        self.transport = transport
        self._token = None

    def access_token(self) -> str:
        if self._token: return self._token
        r = request_json("POST", LWA_URL, form_body={
            "grant_type": "refresh_token", "refresh_token": self.cfg["refresh_token"],
            "client_id": self.cfg["client_id"], "client_secret": self.cfg["client_secret"]},
            transport=self.transport)
        self._token = r["access_token"]; return self._token

    def _get(self, path: str, params: dict = None) -> dict:
        query = urlencode(params or {})
        host = urlparse(ENDPOINT).hostname
        headers = sign_headers(host, path, query, REGION, "execute-api",
                               self.cfg["aws_access_key"], self.cfg["aws_secret_key"],
                               extra_headers={"x-amz-access-token": self.access_token()})
        url = ENDPOINT + path + (f"?{query}" if query else "")
        return request_json("GET", url, headers=headers, transport=self.transport)

    # --- asal endpoints ---
    def get_orders(self, created_after_iso: str) -> list:
        r = self._get("/orders/v0/orders", {"MarketplaceIds": self.cfg["marketplace_id"],
                                            "CreatedAfter": created_after_iso})
        return r.get("payload", {}).get("Orders", [])

    def search_catalog_items(self, keywords: str) -> list:
        r = self._get(f"/catalog/2022-04-01/items", {"marketplaceIds": self.cfg["marketplace_id"],
                                                     "keywords": keywords, "pageSize": 20})
        return r.get("items", [])

    def get_my_listings_report_skus(self) -> dict:
        return self._get("/listings/2021-08-01/items/" + self.cfg.get("seller_id", ""),
                         {"marketplaceIds": self.cfg["marketplace_id"]}) if self.cfg.get("seller_id") else {}

    def fba_inventory(self) -> list:
        r = self._get("/fba/inventory/v1/summaries", {"marketplaceIds": self.cfg["marketplace_id"],
                                                      "granularityType": "Marketplace",
                                                      "granularityId": self.cfg["marketplace_id"]})
        return r.get("payload", {}).get("inventorySummaries", [])

    def create_report(self, report_type: str, start_iso: str, end_iso: str) -> str:
        # Reports API v2021-06-30 — POST hai; signing ke saath
        import json as _json
        from urllib.parse import urlparse as _up
        body = _json.dumps({"reportType": report_type, "marketplaceIds": [self.cfg["marketplace_id"]],
                            "dataStartTime": start_iso, "dataEndTime": end_iso}).encode()
        host = _up(ENDPOINT).hostname
        headers = sign_headers(host, "/reports/2021-06-30/reports", "", REGION, "execute-api",
                               self.cfg["aws_access_key"], self.cfg["aws_secret_key"],
                               extra_headers={"x-amz-access-token": self.access_token(),
                                              "content-type": "application/json"}, method="POST", payload=body)
        # body ko transport tak pahunchana
        def t(req):
            req = dict(req); req["body_bytes"] = body
            from .http_base import _urllib_transport
            return (self.transport or _urllib_transport)(req)
        r = request_json("POST", ENDPOINT + "/reports/2021-06-30/reports", headers=headers, transport=t)
        return r.get("reportId", "")
