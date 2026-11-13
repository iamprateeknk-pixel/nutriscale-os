"""Sync Service V2 — the real F1 Data Sync (fixed in V12.1).
Old gaps (caught in an audit): SP orders were loaded without SKUs, the Ads search-term
sync was missing from the CLI, and there was no Flipkart branch. Now:
  python3 src/sync_service.py --status
  python3 src/sync_service.py --csv-orders file [--platform Flipkart]   (wizard/canonical)
  python3 src/sync_service.py --csv-search-terms file.csv | --csv-campaigns file.csv | --csv-inventory file.csv
  python3 src/sync_service.py --connector amazon_sp --orders-since 2026-10-01T00:00:00Z   (orders + items, canonical)
  python3 src/sync_service.py --connector amazon_ads_terms --start 2026-10-01 --end 2026-10-07
  python3 src/sync_service.py --connector flipkart --from 2026-10-01 --to 2026-10-07      (orders + listings)
  python3 src/sync_service.py --connector unicommerce
Without credentials it refuses plainly — never a fake sync.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store
from connectors import config as cfg
from platform_core import ensure_v12, now_utc

def sync_amazon_orders(store, since: str, sp=None) -> dict:
    """SP-API orders + their items — into canonical order_headers/order_items (line-level)."""
    from connectors.amazon_sp import AmazonSP
    sp = sp or AmazonSP()
    db = store.db; ensure_v12(db)
    orders = sp.get_orders(since); n_items = 0
    for o in orders:
        oid = o.get("AmazonOrderId", "")
        total = float((o.get("OrderTotal") or {}).get("Amount", 0) or 0)
        # V15: UPSERT, not IGNORE — an order's status (Shipped->Cancelled) and amount can change
        db.execute("""INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)
                      ON CONFLICT(platform,seller_account,external_order_id)
                      DO UPDATE SET status=excluded.status, total=excluded.total""",
                   ("Amazon", "default", oid, str(o.get("PurchaseDate", ""))[:10], o.get("OrderStatus", ""), total, "INR"))
        for it in sp.get_order_items(oid):
            amt = float((it.get("ItemPrice") or {}).get("Amount", 0) or 0)
            db.execute("""INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)
                          ON CONFLICT(platform,seller_account,external_order_id,line_id)
                          DO UPDATE SET qty=excluded.qty, gross=excluded.gross""",
                       ("Amazon", "default", oid, str(it.get("OrderItemId", "")), it.get("SellerSKU", ""),
                        it.get("ASIN", ""), float(it.get("QuantityOrdered", 1) or 1), amt, 0))
            n_items += 1
    db.commit()
    return {"orders": len(orders), "items": n_items, "note": "Canonical line-level sync done"}

def sync_campaign_map(store, ads=None) -> dict:
    """Campaign ID -> name map from the Ads API (V15): outcome measurement can resolve IDs to names reliably."""
    from connectors.amazon_ads import AmazonAds
    from platform_core import map_campaign
    ads = ads or AmazonAds()
    camps = ads.list_campaigns()
    for c in camps:
        if c.get("campaignId") and c.get("name"): map_campaign(store.db, "Amazon", c["campaignId"], c["name"])
        if c.get("name"):
            # V17 fix: never CRUSH a real row's metrics with ₹0 — only insert the name when the row does not exist
            store.db.execute("""INSERT INTO campaigns(name, platform, spend, sales, clicks, impressions, source)
                                VALUES (?, 'Amazon', 0, 0, 0, 0, 'Ads API (naam-matra)')
                                ON CONFLICT(name, platform) DO NOTHING""", (c["name"],))
    store.db.commit()
    return {"campaigns": len(camps), "mapped": sum(1 for c in camps if c.get("campaignId"))}

def sync_order_fees(store, days: int = 3, sp=None) -> dict:
    """SP Finances: per-order fees for recent orders into order_fees (for the SKU-exact rate, V14 scheduled)."""
    import datetime
    from connectors.amazon_sp import AmazonSP
    import finance as F
    sp = sp or AmazonSP()
    db = store.db; ensure_v12(db)
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    # V20: fees are recorded under each order's OWN seller_account — accounts are never mixed
    rows = db.execute(
        "SELECT external_order_id, seller_account FROM order_headers WHERE platform='Amazon' AND order_date>=?",
        (cutoff,)).fetchall()
    total, refunds = 0, 0
    for row in rows:
        oid = row["external_order_id"]
        total += F.import_order_fees(db, sp.get_order_financials(oid),
                                     seller_account=row["seller_account"] or "default")["imported"]
        if hasattr(sp, "get_order_refunds"):
            refunds += F.record_refunds(db, sp.get_order_refunds(oid),
                                        seller_account=row["seller_account"] or "default")["updated_lines"]
    return {"orders_checked": len(rows), "fee_rows": total, "refund_lines": refunds,
            "note": "Fees + refunds came from SP Finances — revenue is now counted NET"}

def sync_flipkart(store, from_date: str, to_date: str, fk=None) -> dict:
    """Flipkart orders (canonical) + listings (catalog). Flipkart ads are report-only (capability registry)."""
    from connectors.flipkart import Flipkart
    fk = fk or Flipkart()
    db = store.db; ensure_v12(db)
    items = fk.get_orders(from_date, to_date); n = 0
    for it in items:
        oid = str(it.get("orderId") or it.get("order_id") or "")
        if not oid: continue
        price = float(it.get("price") or it.get("sellingPrice") or 0)
        status = str(it.get("status") or "imported")
        db.execute("""INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)
                      ON CONFLICT(platform,seller_account,external_order_id)
                      DO UPDATE SET status=excluded.status, total=excluded.total""",
                   ("Flipkart", "default", oid, str(it.get("orderDate", ""))[:10], status, price, "INR"))
        db.execute("""INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)
                      ON CONFLICT(platform,seller_account,external_order_id,line_id)
                      DO UPDATE SET qty=excluded.qty, gross=excluded.gross""",
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
            "note": "Flipkart sync done; ads only via CSV/report (no write API available)"}

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
            print(f"{name}: {'✔ CONFIGURED' if s['configured'] else '✘ not configured — missing: ' + ', '.join(s['missing'])}")
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
            print(sync_campaign_map(store))
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
            print("Unicommerce inventory synced to the DB")
        elif a.connector:
            print(f"The sync function for connector '{a.connector}' runs per CONNECTORS_SETUP.md — check --status first")
    except cfg.NotConfigured as e:
        print(f"⛔ {e}"); sys.exit(2)
    finally:
        store.close()

if __name__ == "__main__":
    main()
