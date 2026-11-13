"""Brand Analytics Importer (V20) — a dedicated path for real Amazon Brand Analytics reports.
Until now this data never entered the system (audit: 'Dedicated importer not present').
Two reports are supported:
  SQP (Search Query Performance) — query-level: volume, impressions, clicks, cart-adds, purchases
       + the brand's share (Brand Count columns) — the ASIN view also includes an ASIN column.
  SCP (Search Catalog Performance) — ASIN-level funnel: impressions/clicks/cart-adds/purchases.
Dedup via import_batches SHA-256 (same rule as the wizard): a file is never imported twice.
Columns missing from the report stay NULL — nothing is invented."""
import os, sys, csv
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, sha256_file, now_utc

def _num(v):
    if v is None: return None
    s = str(v).replace(",", "").replace("%", "").strip()
    if s in ("", "-"): return None
    try: return float(s)
    except Exception: return None

def _pick(row, *names):
    low = {str(k).strip().lower(): k for k in row.keys()}
    for n in names:
        if n.lower() in low: return row[low[n.lower()]]
    for k in row.keys():
        kl = str(k).strip().lower()
        for n in names:
            if n.lower() in kl: return row[k]
    return None

def detect_type(headers: list) -> str:
    h = " ".join(headers).lower()
    if "search query" in h: return "SQP"
    if "asin" in h and ("impressions" in h or "clicks" in h): return "SCP"
    return "unknown"

def import_brand_analytics(db, path: str, platform: str = "Amazon", account: str = "default",
                           period: tuple = ("", ""), imported_by: str = "brand-analytics") -> dict:
    """CSV file into the brand_analytics table. Return: {ok, report_type, imported, duplicate}."""
    ensure_v12(db)
    h = sha256_file(path)
    dup = db.execute("SELECT id FROM import_batches WHERE platform=? AND seller_account=? AND file_sha256=? AND report_type LIKE 'brand_%'",
                     (platform, account, h)).fetchone()
    if dup: return {"ok": False, "duplicate": True, "imported": 0, "note": "This Brand Analytics file was already imported — duplicate blocked"}
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(3000); f.seek(0)
        delim = "\t" if "\t" in sample.split("\n")[0] else ","
        rows = list(csv.DictReader(f, delimiter=delim))
    if not rows: return {"ok": False, "imported": 0, "note": "File is empty"}
    rtype = detect_type(list(rows[0].keys()))
    if rtype == "unknown":
        return {"ok": False, "imported": 0, "note": "Report type not recognised — an SQP (Search Query) or SCP (ASIN) report is needed"}
    batch = "ba:" + h[:16]
    n = 0
    for r in rows:
        db.execute("""INSERT INTO brand_analytics(platform,seller_account,report_type,period_start,period_end,asin,query,
                        search_volume,impressions,brand_impressions,clicks,brand_clicks,cart_adds,brand_cart_adds,
                        purchases,brand_purchases,batch_id,imported_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (platform, account, rtype, period[0], period[1],
                    _pick(r, "ASIN"), _pick(r, "Search Query"),
                    _num(_pick(r, "Search Query Volume")),
                    _num(_pick(r, "Impressions: Total Count", "Impressions")),
                    _num(_pick(r, "Impressions: Brand Count")),
                    _num(_pick(r, "Clicks: Total Count", "Clicks")),
                    _num(_pick(r, "Clicks: Brand Count")),
                    _num(_pick(r, "Cart Adds: Total Count", "Cart Adds")),
                    _num(_pick(r, "Cart Adds: Brand Count")),
                    _num(_pick(r, "Purchases: Total Count", "Purchases")),
                    _num(_pick(r, "Purchases: Brand Count")),
                    batch, now_utc()))
        n += 1
    db.execute("""INSERT OR IGNORE INTO import_batches(platform,seller_account,report_type,period_start,period_end,
                    file_sha256,rows_ok,rows_bad,imported_by,imported_at,receipt)
                  VALUES (?,?,?,?,?,?,?,0,?,?,?)""",
               (platform, account, "brand_" + rtype.lower(), period[0], period[1], h, n, imported_by, now_utc(),
                "brand_analytics table (V20)")); db.commit()
    return {"ok": True, "duplicate": False, "report_type": rtype, "imported": n, "batch_id": batch}

def import_dropfolder(db, folder: str = None, platform: str = "Amazon", account: str = "default") -> dict:
    """Scheduled automation (V22): Brand Analytics CSV files in the drop folder are imported automatically.
    The only remaining manual step is exporting SQP/SCP from Seller Central into this folder —
    folder: env NUTRISCALE_BA_INBOX or <data>/brand_analytics_inbox. Duplicate files are blocked by SHA."""
    import glob as _glob
    folder = folder or os.environ.get("NUTRISCALE_BA_INBOX") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "brand_analytics_inbox")
    if not os.path.isdir(folder):
        return {"folder": folder, "available": False, "imported_files": 0,
                "note": "Drop folder does not exist — export SQP/SCP from Seller Central and put it here: " + folder}
    results = []
    for path in sorted(_glob.glob(os.path.join(folder, "*.csv"))):
        r = import_brand_analytics(db, path, platform, account, imported_by="scheduled-dropfolder")
        results.append({"file": os.path.basename(path), "ok": r.get("ok", False),
                        "duplicate": r.get("duplicate", False), "imported": r.get("imported", 0),
                        "report_type": r.get("report_type")})
    return {"folder": folder, "available": True, "files_seen": len(results),
            "imported_files": sum(1 for x in results if x["ok"] and not x["duplicate"]),
            "rows_imported": sum(x["imported"] for x in results), "files": results}

def summary(db, platform: str = "Amazon", limit: int = 10) -> dict:
    """Top SQP queries (by purchases) with brand share + top SCP ASINs.
    Without data it says plainly 'not available' — no estimates."""
    ensure_v12(db)
    tq = db.execute("""SELECT query, MAX(search_volume) vol, SUM(impressions) imp, SUM(clicks) clk,
                              SUM(purchases) pur, SUM(brand_purchases) bpur
                       FROM brand_analytics WHERE platform=? AND report_type='SQP' AND query IS NOT NULL
                       GROUP BY query ORDER BY pur DESC LIMIT ?""", (platform, limit)).fetchall()
    ta = db.execute("""SELECT asin, SUM(impressions) imp, SUM(clicks) clk, SUM(cart_adds) ca, SUM(purchases) pur
                       FROM brand_analytics WHERE platform=? AND report_type='SCP' AND asin IS NOT NULL
                       GROUP BY asin ORDER BY pur DESC LIMIT ?""", (platform, limit)).fetchall()
    top_q = []
    for r in tq:
        pur = r["pur"] or 0
        top_q.append({"query": r["query"], "search_volume": r["vol"], "impressions": r["imp"], "clicks": r["clk"],
                      "purchases": pur, "brand_purchases": r["bpur"],
                      "brand_purchase_share_pct": round(100.0 * (r["bpur"] or 0) / pur, 1) if pur else None})
    return {"available": bool(tq or ta),
            "top_queries_by_purchases": top_q,
            "top_asins_scp": [dict(r) for r in ta],
            "note": "From real Brand Analytics reports — numbers appear only after a file is imported" if not (tq or ta) else "Real data imported from Amazon Brand Analytics (Seller Central)"}
