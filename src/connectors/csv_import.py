"""CSV Import — jo rasta AAJ se asal kaam karega, API manzoori ka intezaar kiye bina.
Seller Central / Ads Console / Flipkart Seller Hub se download ki hui asal reports
ko parse karke DB me bharta hai. Column ke naam dono platforms ke asal export se liye hain;
mismatch ho to flexible mapping se milata hai.
"""
import csv, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db_store import Store

def _num(v):
    try: return float(str(v).replace(",", "").replace("₹", "").replace("%", "").strip() or 0)
    except Exception: return 0.0

def _find(row: dict, *names):
    low = {k.lower().strip(): v for k, v in row.items() if k}
    for n in names:
        if n.lower() in low: return low[n.lower()]
    for k, v in low.items():
        for n in names:
            if n.lower() in k: return v
    return None

def import_ads_search_terms(path: str, store: Store, platform: str = "Amazon",
                            period_start: str = "", period_end: str = "", batch_id: str = "") -> int:
    """Amazon Ads Console -> Reports -> Search Term Report CSV.
    V12.2 dedup: (1) file ke ANDAR ek hi term+campaign ki kai rows jod kar ek banti hai;
    (2) period diya ho to usi source+period ki purani rows pehle hat ti hain — dobara import par totals double NAHI honge."""
    agg = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            term = _find(row, "Customer Search Term", "Search Term", "customer search term")
            if not term: continue
            key = (str(term).strip(), str(_find(row, "Campaign Name", "Campaign") or ""))
            a = agg.setdefault(key, [0.0, 0.0, 0, 0])
            a[0] += _num(_find(row, "Spend", "Cost"))
            a[1] += _num(_find(row, "Sales", "7 Day Total Sales", "Sales14d", "Total Sales"))
            a[2] += int(_num(_find(row, "Clicks")))
            a[3] += int(_num(_find(row, "Purchases", "7 Day Total Orders", "Conversions")))
    src = f"{platform} Ads CSV"
    def _insert():
        for (term, camp), (sp, sa, cl, pu) in agg.items():
            store.add_search_term(term, camp, sp, sa, cl, pu, source=src,
                                  batch_id=batch_id, period_start=period_start, period_end=period_end)
        return len(agg)
    if period_start:
        from connectors.periods import apply_period_rows
        res = apply_period_rows(store.db, src, period_start, period_end, _insert)
        return res.get("inserted", 0)
    return _insert()

def import_campaign_report(path: str, store: Store, platform: str = "Amazon") -> int:
    """Ads Console Campaign Report CSV -> campaigns table.
    Ek hi campaign ki kai rows ho sakti hain (alag-alag date ranges) — pehle jodkar phir bharo,
    warna aakhiri row pichli saari ko mita degi."""
    agg, n = {}, 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = _find(row, "Campaign Name", "Campaign")
            if not name: continue
            a = agg.setdefault(str(name).strip(), [0.0, 0.0, 0, 0])
            a[0] += _num(_find(row, "Spend", "Total cost", "Cost"))
            a[1] += _num(_find(row, "Sales", "Total Sales", "Sales14d"))
            a[2] += int(_num(_find(row, "Clicks")))
            a[3] += int(_num(_find(row, "Impressions"))); n += 1
    for name, (spend, sales, clicks, impr) in agg.items():
        store.upsert_campaign(name, platform, spend, sales, clicks, impr, source=f"{platform} Ads CSV")
    return n

def import_sales_orders(path: str, store: Store, platform: str = "Amazon") -> int:
    """Amazon: All Orders report (tab-separated bhi chalega) / Flipkart: Orders export CSV."""
    n = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(2048); f.seek(0)
        delim = "\t" if "\t" in sample.split("\n")[0] else ","
        for row in csv.DictReader(f, delimiter=delim):
            oid = _find(row, "order-id", "amazon-order-id", "Order Id", "Order ID", "order_id")
            sku = _find(row, "sku", "SKU", "Seller SKU")
            amt = _num(_find(row, "item-price", "Item Price", "Selling Price", "Amount", "price"))
            if not oid: continue
            store.add_order(str(oid).strip(), platform, str(sku or "").strip(), amt,
                            qty=int(_num(_find(row, "quantity-purchased", "Quantity", "Qty")) or 1))
            n += 1
    return n

