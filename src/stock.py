"""Stock Channel Mapping (V20) — a location's channel now comes from a map, not a guess.
Up to V19 the channel was derived by searching the location NAME for 'amazon/fba/flipkart' — a place like
'Godown' always stayed 'unclassified', and a misleading name could get the wrong channel.
Now: explicit mapping first (stock_channel_map) — once a location is mapped, its channel is fixed.
Only without a mapping does the old name guess (HEURISTIC) apply, and that basis is stated clearly so
mistakes are visible, not hidden. Sellable/unsellable: channel math only uses sellable stock."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

CHANNELS = ("Amazon", "Flipkart")

def set_stock_channel(db, location: str, channel: str, updated_by: str = "") -> dict:
    """Fix one location's channel. channel is 'Amazon'/'Flipkart', or 'unclassified' to clear it."""
    ensure_v12(db)
    db.execute("""INSERT INTO stock_channel_map(location,channel,updated_by,updated_at) VALUES (?,?,?,?)
                  ON CONFLICT(location) DO UPDATE SET channel=excluded.channel, updated_by=excluded.updated_by, updated_at=excluded.updated_at""",
               (location, channel, updated_by, now_utc())); db.commit()
    return {"location": location, "channel": channel, "basis": "EXPLICIT"}

def channel_map(db) -> dict:
    ensure_v12(db)
    return {r["location"]: r["channel"] for r in db.execute("SELECT location, channel FROM stock_channel_map")}

def _heuristic(location: str) -> str:
    l = (location or "").lower()
    if "amazon" in l or "fba" in l: return "Amazon"
    if "flipkart" in l or "ekart" in l: return "Flipkart"
    return "unclassified"

def channel_for(db, location: str) -> tuple:
    """(channel, basis) — basis is EXPLICIT (from the map), HEURISTIC (name guess) or UNCLASSIFIED."""
    ensure_v12(db)
    r = db.execute("SELECT channel FROM stock_channel_map WHERE location=?", (location,)).fetchone()
    if r: return (r["channel"], "EXPLICIT")
    h = _heuristic(location)
    return (h, "HEURISTIC" if h != "unclassified" else "UNCLASSIFIED")

def sellable_of(row) -> int:
    """The sellable part of an inventory row: sellable_qty if recorded, otherwise the full qty."""
    q = int(row["qty"] or 0)
    try: s = row["sellable_qty"]
    except Exception: s = None
    return q if s is None else int(s or 0)

def unsellable_of(row) -> int:
    q = int(row["qty"] or 0)
    try: u = row["unsellable_qty"]
    except Exception: u = None
    if u is not None: return int(u or 0)
    return max(0, q - sellable_of(row))
