"""War-Room Service v2 — REAL DATA ONLY. No demo numbers are ever generated.
If data is in the DB (from connectors/CSV) the real numbers are calculated; otherwise connected=False
with an empty state — the dashboard shows exactly that, never a lie.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store
from organic_flywheel import flywheel
from connectors import config as cfg

def warroom_data(store: Store = None, platform: str = None) -> dict:
    own = store is None
    store = store or Store()
    try:
        if not store.has_real_data():
            return {"connected": False, "demo_data": False,
                    "message": "No real data yet. Configure a connector or upload a CSV report — see CONNECTORS_SETUP.md.",
                    "connectors_status": cfg.status_all(),
                    "kpis": None, "products": [], "campaigns": [], "inventory": [], "waste_terms": []}
        import analytics as AN
        st = AN.sales_totals(store.db, platform)   # V12.2 canonical-first; V13 platform filter
        camp = store.db.execute("SELECT COALESCE(SUM(spend),0) sp, COALESCE(SUM(sales),0) sa FROM campaigns" +
                                (" WHERE platform=?" if platform else ""), (platform,) if platform else ()).fetchone()
        ad_spend, paid_sales = round(camp["sp"], 2), round(camp["sa"], 2)
        # Organic = total order sales - paid sales (the real flywheel calculation)
        organic = max(0.0, st["revenue"] - paid_sales)
        # V15: TACOS only on a MATCHED window — dated sales of the last 30 days vs ad spend in the same window;
        # without dated data on both sides it is NOT_COMPARABLE (no fake ratio from lifetime totals)
        import datetime as _dt
        _end = _dt.date.today(); _start = _end - _dt.timedelta(days=29)
        _sw = store.db.execute("""SELECT COALESCE(SUM(oi.gross - COALESCE(oi.refund,0)),0) g, COUNT(*) n
            FROM order_items oi JOIN order_headers oh ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
            WHERE oh.order_date>=? AND oh.order_date<=? AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'""" +
            (" AND oi.platform=?" if platform else ""),
            ((_start.isoformat(), _end.isoformat()) + ((platform,) if platform else ()))).fetchone()
        # V17: rows existing is not enough — day-count coverage + channel scope are checked too
        _src_like = (platform + "%") if platform else "%"
        _aw = store.db.execute("SELECT COALESCE(SUM(spend),0) sp, COUNT(*) n FROM search_terms WHERE period_start>=? AND period_end<=? AND period_start<>'' AND source LIKE ?",
                               (_start.isoformat(), _end.isoformat(), _src_like)).fetchone()
        _periods = store.db.execute("SELECT DISTINCT period_start, period_end FROM search_terms WHERE period_start>=? AND period_end<=? AND period_start<>'' AND source LIKE ?",
                                     (_start.isoformat(), _end.isoformat(), _src_like)).fetchall()
        _covered = set()
        for _p in _periods:
            _d1 = _dt.date.fromisoformat(str(_p["period_start"])[:10]); _d2 = _dt.date.fromisoformat(str(_p["period_end"])[:10])
            while _d1 <= _d2:
                if _start <= _d1 <= _end: _covered.add(_d1)
                _d1 += _dt.timedelta(days=1)
        _cov = len(_covered) / 30.0
        _mix_ok, _mix_reason = True, ""
        if not platform:
            _other = store.db.execute("""SELECT COALESCE(SUM(oi.gross - COALESCE(oi.refund,0)),0) g FROM order_items oi
                JOIN order_headers oh ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
                WHERE oh.order_date>=? AND oh.order_date<=? AND oi.platform<>'Amazon'""",
                (_start.isoformat(), _end.isoformat())).fetchone()["g"]
            if _other and _other > 0:
                _mix_ok, _mix_reason = False, "sales include non-Amazon channels but ads data is Amazon-only — pick a platform"
        if _sw["n"] >= 5 and _aw["n"] and _sw["g"] and _cov >= 0.8 and _mix_ok:
            tacos_m = {"pct": round(100.0 * _aw["sp"] / _sw["g"], 2), "status": "MATCHED",
                       "ads_coverage_pct": round(100 * _cov, 1),
                       "window": {"from": _start.isoformat(), "to": _end.isoformat()}}
        else:
            _why = _mix_reason or (f"ads coverage is only {round(100*_cov)}% (80% needed)" if _aw["n"] else "no period-tagged ads data") \
                   or (f"only {_sw['n']} sales lines (at least 5 needed)")
            tacos_m = {"pct": None, "status": "NOT_COMPARABLE", "reason": _why,
                       "ads_coverage_pct": round(100 * _cov, 1),
                       "window": {"from": _start.isoformat(), "to": _end.isoformat()}}
        fw = flywheel(ad_spend, paid_sales, organic) if ad_spend else {
            "blended_roas": 0, "paid_roas": 0, "tacos_pct": 0, "organic_share_pct": 0}
        return {"connected": True, "demo_data": False,
                "connectors_status": cfg.status_all(),
                "kpis": {**fw, "tacos_pct": tacos_m["pct"], "tacos_status": tacos_m["status"],
                         "tacos_window": tacos_m["window"],
                         "tacos_spend_basis": "period-tagged search-term spend (only periods inside the window)",
                         "orders_count_basis": "cancelled orders excluded from counts; cancelled_orders recorded separately",
                         "revenue": st["revenue"], "total_sales": st["revenue"],
                         "orders": st["orders"], "sales_source": st["source"],
                         "ad_spend": ad_spend, "paid_sales": paid_sales,
                         "organic_sales": round(organic, 2),
                         "organic_basis": "ESTIMATE — total sales minus ads-attributed sales; real organic is not measured separately, attribution windows come from the reports",
                         "tacos_basis": "TACOS is only reliable when sales and ads share the same time window (matched period) — different windows are NOT_COMPARABLE"},
                "products": [p for p in store.all_products() if not platform or p.get("platform") == platform],
                "campaigns": [c for c in store.all_campaigns() if not platform or c.get("platform") == platform],
                "inventory": store.all_inventory(),
                "waste_terms": store.waste_terms(),
                "note": "All these numbers come from real DB records (connector/CSV sync)."}
    finally:
        if own: store.close()
