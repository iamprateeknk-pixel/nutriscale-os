"""Sync Service V2 — F1 Data Sync ka asal roop (V12.1 me sudhara gaya).
Purani kami (audit me pakdi gayi): SP orders bina SKU ke ghus rahe the, Ads search-term
sync CLI me tha hi nahi, Flipkart ka koi branch nahi tha. Ab:
  python3 src/sync_service.py --status
  python3 src/sync_service.py --csv-orders file [--platform Flipkart]   (wizard/canonical)
  python3 src/sync_service.py --csv-search-terms file.csv | --csv-campaigns file.csv | --csv-inventory file.csv
  python3 src/sync_service.py --connector amazon_sp --orders-since 2026-10-01T00:00:00Z   (orders + items, canonical)
  python3 src/sync_service.py --connector amazon_ads_terms --start 2026-10-01 --end 2026-10-07
  python3 src/sync_service.py --connector flipkart --from 2026-10-01 --to 2026-10-07      (orders + listings)
  python3 src/sync_service.py --connector unicommerce
Credentials na hon to saaf mana — jhootha sync kabhi nahi.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store
from connectors import config as cfg
from platform_core import ensure_v12, now_utc

def sync_amazon_orders(store, since: str, sp=None) -> dict:
    """SP-API orders + unke items — canonical order_headers/order_items me (line-level)."""
    from connectors.amazon_sp import AmazonSP
    sp = sp or AmazonSP()
    db = store.db; ensure_v12(db)
    orders = sp.get_orders(since); n_items = 0
    for o in orders:
        oid = o.get("AmazonOrderId", "")
        total = float((o.get("OrderTotal") or {}).get("Amount", 0) or 0)
        db.execute("INSERT OR IGNORE INTO order_headers VALUES (?,?,?,?,?,?,?)",
                   ("Amazon", "default", oid, str(o.get("PurchaseDate", ""))[:10], o.get("OrderStatus", ""), total, "INR"))
        for it in sp.get_order_items(oid):
            amt = float((it.get("ItemPrice") or {}).get("Amount", 0) or 0)
            db.execute("INSERT OR IGNORE INTO order_items VALUES (?,?,?,?,?,?,?,?,?)",
                       ("Amazon", "default", oid, str(it.get("OrderItemId", "")), it.get("SellerSKU", ""),
                        it.get("ASIN", ""), float(it.get("QuantityOrdered", 1) or 1), amt, 0))
            n_items += 1
    db.commit()
    return {"orders": len(orders), "items": n_items, "note": "Canonical line-level sync ho gaya"}

def sync_order_fees(store, days: int = 3, sp=None) -> dict:
    """SP Finances: taaza orders ki per-order fees order_fees me (SKU-exact dar ke liye, V14 scheduled)."""
    import datetime
    from connectors.amazon_sp import AmazonSP
    import finance as F
    sp = sp or AmazonSP()
    db = store.db; ensure_v12(db)
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    ids = [r["external_order_id"] for r in db.execute(
        "SELECT external_order_id FROM order_headers WHERE platform='Amazon' AND order_date>=?", (cutoff,))]
    total = 0
    for oid in ids:
        total += F.import_order_fees(db, sp.get_order_financials(oid))["imported"]
    return {"orders_checked": len(ids), "fee_rows": total,
            "note": "Fees SP Finances se aayi — SKU-exact dar ab in par banega"}

def sync_flipkart(store, from_date: str, to_date: str, fk=None) -> dict:
    """Flipkart orders (canonical) + listings (catalog). Ads Flipkart par report-only hai (capability registry)."""
    from connectors.flipkart import Flipkart
    fk = fk or Flipkart()
    db = store.db; ensure_v12(db)
    items = fk.get_orders(from_date, to_date); n = 0
    for it in items:
        oid = str(it.get("orderId") or it.get("order_id") or "")
        if not oid: continue
        price = float(it.get("price") or it.get("sellingPrice") or 0)
        db.execute("INSERT OR IGNORE INTO order_headers VALUES (?,?,?,?,?,?,?)",
                   ("Flipkart", "default", oid, str(it.get("orderDate", ""))[:10], "imported", price, "INR"))
        db.execute("INSERT OR IGNORE INTO order_items VALUES (?,?,?,?,?,?,?,?,?)",
                   ("Flipkart", "default", oid, str(it.get("orderItemId") or it.get("order_item_id") or oid),
                    str(it.get("sku") or it.get("skuId") or ""), str(it.get("fsn") or ""),
                    float(it.get("quantity") or 1), price, 0))
        n += 1
    listings = fk.get_listings()
    for l in listings:
        sku = str(l.get("skuId") or l.get("sku") or "")
        if not sku: continue
        db.execute("INSERT OR REPLACE INTO products VALUES (?,?, 'Flipkart', ?, 0, 0, 0, 'Flipkart API')",
                   (sku, str(l.get("title") or l.get("productTitle") or sku), float(l.get("sellingPrice") or l.get("mrp") or 0)))
    db.commit()
    return {"orders_items": n, "listings": len(listings),
            "note": "Flipkart sync ho gaya; ads ke liye CSV/report rasta hi hai (write API uplabdh nahi)"}

def main():
    ap = argparse.ArgumentParser(description="NutriScale Sync Service V2")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--csv-search-terms"); ap.add_argument("--csv-campaigns")
    ap.add_argument("--csv-orders"); ap.add_argument("--csv-inventory")
    ap.add_argument("--platform", default="Amazon")
    ap.add_argument("--connector"); ap.add_argument("--orders-since", default="2026-09-01T00:00:00Z")
    ap.add_argument("--start", default="2026-10-01"); ap.add_argument("--end", default="2026-10-07")
    ap.add_argument("--from", dest="from_date", default="2026-10-01"); ap.add_argument("--to", dest="to_date", default="2026-10-07")
    a = ap.parse_args()
    if a.status:
        for name, s in cfg.status_all().items():
            print(f"{name}: {'✔ CONFIGURED' if s['configured'] else '✘ baki hai — missing: ' + ', '.join(s['missing'])}")
        return
    store = Store()
    try:
        if a.csv_orders:
            from import_wizard import commit_import
            print(commit_import(store, a.csv_orders, kind="orders", platform=a.platform))
        if a.csv_search_terms:
            from import_wizard import commit_import
            print(commit_import(store, a.csv_search_terms, kind="search_terms", platform=a.platform))
        if a.csv_campaigns:
            from import_wizard import commit_import
            print(commit_import(store, a.csv_campaigns, kind="campaigns", platform=a.platform))
        if a.csv_inventory:
            from import_wizard import commit_import
            print(commit_import(store, a.csv_inventory, kind="inventory", platform=a.platform))
        if a.connector == "amazon_sp":
            print(sync_amazon_orders(store, a.orders_since))
        elif a.connector == "amazon_fees":
            print(sync_order_fees(store))
        elif a.connector == "amazon_ads_terms":
            from connectors.amazon_ads import AmazonAds
            print(AmazonAds().sync_search_terms(store, a.start, a.end))
        elif a.connector == "amazon_ads":
            from connectors.amazon_ads import AmazonAds
            camps = AmazonAds().list_campaigns()
            for c in camps: store.upsert_campaign(c.get("name", ""), "Amazon", 0, 0, source="Ads API")
            print(f"Amazon Ads se campaigns sync hue: {len(camps)}")
        elif a.connector == "flipkart":
            print(sync_flipkart(store, a.from_date, a.to_date))
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
