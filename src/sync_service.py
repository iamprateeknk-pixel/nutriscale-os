"""Sync Service — F1 Data Sync Flow ka asal roop.
CLI:
  python3 src/sync_service.py --status                      -> kaunsa connector taiyaar hai
  python3 src/sync_service.py --csv-search-terms file.csv   -> Ads Search Term report DB me
  python3 src/sync_service.py --csv-campaigns file.csv
  python3 src/sync_service.py --csv-orders file.csv [--platform Flipkart]
  python3 src/sync_service.py --csv-inventory file.csv
  python3 src/sync_service.py --connector amazon_sp --orders-since 2026-10-01T00:00:00Z
Credentials na hon to saaf message milega ki kya bharna hai — jhootha sync kabhi nahi hoga.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store
from connectors import config as cfg
from connectors.csv_import import (import_ads_search_terms, import_campaign_report,
                                   import_sales_orders, import_inventory_csv)

def main():
    ap = argparse.ArgumentParser(description="Growth OS Sync Service")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--csv-search-terms"); ap.add_argument("--csv-campaigns")
    ap.add_argument("--csv-orders"); ap.add_argument("--csv-inventory")
    ap.add_argument("--platform", default="Amazon")
    ap.add_argument("--connector"); ap.add_argument("--orders-since", default="2026-09-01T00:00:00Z")
    a = ap.parse_args()
    if a.status:
        for name, s in cfg.status_all().items():
            print(f"{name}: {'✔ CONFIGURED' if s['configured'] else '✘ baki hai — missing: ' + ', '.join(s['missing'])}")
        return
    store = Store()
    try:
        if a.csv_search_terms: print(f"Search terms import hue: {import_ads_search_terms(a.csv_search_terms, store, a.platform)}")
        if a.csv_campaigns: print(f"Campaigns import hue: {import_campaign_report(a.csv_campaigns, store, a.platform)}")
        if a.csv_orders: print(f"Orders import hue: {import_sales_orders(a.csv_orders, store, a.platform)}")
        if a.csv_inventory: print(f"Inventory rows import hue: {import_inventory_csv(a.csv_inventory, store)}")
        if a.connector == "amazon_sp":
            from connectors.amazon_sp import AmazonSP
            orders = AmazonSP().get_orders(a.orders_since)
            for o in orders:
                store.add_order(o.get("AmazonOrderId", ""), "Amazon", "", float(o.get("OrderTotal", {}).get("Amount", 0) or 0))
            print(f"Amazon SP-API se orders sync hue: {len(orders)}")
        elif a.connector == "amazon_ads":
            from connectors.amazon_ads import AmazonAds
            camps = AmazonAds().list_campaigns()
            for c in camps: store.upsert_campaign(c.get("name", ""), "Amazon", 0, 0, source="Ads API")
            print(f"Amazon Ads se campaigns sync hue: {len(camps)}")
        elif a.connector == "unicommerce":
            from connectors.unicommerce import Unicommerce
            uc = Unicommerce()
            facs = uc.facilities(); print(f"Unicommerce facilities mile: {len(facs)}")
            for fac in facs:
                code = fac.get("code", "")
                for snap in uc.inventory_snapshot(code):
                    store.set_inventory(snap.get("itemTypeSKU", ""), code, int(snap.get("inventory", 0) or 0), source="Unicommerce API")
            print("Unicommerce inventory DB me sync ho gaya")
        elif a.connector:
            print(f"Connector '{a.connector}' ke liye sync function CONNECTORS_SETUP.md ke hisaab se chalega — pehle --status dekho")
    except cfg.NotConfigured as e:
        print(f"⛔ {e}"); sys.exit(2)
    finally:
        store.close()

if __name__ == "__main__":
    main()
