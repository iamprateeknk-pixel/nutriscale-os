"""War-Room Service v2 — SIRF ASAL DATA. Koi demo number nahi banta.
Data DB me hai (connectors/CSV se aaya) to asal hisaab; nahi hai to connected=False
ke saath khaali halat — dashboard wahi dikhayega, jhooth kabhi nahi.
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
                    "message": "Abhi koi asal data nahi hai. Connector configure karo ya CSV report import karo — tareeka CONNECTORS_SETUP.md me hai.",
                    "connectors_status": cfg.status_all(),
                    "kpis": None, "products": [], "campaigns": [], "inventory": [], "waste_terms": []}
        import analytics as AN
        st = AN.sales_totals(store.db, platform)   # V12.2 canonical-first; V13 platform filter
        camp = store.db.execute("SELECT COALESCE(SUM(spend),0) sp, COALESCE(SUM(sales),0) sa FROM campaigns" +
                                (" WHERE platform=?" if platform else ""), (platform,) if platform else ()).fetchone()
        ad_spend, paid_sales = round(camp["sp"], 2), round(camp["sa"], 2)
        # Organic = kul order sales - paid sales (flywheel ka asal hisaab)
        organic = max(0.0, st["revenue"] - paid_sales)
        # V15: TACOS sirf MATCHED khidki par — pichle 30 din ki dated bikri banam usi khidki ka ads kharch;
        # dono taraf ka dated data na mile to NOT_COMPARABLE (lifetime totals se jhootha ratio nahi)
        import datetime as _dt
        _end = _dt.date.today(); _start = _end - _dt.timedelta(days=29)
        _sw = store.db.execute("""SELECT COALESCE(SUM(oi.gross - COALESCE(oi.refund,0)),0) g, COUNT(*) n
            FROM order_items oi JOIN order_headers oh ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
            WHERE oh.order_date>=? AND oh.order_date<=? AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'""" +
            (" AND oi.platform=?" if platform else ""),
            ((_start.isoformat(), _end.isoformat()) + ((platform,) if platform else ()))).fetchone()
        # V17: sirf rows ka hona kaafi nahi — din-ginti coverage + channel-scope bhi parkha jayega
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
                _mix_ok, _mix_reason = False, "bikri me gair-Amazon hissa hai par ads data sirf Amazon ka — platform chun kar dekho"
        if _sw["n"] >= 5 and _aw["n"] and _sw["g"] and _cov >= 0.8 and _mix_ok:
            tacos_m = {"pct": round(100.0 * _aw["sp"] / _sw["g"], 2), "status": "MATCHED",
                       "ads_coverage_pct": round(100 * _cov, 1),
                       "window": {"from": _start.isoformat(), "to": _end.isoformat()}}
        else:
            _why = _mix_reason or (f"ads coverage sirf {round(100*_cov)}% hai (80% chahiye)" if _aw["n"] else "period-tagged ads data nahi") \
                   or (f"bikri lines sirf {_sw['n']} (kam se kam 5 chahiye)")
            tacos_m = {"pct": None, "status": "NOT_COMPARABLE", "reason": _why,
                       "ads_coverage_pct": round(100 * _cov, 1),
                       "window": {"from": _start.isoformat(), "to": _end.isoformat()}}
        fw = flywheel(ad_spend, paid_sales, organic) if ad_spend else {
            "blended_roas": 0, "paid_roas": 0, "tacos_pct": 0, "organic_share_pct": 0}
        return {"connected": True, "demo_data": False,
                "connectors_status": cfg.status_all(),
                "kpis": {**fw, "tacos_pct": tacos_m["pct"], "tacos_status": tacos_m["status"],
                         "tacos_window": tacos_m["window"],
                         "tacos_spend_basis": "period-tagged search-terms kharch (khidki ke andar ke periods hi)",
                         "orders_count_basis": "cancelled orders ginati se bahar; cancelled_orders alag se darj",
                         "revenue": st["revenue"], "total_sales": st["revenue"],
                         "orders": st["orders"], "sales_source": st["source"],
                         "ad_spend": ad_spend, "paid_sales": paid_sales,
                         "organic_sales": round(organic, 2),
                         "organic_basis": "ANDAAZ — kul bikri me se ads-attributed bikri ghata kar; asal organic alag se maapa nahi jata, attribution khidki reports ki hai",
                         "tacos_basis": "TACOS tabhi pakka jab bikri aur ads ki samay-khidki mile (matched period) — alag khidkiyon par NOT_COMPARABLE mana jayega"},
                "products": [p for p in store.all_products() if not platform or p.get("platform") == platform],
                "campaigns": [c for c in store.all_campaigns() if not platform or c.get("platform") == platform],
                "inventory": store.all_inventory(),
                "waste_terms": store.waste_terms(),
                "note": "Ye saare numbers DB ke asal records se bane hain (connectors/CSV sync se)."}
    finally:
        if own: store.close()
