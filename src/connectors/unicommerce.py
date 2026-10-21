"""Unicommerce (Uniware) API Connector — A13/F2 ka asal data yahi se aayega.
REST APIs: token (username/password), Sale Orders, Inventory Snapshot, Facilities, Returns.
Tenant URL har seller ka apna hota hai (https://<tenant>.unicommerce.com).
Docs: https://docs.unicommerce.com/
"""
from .config import require
from .http_base import request_json

class Unicommerce:
    def __init__(self, cfg: dict = None, transport=None):
        self.cfg = cfg if cfg is not None else require("unicommerce")
        self.base = self.cfg["tenant_url"].rstrip("/")
        self.transport = transport; self._token = None

    def access_token(self) -> str:
        if self._token: return self._token
        r = request_json("POST", self.base + "/oauth/token",
                         form_body={"username": self.cfg["username"], "password": self.cfg["password"],
                                    "grant_type": "password"}, transport=self.transport)
        self._token = r["access_token"]; return self._token

    def _post(self, path: str, body: dict) -> dict:
        return request_json("POST", self.base + path,
                            headers={"Authorization": f"Bearer {self.access_token()}"},
                            json_body=body, transport=self.transport)

    def search_sale_orders(self, from_date: str, to_date: str) -> list:
        r = self._post("/services/rest/v1/oms/saleorder/search",
                       {"fromDate": from_date, "toDate": to_date, "dateType": "CREATED"})
        return r.get("elements", [])

    def inventory_snapshot(self, facility_code: str) -> list:
        """Ek facility ka pura stock — 3-way reconciliation ka 'sach' yahi hai."""
        r = self._post("/services/rest/v1/inventory/inventorySnapshot/get",
                       {"facilityCode": facility_code})
        return r.get("inventorySnapshots", [])

    def facilities(self) -> list:
        r = self._post("/services/rest/v1/facility/getAllFacilities", {})
        return r.get("facilities", [])

    def search_returns(self, from_date: str, to_date: str) -> list:
        r = self._post("/services/rest/v1/oms/return/search",
                       {"fromDate": from_date, "toDate": to_date})
        return r.get("elements", [])
