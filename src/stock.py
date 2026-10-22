"""Stock Channel Mapping (V20) — location se channel ki pehchan ab andaze par nahi, nakse (map) par hogi.
V19 tak channel location ke NAAM me 'amazon/fba/flipkart' dhoondh kar banta tha — 'Godown' jaisi
jagah hamesha 'unclassified' rehti thi aur galat naam par galat channel bhi lag sakta tha.
Ab: pehle explicit mapping (stock_channel_map) — jo jagah ek baar map ho gayi, uska channel pakka.
Mapping na ho tabhi purana naam-andaz (HEURISTIC) lagega, aur woh basis saaf likha jayega taaki
galti dikhe, chhupe nahi. Sellable/unsellable: channel hisaab sirf bikne-yogya stock par hoga."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

CHANNELS = ("Amazon", "Flipkart")

def set_stock_channel(db, location: str, channel: str, updated_by: str = "") -> dict:
    """Ek location ka channel pakka karo. channel 'Amazon'/'Flipkart' ya saaf karne ke liye 'unclassified'."""
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
    """(channel, basis) — basis EXPLICIT (nakse se) ya HEURISTIC (naam-andaz) ya UNCLASSIFIED."""
    ensure_v12(db)
    r = db.execute("SELECT channel FROM stock_channel_map WHERE location=?", (location,)).fetchone()
    if r: return (r["channel"], "EXPLICIT")
    h = _heuristic(location)
    return (h, "HEURISTIC" if h != "unclassified" else "UNCLASSIFIED")

def sellable_of(row) -> int:
    """Ek inventory row ka bikne-yogya hissa: sellable_qty darj ho to wahi, warna poora qty."""
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
