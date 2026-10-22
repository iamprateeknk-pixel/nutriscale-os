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

    def get_order_financials(self, order_id: str) -> list:
        """Finances API: order ki asal fees SKU tak (V13 — SKU-exact fees ka rasta).
        Har shipment item se: sku, gross (ItemPrice), fees (ItemFeeList ka yog, rinatmak)."""
        r = self._get(f"/finances/v0/orders/{order_id}/financialEvents")
        events = (r.get("payload") or {}).get("FinancialEvents", {})
        out = []
        for ev in events.get("ShipmentEventList", []):
            for it in ev.get("ShipmentItemList", []):
                fees = 0.0
                for f in it.get("ItemFeeList", []):
                    fees += float((f.get("FeeAmount") or {}).get("CurrencyAmount", 0) or 0)
                gross = 0.0
                for c in it.get("ItemChargeList", []):
                    if c.get("ChargeType") == "Principal":
                        gross += float((c.get("ChargeAmount") or {}).get("CurrencyAmount", 0) or 0)
                out.append({"order_id": order_id, "sku": it.get("SellerSKU", ""),
                            "gross": gross, "fees": abs(fees), "refund": 0.0})
        # V19: usi order ke refunds bhi SKU-war isi record me — milaan gross/refund alag-alag hoga
        for ev in events.get("RefundEventList", []):
            for it in ev.get("ShipmentItemAdjustmentList", []):
                amt = 0.0
                for c in it.get("ItemChargeList", []):
                    if c.get("ChargeType") == "Principal":
                        amt += float((c.get("ChargeAmount") or {}).get("CurrencyAmount", 0) or 0)
                if not amt: continue
                row = next((x for x in out if x["sku"] == it.get("SellerSKU", "")), None)
                if row: row["refund"] += abs(amt)
                else: out.append({"order_id": order_id, "sku": it.get("SellerSKU", ""),
                                  "gross": 0.0, "fees": 0.0, "refund": abs(amt)})
        return out

    def get_order_refunds(self, order_id: str) -> list:
        """Finances RefundEventList: kis SKU par kitna refund gaya (V15 — reconciliation).
        Refund charges rinatmak Principal ke roop me aate hain; hum sakaratmak rakam lautate hain."""
        r = self._get(f"/finances/v0/orders/{order_id}/financialEvents")
        events = (r.get("payload") or {}).get("FinancialEvents", {})
        out = []
        for ev in events.get("RefundEventList", []):
            for it in ev.get("ShipmentItemAdjustmentList", []):
                amt = 0.0
                for c in it.get("ItemChargeList", []):
                    if c.get("ChargeType") == "Principal":
                        amt += float((c.get("ChargeAmount") or {}).get("CurrencyAmount", 0) or 0)
                if amt: out.append({"order_id": order_id, "sku": it.get("SellerSKU", ""),
                                    "line_id": it.get("OrderItemId") or "", "refund": abs(amt)})
        return out

    def put_listing(self, sku: str, product_type: str, attributes: dict, mode: str = "VALIDATION_PREVIEW") -> dict:
        """Listings Items API (2021-08-01): listing publish/update. Sirf certified capability par chalega.
        mode=VALIDATION_PREVIEW par Amazon sirf parkhega, live nahi karega — pilot ke liye surakshit pehla kadam."""
        seller = self.cfg.get("seller_id")
        if not seller:
            raise ValueError("amazon_sp config me seller_id baki hai — bina iske Listings API nahi chalegi")
        body = {"productType": product_type, "mode": mode, "attributes": attributes}
        url = ENDPOINT + f"/listings/2021-08-01/items/{seller}/{sku}"
        return request_json("PUT", url + f"?marketplaceIds={self.cfg['marketplace_id']}",
                            headers=self._headers(), json_body=body, transport=self.transport)

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
