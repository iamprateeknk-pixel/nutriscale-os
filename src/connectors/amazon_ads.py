"""Amazon Ads API Connector (EU endpoint).
OAuth (LWA) -> Profiles -> Sponsored Products campaigns/ad groups/keywords +
Reporting v3 (search term report — A06 Ads Agent ka khana yahi se aayega).
Docs: https://advertising.amazon.com/API/docs/en-us/
"""
from .config import require
from .http_base import request_json

ENDPOINT = "https://advertising-api-eu.amazon.com"
LWA_URL = "https://api.amazon.com/auth/o2/token"
SP_CONTENT_TYPE = "application/vnd.spCampaign.v3+json"

class AmazonAds:
    def __init__(self, cfg: dict = None, transport=None):
        self.cfg = cfg if cfg is not None else require("amazon_ads")
        self.transport = transport; self._token = None

    def access_token(self) -> str:
        if self._token: return self._token
        r = request_json("POST", LWA_URL, form_body={
            "grant_type": "refresh_token", "refresh_token": self.cfg["refresh_token"],
            "client_id": self.cfg["client_id"], "client_secret": self.cfg["client_secret"]},
            transport=self.transport)
        self._token = r["access_token"]; return self._token

    def _headers(self, ct: str = None) -> dict:
        h = {"Authorization": f"Bearer {self.access_token()}",
             "Amazon-Advertising-API-ClientId": self.cfg["client_id"],
             "Amazon-Advertising-API-Scope": str(self.cfg["profile_id"])}
        if ct: h["Content-Type"] = ct; h["Accept"] = ct
        return h

    def list_profiles(self) -> list:
        return request_json("GET", ENDPOINT + "/v2/profiles",
                            headers={"Authorization": f"Bearer {self.access_token()}",
                                     "Amazon-Advertising-API-ClientId": self.cfg["client_id"]},
                            transport=self.transport)

    def list_campaigns(self) -> list:
        r = request_json("POST", ENDPOINT + "/sp/campaigns/list", headers=self._headers(SP_CONTENT_TYPE),
                         json_body={"maxResults": 100}, transport=self.transport)
        return r.get("campaigns", [])

    def list_keywords(self) -> list:
        r = request_json("POST", ENDPOINT + "/sp/keywords/list",
                         headers=self._headers("application/vnd.spKeyword.v3+json"),
                         json_body={"maxResults": 1000}, transport=self.transport)
        return r.get("keywords", [])

    def request_search_term_report(self, start_date: str, end_date: str) -> str:
        """Reporting v3 — reportId milega, phir status poll karke download URL (gzip JSON)."""
        body = {"name": "GrowthOS Search Terms", "startDate": start_date, "endDate": end_date,
                "configuration": {"adProduct": "SPONSORED_PRODUCTS", "groupBy": ["searchTerm"],
                                  "columns": ["searchTerm", "campaignName", "clicks", "cost",
                                              "purchases14d", "sales14d", "impressions"],
                                  "reportTypeId": "spSearchTerm", "timeUnit": "SUMMARY", "format": "GZIP_JSON"}}
        r = request_json("POST", ENDPOINT + "/reporting/reports", headers=self._headers("application/json"),
                         json_body=body, transport=self.transport)
        return r.get("reportId", "")

    def report_status(self, report_id: str) -> dict:
        return request_json("GET", f"{ENDPOINT}/reporting/reports/{report_id}",
                            headers=self._headers("application/json"), transport=self.transport)
