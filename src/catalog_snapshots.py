"""Catalog ASIN/BSR Snapshots (V22) — apne aur bazaar ke ASINs ki samay-ke-saath tasveer.
Ab tak BSR/rank ka koi dated record nahi banta tha — trend dekhna namumkin tha.
Rasta: Catalog/BSR CSV (Seller Central / Keepa export) import → catalog_snapshots table;
har ASIN ki pehli-aakhri tasveer aur BSR badlav summary me. SP Catalog API se live pull
credentials aane par isi table me aayega — table aur hisaab wahi rahega.
Dedup: file SHA (import_batches) — ek file dobara nahi ghusegi; invent kuch nahi hoga."""
import os, sys, csv
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, sha256_file, now_utc
from brand_analytics import _num, _pick

def import_catalog_csv(db, path: str, platform: str = "Amazon", account: str = "default",
                       captured_date: str = "", imported_by: str = "catalog-import") -> dict:
    ensure_v12(db)
    h = sha256_file(path)
    dup = db.execute("SELECT id FROM import_batches WHERE platform=? AND seller_account=? AND file_sha256=? AND report_type='catalog_snapshot'",
                     (platform, account, h)).fetchone()
    if dup: return {"ok": False, "duplicate": True, "imported": 0, "note": "Ye catalog file pehle aa chuki hai — duplicate roka gaya"}
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(3000); f.seek(0)
        delim = "\t" if "\t" in sample.split("\n")[0] else ","
        rows = list(csv.DictReader(f, delimiter=delim))
    if not rows: return {"ok": False, "imported": 0, "note": "File khaali hai"}
    import datetime as _dt
    cap = captured_date or _dt.date.today().isoformat()
    batch = "cat:" + h[:16]
    n, bad = 0, 0
    for r in rows:
        asin = _pick(r, "ASIN")
        if not asin: bad += 1; continue
        bsr = _num(_pick(r, "BSR", "Sales Rank", "Best Sellers Rank"))
        db.execute("""INSERT INTO catalog_snapshots(platform,seller_account,asin,sku,title,category,bsr,price,rating,reviews,
                        captured_date,source,batch_id,imported_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (platform, account, str(asin).strip(),
                    _pick(r, "Seller SKU", "SKU"), _pick(r, "Title", "Product Title"),
                    _pick(r, "Category"), int(bsr) if bsr is not None else None,
                    _num(_pick(r, "Price")), _num(_pick(r, "Rating")), 
                    int(_num(_pick(r, "Reviews", "Ratings")) or 0) or None,
                    cap, "CSV Import", batch, now_utc()))
        n += 1
    db.execute("""INSERT OR IGNORE INTO import_batches(platform,seller_account,report_type,period_start,period_end,
                    file_sha256,rows_ok,rows_bad,imported_by,imported_at,receipt)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
               (platform, account, "catalog_snapshot", cap, cap, h, n, bad, imported_by, now_utc(),
                "catalog_snapshots table (V22)")); db.commit()
    return {"ok": True, "duplicate": False, "imported": n, "bad_rows": bad, "captured_date": cap, "batch_id": batch}

def bsr_trend(db, platform: str = "Amazon") -> dict:
    """Har ASIN ki pehli aur aakhri tasveer — BSR badlav (gira = behtar) saaf dikhega."""
    ensure_v12(db)
    out = []
    for a in db.execute("SELECT DISTINCT asin FROM catalog_snapshots WHERE platform=?", (platform,)):
        rows = db.execute("""SELECT * FROM catalog_snapshots WHERE platform=? AND asin=?
                             ORDER BY captured_date, id""", (platform, a["asin"])).fetchall()
        if not rows: continue
        f, l = dict(rows[0]), dict(rows[-1])
        out.append({"asin": a["asin"], "sku": l.get("sku"), "snapshots": len(rows),
                    "first_date": f["captured_date"], "last_date": l["captured_date"],
                    "bsr_first": f["bsr"], "bsr_last": l["bsr"],
                    "bsr_change": (l["bsr"] - f["bsr"]) if (f["bsr"] is not None and l["bsr"] is not None) else None,
                    "price_last": l["price"], "rating_last": l["rating"], "reviews_last": l["reviews"]})
    return {"available": bool(out), "asins": out,
            "note": "BSR ghatna = rank behtar. Data catalog CSV import ke baad hi aayega" if not out else "Catalog snapshots se asal trend"}