def import_orders_canonical(path: str, store, platform: str = "Amazon", account: str = "default",
                            period: tuple = ("", ""), imported_by: str = "system") -> dict:
    """DAT-01: line-level canonical import + batch hash. Wahi file dobara = duplicate receipt,
    numbers nahi badlenge (QA-02). Do-item order = do line rows."""
    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from platform_core import ensure_v12, sha256_file, now_utc
    db = store.db; ensure_v12(db)
    h = sha256_file(path)
    dup = db.execute("""SELECT * FROM import_batches WHERE platform=? AND seller_account=? AND file_sha256=?
                        AND report_type='orders'""", (platform, account, h)).fetchone()
    if dup: return {"duplicate": True, "batch_id": dup["id"], "rows_ok": dup["rows_ok"],
                    "note": "Ye file pehle import ho chuki hai — duplicate roka gaya, numbers wahi rahenge"}
    n = bad = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(2048); f.seek(0)
        delim = "\t" if "\t" in sample.split("\n")[0] else ","
        for row in csv.DictReader(f, delimiter=delim):
            oid = _find(row, "order-id", "amazon-order-id", "Order Id", "Order ID", "order_id")
            line = _find(row, "order-item-id", "Item Id", "line_id") or str(n + 1)
            sku = _find(row, "sku", "SKU", "Seller SKU")
            amt = _num(_find(row, "item-price", "Item Price", "Selling Price", "Amount", "price"))
            qty = _num(_find(row, "quantity-purchased", "Quantity", "Qty")) or 1
            if not oid or not sku: bad += 1; continue
            status = str(_find(row, "order-status", "Order Status", "status") or "imported")
            db.execute("""INSERT INTO order_headers VALUES (?,?,?,?,?,?,?)
                          ON CONFLICT(platform,seller_account,external_order_id)
                          DO UPDATE SET status=excluded.status, total=excluded.total""",
                       (platform, account, str(oid).strip(), str(_find(row, "purchase-date", "Order Date") or "")[:10], status, amt, "INR"))
            db.execute("""INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?,?)
                          ON CONFLICT(platform,seller_account,external_order_id,line_id)
                          DO UPDATE SET qty=excluded.qty, gross=excluded.gross""",
                       (platform, account, str(oid).strip(), str(line).strip(), str(sku).strip(),
                        str(_find(row, "asin", "ASIN") or ""), qty, amt, 0))
            n += 1
    db.execute("INSERT INTO import_batches(platform,seller_account,report_type,period_start,period_end,file_sha256,rows_ok,rows_bad,imported_by,imported_at,receipt) VALUES (?,?, 'orders',?,?,?,?,?,?,?,?)",
               (platform, account, period[0], period[1], h, n, bad, imported_by, now_utc(), f"canonical orders import: {n} lines"))
    db.commit()
    return {"duplicate": False, "rows_ok": n, "rows_bad": bad, "sha256": h[:12],
            "note": "Line-level canonical import ho gaya (order_items me har line alag)"}


def import_inventory_csv(path: str, store: Store, location: str = "Own Warehouse") -> int:
    """Simple stock sheet: sku, quantity columns (Unicommerce export se bhi chalega)."""
    n = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sku = _find(row, "sku", "SKU", "Item SKU", "skuCode")
            qty = _find(row, "quantity", "Quantity", "inventory", "stock", "available")
            if sku:
                store.set_inventory(str(sku).strip(), location, int(_num(qty)), source="CSV Import"); n += 1
    return n
