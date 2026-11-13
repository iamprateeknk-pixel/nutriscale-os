"""Amazon SP-API Connector — V12/INT-01 modernized.
Amazon's new rules: new apps do NOT need AWS SigV4 signing — only an LWA access token.
Orders API: the full list via pagination (nextToken); version comes from config (GOS_SP_ORDERS_VERSION,
default 'v0', today's verified path; a new version changes config, not code).
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

    # --- real endpoints ---
    def get_orders(self, created_after_iso: str, max_pages: int = 20) -> list:
        """All pages combined — calculations on a partial list are wrong (INT-01 acceptance)."""
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
        """Finances API: real order fees down to SKU level (V13 — the path to SKU-exact fees).
        V20: every financial EVENT is its own row (with event_id + type + posted date) —
        several shipment events for the same order+SKU no longer overwrite each other;
        a refund gets its own REFUND event instead of being squeezed into the shipment row.
        Finances v0 has no stable event id, so event_id is derived from the content (deterministic)
        — the same event synced again keeps the same identity, so it is never double-counted."""
        import hashlib
        r = self._get(f"/finances/v0/orders/{order_id}/financialEvents")
        events = (r.get("payload") or {}).get("FinancialEvents", {})
        raw = []
        for ev in events.get("ShipmentEventList", []):
            posted = str(ev.get("PostedDate", "") or "")
            for it in ev.get("ShipmentItemList", []):
                fees = 0.0
                for f in it.get("ItemFeeList", []):
                    fees += float((f.get("FeeAmount") or {}).get("CurrencyAmount", 0) or 0)
                gross = 0.0
                for c in it.get("ItemChargeList", []):
                    if c.get("ChargeType") == "Principal":
                        gross += float((c.get("ChargeAmount") or {}).get("CurrencyAmount", 0) or 0)
                raw.append({"order_id": order_id, "sku": it.get("SellerSKU", ""), "event_type": "SHIPMENT",
                            "posted_at": posted, "gross": gross, "fees": abs(fees), "refund": 0.0})
        for ev in events.get("RefundEventList", []):
            posted = str(ev.get("PostedDate", "") or "")
            for it in ev.get("ShipmentItemAdjustmentList", []):
                amt = 0.0
                for c in it.get("ItemChargeList", []):
                    if c.get("ChargeType") == "Principal":
                        amt += float((c.get("ChargeAmount") or {}).get("CurrencyAmount", 0) or 0)
                if not amt: continue
                raw.append({"order_id": order_id, "sku": it.get("SellerSKU", ""), "event_type": "REFUND",
                            "posted_at": posted, "gross": 0.0, "fees": 0.0, "refund": abs(amt)})
        # V21: event ids NO LONGER depend on the RESPONSE ORDER — rows are first sorted into a fixed order,
        # then counting happens only within each group of FULLY IDENTICAL rows. If the API sends events
        # in a different order the ids stay the same; adding a new distinct event never changes old ids
        # (regression tests cover partial/reordered responses for duplicates/misses).
        raw.sort(key=lambda x: (x["event_type"], x["posted_at"], x["sku"], x["gross"], x["fees"], x["refund"]))
        seen = {}
        for row in raw:
            key = (row["event_type"], row["posted_at"], row["sku"], row["gross"], row["fees"], row["refund"])
            seen[key] = seen.get(key, 0) + 1
            basis = "|".join([order_id, row["event_type"], row["posted_at"], row["sku"],
                              f"{row['gross']:.2f}", f"{row['fees']:.2f}", f"{row['refund']:.2f}", str(seen[key])])
            row["event_id"] = "spfin:" + hashlib.sha1(basis.encode()).hexdigest()[:24]
        return raw

    def get_order_refunds(self, order_id: str) -> list:
        """Finances RefundEventList: how much was refunded on which SKU/line (V15 — reconciliation).
        V21: every refund adjustment is its own EVENT row (stable event_id + posted date) —
        record_refunds adds them into the ledger; partial refunds no longer erase each other.
        Refund charges arrive as negative Principal amounts; we return positive amounts."""
        import hashlib
        r = self._get(f"/finances/v0/orders/{order_id}/financialEvents")
        events = (r.get("payload") or {}).get("FinancialEvents", {})
        out = []
        for ev in events.get("RefundEventList", []):
            posted = str(ev.get("PostedDate", "") or "")
            for it in ev.get("ShipmentItemAdjustmentList", []):
                amt = 0.0
                for c in it.get("ItemChargeList", []):
                    if c.get("ChargeType") == "Principal":
                        amt += float((c.get("ChargeAmount") or {}).get("CurrencyAmount", 0) or 0)
                if amt: out.append({"order_id": order_id, "sku": it.get("SellerSKU", ""),
                                    "line_id": it.get("OrderItemId") or "", "refund": abs(amt),
                                    "posted_at": posted})
        out.sort(key=lambda x: (x["posted_at"], x["sku"], x["line_id"], x["refund"]))
        seen = {}
        for row in out:
            key = (row["posted_at"], row["sku"], row["line_id"], row["refund"])
            seen[key] = seen.get(key, 0) + 1
            basis = "|".join([order_id, "REFUND", row["posted_at"], row["sku"], row["line_id"],
                              f"{row['refund']:.2f}", str(seen[key])])
            row["event_id"] = "spref:" + hashlib.sha1(basis.encode()).hexdigest()[:24]
        return out

    def put_listing(self, sku: str, product_type: str, attributes: dict, mode: str = "VALIDATION_PREVIEW") -> dict:
        """Listings Items API (2021-08-01): listing publish/update. Only runs with a certified capability.
        With mode=VALIDATION_PREVIEW Amazon only validates and does not publish — a safe first step for a pilot."""
        seller = self.cfg.get("seller_id")
        if not seller:
            raise ValueError("seller_id is missing in the amazon_sp config — the Listings API cannot run without it")
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
