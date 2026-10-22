"""GATE-D ka asal roop (V12.1): Amazon Ads WRITE adapter.
ManualAdapter insaani saboot par chalta hai; ye adapter vendor se sach me badlav karke
REFETCH se pushti karta hai, aur purani halat yaad rakh kar ROLLBACK bhi kar sakta hai.
Suraksha: jab tak capability registry me write_ads = 'certified' nahi, adapter chalega hi nahi —
pilot sign-off ke bina live paisa haath nahi lagega.
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
            return {"error": f"Ads write capability certified nahi hai (halat: {c['status']}) — pehle pilot sign-off se registry me certified karo. Koi badlav NAHI hua."}
        kind = payload.get("kind") or action.get("kind")
        db = self.store.db; ensure_v12(db)
        try:
            if kind in ("PAUSE_CAMPAIGN", "RESUME_CAMPAIGN"):
                cid = payload["campaign_id"]
                before = self._campaign(cid)
                if not before: return {"error": "Campaign vendor par mila nahi — badlav nahi hua"}
                want = "PAUSED" if kind == "PAUSE_CAMPAIGN" else "ENABLED"
                self.ads.update_campaigns([{"campaignId": cid, "state": want}])
                after = self._campaign(cid)
                if not after or after.get("state") != want:
                    return {"error": f"Vendor par pushti nahi mili (state={after and after.get('state')}) — applied NAHI mana jayega"}
                db.execute("UPDATE action_v12 SET diff=? WHERE id=?",
                           (json.dumps({"before_state": before.get("state"), "campaign_id": cid}), action["id"])); db.commit()
                return {"vendor_ref": f"ads:campaign:{cid}:{want}"}
            if kind == "SET_KEYWORD_BID":
                kid, bid = payload["keyword_id"], float(payload["bid"])
                before = self._keyword(kid)
                if not before: return {"error": "Keyword vendor par mila nahi"}
                self.ads.update_keywords([{"keywordId": kid, "bid": bid}])
                after = self._keyword(kid)
                if not after or abs(float(after.get("bid", -1)) - bid) > 0.001:
                    return {"error": "Bid ki refetch-pushti nahi mili — applied NAHI mana jayega"}
                db.execute("UPDATE action_v12 SET diff=? WHERE id=?",
                           (json.dumps({"before_bid": before.get("bid"), "keyword_id": kid}), action["id"])); db.commit()
                return {"vendor_ref": f"ads:keyword:{kid}:bid={bid}"}
            return {"error": f"Is adapter ko '{kind}' chalana nahi aata"}
        except Exception as e:
            return {"error": f"Vendor write fail: {type(e).__name__}: {e}"}
    def rollback(self, action_row: dict) -> dict:
        """Execute ke samay yaad ki gayi purani halat wapas lagao + refetch pushti."""
        diff = json.loads(action_row.get("diff") or "{}")
        p = json.loads(action_row.get("payload") or "{}")
        kind = p.get("kind") or action_row.get("kind")
        try:
            if "campaign_id" in diff:
                self.ads.update_campaigns([{"campaignId": diff["campaign_id"], "state": diff["before_state"]}])
                after = self._campaign(diff["campaign_id"])
                if after and after.get("state") == diff["before_state"]:
                    return {"ok": True, "note": f"Campaign purani halat ({diff['before_state']}) par wapas"}
            if "keyword_id" in diff:
                self.ads.update_keywords([{"keywordId": diff["keyword_id"], "bid": float(diff["before_bid"])}])
                after = self._keyword(diff["keyword_id"])
                if after and abs(float(after.get("bid", -1)) - float(diff["before_bid"])) < 0.001:
                    return {"ok": True, "note": f"Bid purani rakam ({diff['before_bid']}) par wapas"}
            return {"ok": False, "error": "Rollback ki pushti nahi mili ya purani halat darj nahi thi"}
        except Exception as e:
            return {"ok": False, "error": f"Rollback fail: {e}"}
