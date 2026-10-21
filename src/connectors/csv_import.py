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

def import_ads_search_terms(path: str, store: Store, platform: str = "Amazon") -> int:
    """Amazon Ads Console -> Reports -> Search Term Report CSV."""
    n = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            term = _find(row, "Customer Search Term", "Search Term", "customer search term")
            if not term: continue
            store.add_search_term(str(term).strip(),
                                  str(_find(row, "Campaign Name", "Campaign") or ""),
                                  _num(_find(row, "Spend", "Cost")),
                                  _num(_find(row, "Sales", "7 Day Total Sales", "Sales14d", "Total Sales")),
                                  int(_num(_find(row, "Clicks"))),
                                  int(_num(_find(row, "Purchases", "7 Day Total Orders", "Conversions"))),
                                  source=f"{platform} Ads CSV")
            n += 1
    return n

def import_campaign_report(path: str, store: Store, platform: str = "Amazon") -> int:
    """Ads Console Campaign Report CSV -> campaigns table."""
    n = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = _find(row, "Campaign Name", "Campaign")
            if not name: continue
            store.upsert_campaign(str(name).strip(), platform,
                                  _num(_find(row, "Spend", "Cost")),
                                  _num(_find(row, "Sales", "Total Sales", "Sales14d")),
                                  int(_num(_find(row, "Clicks"))),
                                  int(_num(_find(row, "Impressions"))),
                                  source=f"{platform} Ads CSV"); n += 1
    return n

def import_sales_orders(path: str, store: Store, platform: str = "Amazon") -> int:
    """Amazon: All Orders report (tab-separated bhi chalega) / Flipkart: Orders export CSV."""
    n = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(2048); f.seek(0)
        delim = "\t" if "\t" in sample.split("\n")[0] else ","
        for row in csv.DictReader(f, delimiter=delim):
            oid = _find(row, "amazon-order-id", "Order Id", "Order ID", "order_id")
            sku = _find(row, "sku", "SKU", "Seller SKU")
            amt = _num(_find(row, "item-price", "Item Price", "Selling Price", "Amount", "price"))
            if not oid: continue
            store.add_order(str(oid).strip(), platform, str(sku or "").strip(), amt,
                            qty=int(_num(_find(row, "quantity-purchased", "Quantity", "Qty")) or 1))
            n += 1
    return n

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
