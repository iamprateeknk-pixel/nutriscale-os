"""Flipkart Seller API Connector.
Token: app_id/app_secret se OAuth. Listings, Orders, Returns, Inventory.
Note: Flipkart API access har seller ko khula nahi milta — Seller Hub se API access ki
manzuri lagti hai (guide CONNECTORS_SETUP.md me). Na mile to CSV import ka rasta hamesha khula hai.
Docs: https://seller.flipkart.com/api-docs/
"""
from urllib.parse import urlencode
from .config import require
from .http_base import request_json

ENDPOINT = "https://api.flipkart.net"
TOKEN_URL = "https://api.flipkart.net/oauth-service/oauth/token?grant_type=client_credentials&scope=Seller_Api"

class Flipkart:
    def __init__(self, cfg: dict = None, transport=None):
        self.cfg = cfg if cfg is not None else require("flipkart")
        self.transport = transport; self._token = None

    def access_token(self) -> str:
        if self._token: return self._token
        import base64
        cred = base64.b64encode(f"{self.cfg['app_id']}:{self.cfg['app_secret']}".encode()).decode()
        r = request_json("GET", TOKEN_URL, headers={"Authorization": f"Basic {cred}"}, transport=self.transport)
        self._token = r["access_token"]; return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token()}", "Content-Type": "application/json"}

    def get_orders(self, from_date: str, to_date: str) -> list:
        q = urlencode({"filter": f'{{"orderDate":{{"fromDate":"{from_date}","toDate":"{to_date}"}}}}'})
        r = request_json("GET", f"{ENDPOINT}/sellers/orders/search?{q}", headers=self._headers(), transport=self.transport)
        return r.get("orderItems", [])

    def get_listings(self) -> list:
        r = request_json("GET", f"{ENDPOINT}/sellers/listings/v3/get/listings", headers=self._headers(), transport=self.transport)
        return r.get("listings", []) if isinstance(r, dict) else []

    def get_listing(self, sku_id: str) -> dict:
        return request_json("GET", f"{ENDPOINT}/sellers/listings/v3/{sku_id}", headers=self._headers(), transport=self.transport)

    def update_inventory(self, sku_id: str, quantity: int, location_id: str = "") -> dict:
        body = {sku_id: {"price": None, "locations": [{"id": location_id, "quantity": quantity}]}}
        # sirf quantity badalna hai to price purana rakhna padta hai — pehle listing padho
        cur = self.get_listing(sku_id)
        body[sku_id]["price"] = {"mrp": cur.get("mrp"), "sellingPrice": cur.get("sellingPrice")}
        return request_json("POST", f"{ENDPOINT}/sellers/listings/v3/update/inventory",
                            headers=self._headers(), json_body=body, transport=self.transport)
