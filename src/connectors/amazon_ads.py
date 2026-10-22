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

    def update_campaigns(self, campaigns: list) -> dict:
        """Write API: campaign state/budget badlav. Sirf certified capability par chalega (adapter gate)."""
        return request_json("POST", ENDPOINT + "/sp/campaigns", headers=self._headers(SP_CONTENT_TYPE),
                            json_body={"campaigns": campaigns}, transport=self.transport)

    def update_keywords(self, keywords: list) -> dict:
        return request_json("POST", ENDPOINT + "/sp/keywords",
                            headers=self._headers("application/vnd.spKeyword.v3+json"),
                            json_body={"keywords": keywords}, transport=self.transport)

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

    def wait_and_download(self, report_id: str, raw_transport=None, max_polls: int = 30,
                          sleep=lambda s: None) -> list:
        """INT-02: status poll -> COMPLETED par download URL -> gzip kholo -> rows.
        FAILURE/429 par saaf error — adhoori report ko data nahi mana jayega."""
        import gzip, json as _json
        from .http_base import request_raw
        for _ in range(max_polls):
            st = self.report_status(report_id)
            status = st.get("status")
            if status == "COMPLETED":
                raw = request_raw("GET", st["url"], transport=raw_transport)
                if isinstance(raw, (bytes, bytearray)):
                    try: rows = _json.loads(gzip.decompress(bytes(raw)).decode())
                    except Exception: rows = _json.loads(bytes(raw).decode())
                else: rows = raw
                return rows if isinstance(rows, list) else rows.get("rows", [])
            if status in ("FAILURE", "CANCELLED"):
                raise RuntimeError(f"Ads report fail ho gayi: {st.get('failureReason', status)}")
            sleep(5)
        raise RuntimeError("Ads report samay par taiyaar nahi hui — baad me dobara koshish hogi (job retry)")

    def sync_search_terms(self, store, start_date: str, end_date: str, raw_transport=None,
                          sleep=lambda s: None) -> dict:
        """Poora pipeline: request -> poll -> download -> DB (search_terms) + batch record."""
        import sys as _s, os as _os
        _s.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))
        from platform_core import ensure_v12, now_utc
        rid = self.request_search_term_report(start_date, end_date)
        rows = self.wait_and_download(rid, raw_transport=raw_transport, sleep=sleep)
        # V12.2: wahi period dobara sync ho to purani rows pehle hatengi — totals double nahi honge (idempotent sync)
        ensure_v12(store.db)
        store.db.execute("DELETE FROM search_terms WHERE source='Amazon Ads API (Reporting v3)' AND period_start=? AND period_end=?",
                         (start_date, end_date)); store.db.commit()
        agg = {}
        for r in rows:
            term = r.get("searchTerm")
            if not term: continue
            a = agg.setdefault((str(term), str(r.get("campaignName", ""))), [0.0, 0.0, 0, 0])
            a[0] += float(r.get("cost", 0) or 0); a[1] += float(r.get("sales14d", 0) or 0)
            a[2] += int(r.get("clicks", 0) or 0); a[3] += int(r.get("purchases14d", 0) or 0)
        n = 0
        for (term, camp), (sp, sa, cl, pu) in agg.items():
            store.add_search_term(term, camp, sp, sa, cl, pu, source="Amazon Ads API (Reporting v3)",
                                  batch_id=f"api:{rid}", period_start=start_date, period_end=end_date)
            n += 1
        ensure_v12(store.db)
        store.db.execute("INSERT INTO import_batches(platform,seller_account,report_type,period_start,period_end,file_sha256,rows_ok,rows_bad,imported_by,imported_at,receipt) VALUES ('Amazon','default','ads_search_terms',?,?,?, ?,0,'ads-api',?,?)",
                         (start_date, end_date, f"api:{rid}", n, now_utc(), f"Ads API report {rid}: {n} terms"))
        store.db.commit()
        return {"report_id": rid, "imported": n, "period": (start_date, end_date)}
