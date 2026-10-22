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
        fw = flywheel(ad_spend, paid_sales, organic) if ad_spend else {
            "blended_roas": 0, "paid_roas": 0, "tacos_pct": 0, "organic_share_pct": 0}
        return {"connected": True, "demo_data": False,
                "connectors_status": cfg.status_all(),
                "kpis": {**fw, "revenue": st["revenue"], "total_sales": st["revenue"],
                         "orders": st["orders"], "sales_source": st["source"],
                         "ad_spend": ad_spend, "paid_sales": paid_sales,
                         "organic_sales": round(organic, 2)},
                "products": [p for p in store.all_products() if not platform or p.get("platform") == platform],
                "campaigns": [c for c in store.all_campaigns() if not platform or c.get("platform") == platform],
                "inventory": store.all_inventory(),
                "waste_terms": store.waste_terms(),
                "note": "Ye saare numbers DB ke asal records se bane hain (connectors/CSV sync se)."}
    finally:
        if own: store.close()
