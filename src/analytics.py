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

STALE_WARN_DAYS = 14   # aakhri bikri itne din se purani ho to velocity par 'stale data' ki chetaavni

def sku_velocity_report(db, sku: str, window_days: int = 30, platform: str = None, as_of=None) -> dict:
    """Velocity report (V20) — khidki ka aakhri din AB 'aaj' (reporting date) hai, aakhri bikri nahi.
    V19 tak khidki MAX(order_date) se bandhi thi: 60 din purani bikri bhi 'taaza' raftaar dikhati thi.
    Ab purani bikri khidki se bahar girti hai, raftaar sach dikhati hai, aur stale chetaavni alag se milti hai."""
    ensure_v12(db)
    import datetime as _dt
    end = as_of or _dt.date.today()
    if isinstance(end, str): end = _dt.date.fromisoformat(end[:10])
    start = end - _dt.timedelta(days=window_days - 1)
    j = """FROM order_items oi JOIN order_headers oh
             ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
           WHERE oi.sku=? AND (? IS NULL OR oi.platform=?) AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'"""
    mx = db.execute(f"SELECT MAX(oh.order_date) m {j}", (sku, platform, platform)).fetchone()
    last = str(mx["m"])[:10] if mx and mx["m"] else None
    r = db.execute(f"""SELECT COALESCE(SUM(oi.qty),0) q, MIN(oh.order_date) f, MAX(oh.order_date) t,
                              COUNT(DISTINCT oh.order_date) od {j}
                       AND oh.order_date>=? AND oh.order_date<=?""",
                   (sku, platform, platform, start.isoformat(), end.isoformat())).fetchone()
    units = float(r["q"] or 0) if r else 0.0
    # V21 P0 FIX: denominator ab POORA reporting window (30 din) hai — V20 tak units sirf
    # pehli-aakhri bikri ke beech ke dino se bant-te the, jisse 3-din ki bikri bhi poori
    # raftaar lagti thi aur cover kam dikhta tha. Span-wali sankhya ab alag 'run_rate' hai.
    vel = units / window_days if units else 0.0
    run_rate = 0.0
    if units:
        span = (_dt.date.fromisoformat(str(r["t"])[:10]) - _dt.date.fromisoformat(str(r["f"])[:10])).days + 1
        run_rate = units / max(1, span)
    since = (end - _dt.date.fromisoformat(last)).days if last else None
    return {"sku": sku, "platform": platform, "velocity_per_day": round(vel, 4),
            "run_rate_per_day": round(run_rate, 4),
            "observed_sale_days": (r["od"] if r else 0),
            "window_start": start.isoformat(), "window_end": end.isoformat(), "window_days": window_days,
            "units_in_window": units, "last_sale_date": last, "days_since_last_sale": since,
            "stale": (since is None or since > STALE_WARN_DAYS),
            "basis": "CANONICAL — units / POORA reporting window (V21); run_rate sirf jaankari ke liye",
            "warning": ("STALE DATA — is SKU ki aakhri bikri " + (f"{since} din pehle" if since is not None else "kabhi darj hi nahi") +
                        "; raftaar purane data par bharosa karke mat chalao, pehle taaza sync karo") if (since is None or since > STALE_WARN_DAYS) else None}

def sku_velocity_per_day(db, sku: str, window_days: int = 30, platform: str = None) -> float:
    """Roz ki asal bikri. V20: khidki aaj se bandhi hai (stale bikri raftaar nahi bana sakti).
    Canonical data hi na ho to legacy orders par fallback (purane imports ke liye)."""
    rep = sku_velocity_report(db, sku, window_days, platform)
    if rep["last_sale_date"] is not None: return rep["velocity_per_day"]
    lo = db.execute("SELECT COUNT(*) c FROM orders WHERE sku=?", (sku,)).fetchone()
    return (lo["c"] / window_days) if lo and lo["c"] else 0.0
