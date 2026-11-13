"""The real GATE-D (V12.1): Amazon Ads WRITE adapter.
The ManualAdapter relies on human proof; this adapter actually changes things at the vendor,
confirms via REFETCH, and remembers the previous state so it can ROLL BACK.
Safety: until write_ads = 'certified' in the capability registry, the adapter does not run at all —
no live money is touched without a pilot sign-off.
Supported payloads:
  {"kind":"PAUSE_CAMPAIGN","campaign_id":"..."} / {"kind":"RESUME_CAMPAIGN",...}
  {"kind":"SET_KEYWORD_BID","keyword_id":"...","bid": 4.5}
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12
import capabilities as caps

class AmazonAdsWriteAdapter:
    name = "AMAZON_ADS_API"
    def __init__(self, store, ads=None):
        self.store = store
        self._ads = ads
    @property
    def ads(self):
        if self._ads is None:
            from connectors.amazon_ads import AmazonAds
            self._ads = AmazonAds()
        return self._ads
    def _gate(self):
        c = caps.capability(self.store.db, "Amazon", "write_ads")
        return c["status"] == "certified", c
    def _campaign(self, cid):
        for c in self.ads.list_campaigns():
            if str(c.get("campaignId")) == str(cid): return c
        return None
    def _keyword(self, kid):
        for k in self.ads.list_keywords():
            if str(k.get("keywordId")) == str(kid): return k
        return None
    def execute(self, payload: dict, action: dict) -> dict:
        ok, c = self._gate()
        if not ok:
            return {"error": f"Ads write capability is not certified (status: {c['status']}) — certify it in the registry via pilot sign-off first. NOTHING was changed."}
        kind = payload.get("kind") or action.get("kind")
        db = self.store.db; ensure_v12(db)
        try:
            if kind in ("PAUSE_CAMPAIGN", "RESUME_CAMPAIGN"):
                cid = payload["campaign_id"]
                before = self._campaign(cid)
                if not before: return {"error": "Campaign not found at the vendor — nothing changed"}
                want = "PAUSED" if kind == "PAUSE_CAMPAIGN" else "ENABLED"
                self.ads.update_campaigns([{"campaignId": cid, "state": want}])
                after = self._campaign(cid)
                if not after or after.get("state") != want:
                    return {"error": f"No confirmation from the vendor (state={after and after.get('state')}) — NOT treated as applied"}
                db.execute("UPDATE action_v12 SET diff=? WHERE id=?",
                           (json.dumps({"before_state": before.get("state"), "campaign_id": cid}), action["id"])); db.commit()
                return {"vendor_ref": f"ads:campaign:{cid}:{want}"}
            if kind == "SET_KEYWORD_BID":
                kid, bid = payload["keyword_id"], float(payload["bid"])
                before = self._keyword(kid)
                if not before: return {"error": "Keyword not found at the vendor"}
                self.ads.update_keywords([{"keywordId": kid, "bid": bid}])
                after = self._keyword(kid)
                if not after or abs(float(after.get("bid", -1)) - bid) > 0.001:
                    return {"error": "No refetch confirmation of the bid — NOT treated as applied"}
                db.execute("UPDATE action_v12 SET diff=? WHERE id=?",
                           (json.dumps({"before_bid": before.get("bid"), "keyword_id": kid}), action["id"])); db.commit()
                return {"vendor_ref": f"ads:keyword:{kid}:bid={bid}"}
            return {"error": f"This adapter cannot run '{kind}'"}
        except Exception as e:
            return {"error": f"Vendor write fail: {type(e).__name__}: {e}"}
    def rollback(self, action_row: dict) -> dict:
        """Re-apply the state remembered at execution time + refetch confirmation."""
        diff = json.loads(action_row.get("diff") or "{}")
        p = json.loads(action_row.get("payload") or "{}")
        kind = p.get("kind") or action_row.get("kind")
        try:
            if "campaign_id" in diff:
                self.ads.update_campaigns([{"campaignId": diff["campaign_id"], "state": diff["before_state"]}])
                after = self._campaign(diff["campaign_id"])
                if after and after.get("state") == diff["before_state"]:
                    return {"ok": True, "note": f"Campaign restored to its previous state ({diff['before_state']})"}
            if "keyword_id" in diff:
                self.ads.update_keywords([{"keywordId": diff["keyword_id"], "bid": float(diff["before_bid"])}])
                after = self._keyword(diff["keyword_id"])
                if after and abs(float(after.get("bid", -1)) - float(diff["before_bid"])) < 0.001:
                    return {"ok": True, "note": f"Bid restored to its previous amount ({diff['before_bid']})"}
            return {"ok": False, "error": "No rollback confirmation, or the previous state was not recorded"}
        except Exception as e:
            return {"ok": False, "error": f"Rollback fail: {e}"}
