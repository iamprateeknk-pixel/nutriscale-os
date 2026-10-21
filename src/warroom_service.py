"""War-Room Service v2 — SIRF ASAL DATA. Koi demo number nahi banta.
Data DB me hai (connectors/CSV se aaya) to asal hisaab; nahi hai to connected=False
ke saath khaali halat — dashboard wahi dikhayega, jhooth kabhi nahi.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store
from organic_flywheel import flywheel
from connectors import config as cfg

def warroom_data(store: Store = None) -> dict:
    own = store is None
    store = store or Store()
    try:
        if not store.has_real_data():
            return {"connected": False, "demo_data": False,
                    "message": "Abhi koi asal data nahi hai. Connector configure karo ya CSV report import karo — tareeka CONNECTORS_SETUP.md me hai.",
                    "connectors_status": cfg.status_all(),
                    "kpis": None, "products": [], "campaigns": [], "inventory": [], "waste_terms": []}
        t = store.totals()
        # Organic = kul order sales - paid sales (flywheel ka asal hisaab)
        organic = max(0.0, t["order_sales"] - t["paid_sales"])
        fw = flywheel(t["ad_spend"], t["paid_sales"], organic) if t["ad_spend"] else {
            "blended_roas": 0, "paid_roas": 0, "tacos_pct": 0, "organic_share_pct": 0}
        return {"connected": True, "demo_data": False,
                "connectors_status": cfg.status_all(),
                "kpis": {**fw, "total_sales": t["order_sales"], "ad_spend": t["ad_spend"],
                         "paid_sales": t["paid_sales"], "organic_sales": round(organic, 2)},
                "products": store.all_products(),
                "campaigns": store.all_campaigns(),
                "inventory": store.all_inventory(),
                "waste_terms": store.waste_terms(),
                "note": "Ye saare numbers DB ke asal records se bane hain (connectors/CSV sync se)."}
    finally:
        if own: store.close()
