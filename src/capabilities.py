"""API-03 Capability Registry + INT-05 External Intelligence Adapter.
Niyam: jo capability certified nahi, UI use chhupayega/nishkriy rakhega — jhootha button kabhi nahi.
Intel adapter: licensed provider na ho to har metric UNAVAILABLE + wajah — andaaz kabhi nahi.
"""
import os, sys, csv, glob
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

DEFAULT_CAPS = [
    ("Amazon", "read_orders", "code_ready", "SP-API code taiyaar hai; live certification seller keys ke baad"),
    ("Amazon", "read_ads", "code_ready", "Ads Reporting v3 pipeline taiyaar; live certification keys ke baad"),
    ("Amazon", "write_ads", "not_certified", "Write adapter pilot + owner sign-off ke baad hi on hoga"),
    ("Amazon", "edit_listing", "not_certified", "Listings API pilot ke baad"),
    ("Flipkart", "read_orders", "code_ready", "Seller API/CSV; live parity test keys ke baad"),
    ("Flipkart", "read_ads", "report_only", "Programmatic Ads API uplabdh nahi — sirf report/CSV import chalega"),
    ("Flipkart", "write_ads", "unavailable", "Flipkart par ads write ka koi certified rasta nahi — UI me button hi nahi dikhega"),
    ("Flipkart", "edit_listing", "not_certified", "Seller API manzuri ke baad"),
    ("External", "keyword_provider", "unavailable", "Licensed provider (Helium10 aadi) ka contract nahi — volume/rank 'unknown' rahega"),
    ("External", "rank_provider", "unavailable", "Rank observation sirf apne darj kiye hue/licensed data se"),
]

def seed_capabilities(db):
    ensure_v12(db)
    for p, c, s, r in DEFAULT_CAPS:
        db.execute("INSERT OR IGNORE INTO capabilities VALUES (?,?,?,?,?)", (p, c, s, r, "")); db.commit()

def set_capability(db, platform, capability, status, reason=""):
    ensure_v12(db)
    db.execute("INSERT OR REPLACE INTO capabilities VALUES (?,?,?,?,?)",
               (platform, capability, status, reason, now_utc())); db.commit()

def capability(db, platform, capability) -> dict:
    seed_capabilities(db)
    r = db.execute("SELECT * FROM capabilities WHERE platform=? AND capability=?", (platform, capability)).fetchone()
    if not r: return {"status": "unavailable", "reason": "Registry me darj nahi"}
    return dict(r)

def all_capabilities(db) -> list:
    seed_capabilities(db)
    return [dict(r) for r in db.execute("SELECT * FROM capabilities ORDER BY platform, capability")]

class IntelProvider:
    """INT-05: bahari keyword/rank data ka darwaza. Provider = 'licensed_csv' folder ya None.
    None ho to sab UNAVAILABLE — yahi imaandaar jawab hai."""
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
                    "reason": "Licensed keyword provider connected nahi — volume ka andaaz dikhana mana hai"}
        for r in rows:
            if (r.get("keyword") or r.get("term") or "").lower() == term.lower():
                return {"term": term, "status": "ESTIMATED", "volume": int(float(r.get("volume") or r.get("search_volume") or 0)),
                        "source": "Licensed provider export", "class": "ESTIMATED"}
        return {"term": term, "status": "UNAVAILABLE", "volume": None, "reason": "Provider export me ye term nahi mila"}
    def reverse_keywords(self, peer_ref: str, platform: str = "Amazon") -> dict:
        rows = self._rows("*reverse*.csv")
        if rows is None:
            return {"peer": peer_ref, "status": "UNAVAILABLE", "keywords": [],
                    "reason": "Reverse-ASIN ka licensed feed nahi — sirf listing-text gap aur apne search terms se kaam chalega"}
        kw = [{"term": r.get("keyword", ""), "rank": r.get("rank")} for r in rows
              if (r.get("asin") or r.get("peer") or "") == peer_ref]
        return {"peer": peer_ref, "status": "ESTIMATED" if kw else "UNAVAILABLE", "keywords": kw,
                "source": "Licensed provider export", "class": "ESTIMATED"}
