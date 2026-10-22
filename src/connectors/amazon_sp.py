"""Amazon SP-API Connector — V12/INT-01 modernized.
Amazon ke naye niyam: naye apps ke liye AWS SigV4 signing NAHI chahiye — sirf LWA access token.
Orders API: pagination (nextToken) ke saath poori list; version config se (GOS_SP_ORDERS_VERSION,
default 'v0' jo aaj ka verified path hai; naya version aate hi config se badlega, code nahi).
Docs: https://developer-docs.amazon.com/sp-api/docs/orders-api
"""
import os
from urllib.parse import urlencode, urlparse
from .config import require
from .http_base import request_json

ENDPOINT = "https://sellingpartnerapi-eu.amazon.com"   # IN/EU region
LWA_URL = "https://api.amazon.com/auth/o2/token"
ORDERS_VERSION = os.environ.get("GOS_SP_ORDERS_VERSION", "v0")

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

    def _headers(self) -> dict:
        return {"x-amz-access-token": self.access_token(), "Content-Type": "application/json"}

    def _get(self, path: str, params: dict = None) -> dict:
        query = urlencode(params or {})
        url = ENDPOINT + path + (f"?{query}" if query else "")
        return request_json("GET", url, headers=self._headers(), transport=self.transport)

    def _post(self, path: str, body: dict) -> dict:
        return request_json("POST", ENDPOINT + path, headers=self._headers(),
                            json_body=body, transport=self.transport)

    # --- asal endpoints ---
    def get_orders(self, created_after_iso: str, max_pages: int = 20) -> list:
        """Saare pages jodkar — adhoori list par hisaab galat hota hai (INT-01 acceptance)."""
        orders, token = [], None
        for _ in range(max_pages):
            params = {"MarketplaceIds": self.cfg["marketplace_id"], "CreatedAfter": created_after_iso}
            if token: params["NextToken"] = token
            r = self._get(f"/orders/{ORDERS_VERSION}/orders", params)
            payload = r.get("payload", {})
            orders += payload.get("Orders", [])
            token = payload.get("NextToken")
            if not token: break
        return orders

    def get_order_items(self, order_id: str) -> list:
        r = self._get(f"/orders/{ORDERS_VERSION}/orders/{order_id}/orderItems")
        return r.get("payload", {}).get("OrderItems", [])

    def search_catalog_items(self, keywords: str) -> list:
        r = self._get("/catalog/2022-04-01/items", {"marketplaceIds": self.cfg["marketplace_id"],
                                                    "keywords": keywords, "pageSize": 20})
        return r.get("items", [])

    def fba_inventory(self) -> list:
        r = self._get("/fba/inventory/v1/summaries", {"marketplaceIds": self.cfg["marketplace_id"],
                                                     "granularityType": "Marketplace",
                                                     "granularityId": self.cfg["marketplace_id"]})
        return r.get("payload", {}).get("inventorySummaries", [])

    def create_report(self, report_type: str, start_iso: str, end_iso: str) -> str:
        r = self._post("/reports/2021-06-30/reports",
                       {"reportType": report_type, "marketplaceIds": [self.cfg["marketplace_id"]],
                        "dataStartTime": start_iso, "dataEndTime": end_iso})
        return r.get("reportId", "")

    def report_status(self, report_id: str) -> dict:
        return self._get(f"/reports/2021-06-30/reports/{report_id}")
