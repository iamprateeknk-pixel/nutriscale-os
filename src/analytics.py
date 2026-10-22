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
    # V15: revenue NET hai (gross - refund) aur Cancelled orders ginati se bahar
    jw = ("WHERE oi.platform=?" if platform else "") + (" AND" if platform else "WHERE") + " COALESCE(oh.status,'') NOT LIKE 'Cancel%'"
    ci = db.execute(f"""SELECT COALESCE(SUM(oi.gross - COALESCE(oi.refund,0)),0) g, COUNT(*) lines
                        FROM order_items oi JOIN order_headers oh
                          ON oi.platform=oh.platform AND oi.external_order_id=oh.external_order_id {jw}""", args).fetchone()
    if ci["lines"]:
        oc = db.execute(f"SELECT COUNT(DISTINCT platform||'|'||external_order_id) c FROM order_headers {w}", args).fetchone()["c"]
        return {"revenue": round(ci["g"], 2), "orders": oc, "lines": ci["lines"], "source": "CANONICAL NET (order_items − refunds, cancelled bahar)"}
    lo = db.execute(f"SELECT COALESCE(SUM(amount),0) s, COUNT(*) c FROM orders {w}", args).fetchone()
    return {"revenue": round(lo["s"], 2), "orders": lo["c"], "lines": lo["c"], "source": "LEGACY (orders table — purana import)"}

def sku_sales(db, platform: str = None) -> list:
    ensure_v12(db)
    w = "WHERE oi.platform=?" if platform else ""
    rows = db.execute(f"""SELECT oi.sku, SUM(oi.qty) units, SUM(oi.gross - COALESCE(oi.refund,0)) revenue
                          FROM order_items oi LEFT JOIN order_headers oh
                            ON oi.platform=oh.platform AND oi.external_order_id=oh.external_order_id
                          {w} {'AND' if platform else 'WHERE'} COALESCE(oh.status,'') NOT LIKE 'Cancel%'
                          GROUP BY oi.sku ORDER BY revenue DESC""", (platform,) if platform else ()).fetchall()
    if rows: return [dict(r) for r in rows]
    return [dict(r) for r in db.execute(
        "SELECT sku, COUNT(*) units, SUM(amount) revenue FROM orders GROUP BY sku ORDER BY revenue DESC")]

def sku_velocity_per_day(db, sku: str, window_days: int = 30) -> float:
    """Roz ki asal bikri — denominator poori observation-window (pehli se aakhri bikri-taareekh ka antar),
    sirf bikri-wale din nahi (V14 fix: sirf selling-days ginne se raftaar zyada dikhti thi, cover kam)."""
    ensure_v12(db)
    import datetime as _dt
    r = db.execute("""SELECT COALESCE(SUM(oi.qty),0) q, MIN(oh.order_date) d0, MAX(oh.order_date) d1
                      FROM order_items oi JOIN order_headers oh
                        ON oi.platform=oh.platform AND oi.external_order_id=oh.external_order_id
                      WHERE oi.sku=?""", (sku,)).fetchone()
    if r and r["q"] and r["d0"] and r["d1"]:
        try:
            span = (_dt.date.fromisoformat(str(r["d1"])[:10]) - _dt.date.fromisoformat(str(r["d0"])[:10])).days + 1
        except Exception:
            span = 1
        days = max(1, min(window_days, span))
        return r["q"] / days
    lo = db.execute("SELECT COUNT(*) c FROM orders WHERE sku=?", (sku,)).fetchone()
    return (lo["c"] / window_days) if lo and lo["c"] else 0.0
