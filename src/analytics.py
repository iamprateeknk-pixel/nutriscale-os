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
                          ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id {jw}""", args).fetchone()
    if ci["lines"]:
        # V18: orders ki GINATI bhi cancelled ko bahar rakhegi (pehle sirf revenue bahar tha — count jhootha bada dikhta tha)
        cw = ("WHERE platform=? AND" if platform else "WHERE") + " COALESCE(status,'') NOT LIKE 'Cancel%'"
        oc = db.execute(f"SELECT COUNT(DISTINCT platform||'|'||seller_account||'|'||external_order_id) c FROM order_headers {cw}", args).fetchone()["c"]
        cx = db.execute(f"SELECT COUNT(DISTINCT platform||'|'||seller_account||'|'||external_order_id) c FROM order_headers {w} "
                        + ("AND" if w else "WHERE") + " COALESCE(status,'') LIKE 'Cancel%'", args).fetchone()["c"]
        return {"revenue": round(ci["g"], 2), "orders": oc, "cancelled_orders": cx, "lines": ci["lines"],
                "source": "CANONICAL NET (order_items − refunds, cancelled bahar)"}
    lo = db.execute(f"SELECT COALESCE(SUM(amount),0) s, COUNT(*) c FROM orders {w}", args).fetchone()
    return {"revenue": round(lo["s"], 2), "orders": lo["c"], "lines": lo["c"], "source": "LEGACY (orders table — purana import)"}

def sku_sales(db, platform: str = None) -> list:
    ensure_v12(db)
    w = "WHERE oi.platform=?" if platform else ""
    rows = db.execute(f"""SELECT oi.sku, SUM(oi.qty) units, SUM(oi.gross - COALESCE(oi.refund,0)) revenue
                          FROM order_items oi LEFT JOIN order_headers oh
                            ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
                          {w} {'AND' if platform else 'WHERE'} COALESCE(oh.status,'') NOT LIKE 'Cancel%'
                          GROUP BY oi.sku ORDER BY revenue DESC""", (platform,) if platform else ()).fetchall()
    if rows: return [dict(r) for r in rows]
    return [dict(r) for r in db.execute(
        "SELECT sku, COUNT(*) units, SUM(amount) revenue FROM orders GROUP BY sku ORDER BY revenue DESC")]

def sku_velocity_per_day(db, sku: str, window_days: int = 30, platform: str = None) -> float:
    """Roz ki asal bikri — denominator poori observation-window (pehli se aakhri bikri-taareekh ka antar),
    sirf bikri-wale din nahi (V14 fix). V18: platform diya to raftaar sirf usi channel ki (channel-specific stock hisaab)."""
    ensure_v12(db)
    import datetime as _dt
    # V19 P0: sirf TRAILING window (taaza-taarin bikri-taareekh se peeche ke window_days din) ginega —
    # all-time units ko 30 se baantna galat tha; cancelled orders bhi bahar
    mx = db.execute("""SELECT MAX(oh.order_date) m FROM order_items oi JOIN order_headers oh
                       ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
                       WHERE oi.sku=? AND (? IS NULL OR oi.platform=?) AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'""",
                    (sku, platform, platform)).fetchone()
    if not mx or not mx["m"]: return 0.0
    d1 = _dt.date.fromisoformat(str(mx["m"])[:10]); d0 = d1 - _dt.timedelta(days=window_days - 1)
    r = db.execute("""SELECT COALESCE(SUM(oi.qty),0) q, MIN(oh.order_date) f, MAX(oh.order_date) t
                      FROM order_items oi JOIN order_headers oh
                        ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
                      WHERE oi.sku=? AND (? IS NULL OR oi.platform=?) AND oh.order_date>=? AND oh.order_date<=?
                        AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'""",
                   (sku, platform, platform, d0.isoformat(), d1.isoformat())).fetchone()
    if r and r["q"]:
        span = (_dt.date.fromisoformat(str(r["t"])[:10]) - _dt.date.fromisoformat(str(r["f"])[:10])).days + 1
        return r["q"] / max(1, min(window_days, span))
    lo = db.execute("SELECT COUNT(*) c FROM orders WHERE sku=?", (sku,)).fetchone()
    return (lo["c"] / window_days) if lo and lo["c"] else 0.0
