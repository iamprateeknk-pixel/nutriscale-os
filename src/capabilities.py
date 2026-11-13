"""API-03 Capability Registry + INT-05 External Intelligence Adapter.
Rule: the UI hides/disables any capability that is not certified — never a fake button.
Intel adapter: without a licensed provider every metric is UNAVAILABLE + a reason — never an estimate.
"""
import os, sys, csv, glob
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

DEFAULT_CAPS = [
    ("Amazon", "read_orders", "code_ready", "SP-API code is ready; live certification after seller keys"),
    ("Amazon", "read_ads", "code_ready", "Ads Reporting v3 pipeline ready; live certification after keys"),
    ("Amazon", "write_ads", "not_certified", "The write adapter turns on only after a pilot + owner sign-off"),
    ("Amazon", "write_listings", "not_certified", "After a Listings API pilot"),
    ("Flipkart", "read_orders", "code_ready", "Seller API/CSV; live parity test after keys"),
    ("Flipkart", "read_ads", "report_only", "No programmatic Ads API — only report/CSV import"),
    ("Flipkart", "write_ads", "unavailable", "No certified way to write Flipkart ads — the UI shows no button"),
    ("Flipkart", "write_listings", "not_certified", "After Seller API approval"),
    ("External", "keyword_provider", "unavailable", "No licensed provider contract (Helium10 etc.) — volume/rank stay 'unknown'"),
    ("External", "rank_provider", "unavailable", "Rank observations only from your own recorded/licensed data"),
]

def seed_capabilities(db):
    ensure_v12(db)
    # V19: old name edit_listing -> write_listings (the publish gate checks this — keep one name)
    db.execute("UPDATE capabilities SET capability='write_listings' WHERE capability='edit_listing'"); db.commit()
    for p, c, s, r in DEFAULT_CAPS:
        db.execute("INSERT OR IGNORE INTO capabilities VALUES (?,?,?,?,?)", (p, c, s, r, ""))
        # V27: refresh the default note text (e.g. after a language change) only on rows nobody has
        # changed — same default status and never certified via set_capability.
        db.execute("""UPDATE capabilities SET reason=? WHERE platform=? AND capability=? AND status=?
                      AND COALESCE(certified_at,'')=''""", (r, p, c, s))
    db.commit()

def set_capability(db, platform, capability, status, reason=""):
    ensure_v12(db)
    db.execute("INSERT OR REPLACE INTO capabilities VALUES (?,?,?,?,?)",
               (platform, capability, status, reason, now_utc())); db.commit()

def capability(db, platform, capability) -> dict:
    seed_capabilities(db)
    r = db.execute("SELECT * FROM capabilities WHERE platform=? AND capability=?", (platform, capability)).fetchone()
    if not r: return {"status": "unavailable", "reason": "Not in the registry"}
    return dict(r)

def all_capabilities(db) -> list:
    seed_capabilities(db)
    return [dict(r) for r in db.execute("SELECT * FROM capabilities ORDER BY platform, capability")]

class IntelProvider:
    """INT-05: the gateway for external keyword/rank data. Provider = a 'licensed_csv' folder or None.
    With None everything is UNAVAILABLE — that is the honest answer."""
    def __init__(self, export_dir: str = None):
        self.export_dir = export_dir
    def _rows(self, name):
        if not self.export_dir: return None
        for f in glob.glob(os.path.join(self.export_dir, name)):
            with open(f, newline="", encoding="utf-8-sig") as fh:
                return list(csv.DictReader(fh))
        return None
    def keyword_volume(self, term: str, platform: str = "Amazon") -> dict:
        rows = self._rows("*keyword*volume*.csv")
        if rows is None:
            return {"term": term, "status": "UNAVAILABLE", "volume": None,
                    "reason": "No licensed keyword provider connected — showing volume estimates is not allowed"}
        for r in rows:
            if (r.get("keyword") or r.get("term") or "").lower() == term.lower():
                return {"term": term, "status": "ESTIMATED", "volume": int(float(r.get("volume") or r.get("search_volume") or 0)),
                        "source": "Licensed provider export", "class": "ESTIMATED"}
        return {"term": term, "status": "UNAVAILABLE", "volume": None, "reason": "This term is not in the provider export"}
    def reverse_keywords(self, peer_ref: str, platform: str = "Amazon") -> dict:
        rows = self._rows("*reverse*.csv")
        if rows is None:
            return {"peer": peer_ref, "status": "UNAVAILABLE", "keywords": [],
                    "reason": "No licensed reverse-ASIN feed — work from listing-text gaps and your own search terms"}
        kw = [{"term": r.get("keyword", ""), "rank": r.get("rank")} for r in rows
              if (r.get("asin") or r.get("peer") or "") == peer_ref]
        return {"peer": peer_ref, "status": "ESTIMATED" if kw else "UNAVAILABLE", "keywords": kw,
                "source": "Licensed provider export", "class": "ESTIMATED"}
