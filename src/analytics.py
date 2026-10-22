"""Unified Canonical Analytics (V12.2) — War Room ka mismatch fix.
Naya sync canonical order_items me likhta hai, purana warroom legacy orders padhta tha —
ab ek hi sach: canonical maujud ho to wahi, warna legacy (purane imports ke liye)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12

def sales_totals(db, platform: str = None) -> dict:
    ensure_v12(db)
    w = "WHERE platform=?" if platform else ""
    args = (platform,) if platform else ()
    ci = db.execute(f"SELECT COALESCE(SUM(gross),0) g, COUNT(*) lines FROM order_items {w}", args).fetchone()
    if ci["lines"]:
        oc = db.execute(f"SELECT COUNT(DISTINCT platform||'|'||external_order_id) c FROM order_headers {w}", args).fetchone()["c"]
        return {"revenue": round(ci["g"], 2), "orders": oc, "lines": ci["lines"], "source": "CANONICAL (order_items)"}
    lo = db.execute(f"SELECT COALESCE(SUM(amount),0) s, COUNT(*) c FROM orders {w}", args).fetchone()
    return {"revenue": round(lo["s"], 2), "orders": lo["c"], "lines": lo["c"], "source": "LEGACY (orders table — purana import)"}

def sku_sales(db) -> list:
    ensure_v12(db)
    rows = db.execute("""SELECT sku, SUM(qty) units, SUM(gross) revenue FROM order_items
                         GROUP BY sku ORDER BY revenue DESC""").fetchall()
    if rows: return [dict(r) for r in rows]
    return [dict(r) for r in db.execute(
        "SELECT sku, COUNT(*) units, SUM(amount) revenue FROM orders GROUP BY sku ORDER BY revenue DESC")]

def sku_velocity_per_day(db, sku: str, window_days: int = 30) -> float:
    """Pichle window me roz ki asal bikri (canonical pehle). Dinankh na mile to kul/window ka surakshit andaaz nahi —
    sirf wahi data jo hai: order_headers ki taaza-taarin taareekh se window gin lo."""
    ensure_v12(db)
    r = db.execute("""SELECT COALESCE(SUM(oi.qty),0) q, COUNT(DISTINCT oh.order_date) days
                      FROM order_items oi JOIN order_headers oh
                        ON oi.platform=oh.platform AND oi.external_order_id=oh.external_order_id
                      WHERE oi.sku=?""", (sku,)).fetchone()
    if r and r["q"]:
        days = max(r["days"] or 1, 1)
        return r["q"] / days
    lo = db.execute("SELECT COUNT(*) c FROM orders WHERE sku=?", (sku,)).fetchone()
    return (lo["c"] / window_days) if lo and lo["c"] else 0.0
