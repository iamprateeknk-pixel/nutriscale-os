"""INT-04 CSV Wizard — koi bhi report pehle PREVIEW, phir COMMIT.
Preview: file hash, pehchana gaya type, header-mapping, galat rows ki ginati, duplicate hai ya nahi.
Commit: import + receipt + exceptions (galat rows ki list) — reimport par duplicate block.
"""
import os, sys, csv
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, sha256_file, now_utc
from connectors import csv_import

def _sniff(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(3000); f.seek(0)
        first = sample.split("\n")[0]
        delim = "\t" if "\t" in first else ","
        rows = list(csv.DictReader(f, delimiter=delim))
        return rows, (list(rows[0].keys()) if rows else [])

def guess_kind(headers: list) -> str:
    h = " ".join(headers).lower()
    if "search query" in h: return "brand_analytics"   # V20: Brand Analytics SQP — search-terms se pehle parkho
    if "customer search term" in h or "search term" in h: return "search_terms"
    if "order-id" in h or "amazon-order-id" in h: return "orders"
    if "asin" in h and "impressions" in h: return "brand_analytics"   # V22: SCP (ASIN funnel) report
    if "bsr" in h or "sales rank" in h or "best sellers rank" in h: return "catalog_snapshot"   # V22
    if "campaign" in h and ("total cost" in h or "spend" in h): return "campaigns"
    if "sku" in h and ("quantity" in h or "stock" in h): return "inventory"
    return "unknown"

def preview_import(db, path: str, platform: str = "Amazon", account: str = "default") -> dict:
    ensure_v12(db)
    h = sha256_file(path)
    rows, headers = _sniff(path)
    kind = guess_kind(headers)
    dup = db.execute("SELECT id FROM import_batches WHERE platform=? AND seller_account=? AND file_sha256=?",
                     (platform, account, h)).fetchone()
    bad = 0
    if kind == "orders":
        bad = sum(1 for r in rows if not (r.get("order-id") or r.get("amazon-order-id")))
    return {"sha256": h, "kind": kind, "rows": len(rows), "bad_rows_est": bad,
            "headers": headers[:12], "duplicate": bool(dup),
            "note": "Duplicate file hai — commit karne par dobara import NAHI hoga" if dup else
                    ("Pehchana gaya: " + kind if kind != "unknown" else "Report ka type pehchana nahi gaya — kind haath se do")}

def commit_import(store, path: str, kind: str = None, platform: str = "Amazon",
                  account: str = "default", period: tuple = ("", ""), imported_by: str = "wizard") -> dict:
    db = store.db
    pv = preview_import(db, path, platform, account)
    kind = kind or pv["kind"]
    if pv["duplicate"] and kind != "orders":
        return {"ok": False, "duplicate": True, "receipt": pv, "exceptions": [],
                "note": "Ye file pehle aa chuki hai — duplicate roka gaya"}
    exceptions = []
    if kind == "search_terms":
        n = csv_import.import_ads_search_terms(path, store, platform); how = "legacy table: search_terms"
    elif kind == "campaigns":
        n = csv_import.import_campaign_report(path, store, platform); how = "legacy table: campaigns (campaign-wise jodkar)"
    elif kind == "orders":
        r = csv_import.import_orders_canonical(path, store, platform, account, period, imported_by)
        return {"ok": True, "duplicate": r.get("duplicate", False), "imported": r.get("rows_ok", 0),
                "exceptions": [], "how": "canonical: order_headers + order_items (line-level)", "receipt": r}
    elif kind == "brand_analytics":
        import brand_analytics as BA
        r = BA.import_brand_analytics(db, path, platform, account, period, imported_by)
        return {"ok": r.get("ok", False), "duplicate": r.get("duplicate", False), "imported": r.get("imported", 0),
                "exceptions": [], "how": "brand_analytics table (SQP/SCP — V20)", "receipt": r}
    elif kind == "catalog_snapshot":
        import catalog_snapshots as CS
        r = CS.import_catalog_csv(db, path, platform, account, captured_date=period[1] or period[0], imported_by=imported_by)
        return {"ok": r.get("ok", False), "duplicate": r.get("duplicate", False), "imported": r.get("imported", 0),
                "exceptions": [], "how": "catalog_snapshots table (ASIN/BSR — V22)", "receipt": r}
    elif kind == "inventory":
        n = csv_import.import_inventory_csv(path, store); how = "legacy table: inventory"
    else:
        return {"ok": False, "note": "Kind pehchana nahi gaya — pehle preview dekho, phir kind batao", "receipt": pv}
    if not pv["duplicate"]:
        db.execute("INSERT OR IGNORE INTO import_batches(platform,seller_account,report_type,period_start,period_end,file_sha256,rows_ok,rows_bad,imported_by,imported_at,receipt) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (platform, account, kind, period[0], period[1], pv["sha256"], n, pv["bad_rows_est"], imported_by, now_utc(), how)); db.commit()
    return {"ok": True, "duplicate": pv["duplicate"], "imported": n, "exceptions": exceptions, "how": how, "receipt": pv}

# ---------------- V26: dashboard se upload + path suraksha ----------------
import re as _re, base64 as _b64, hashlib as _hl
UPLOAD_EXT = {".csv", ".tsv", ".txt"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

def data_dir(db_path: str) -> str:
    return os.path.dirname(os.path.abspath(db_path))

def uploads_dir(db_path: str) -> str:
    d = os.path.join(data_dir(db_path), "uploads"); os.makedirs(d, exist_ok=True); return d

def allowed_path(db_path: str, path: str) -> bool:
    """API se import sirf data/ folder ke andar ki file — pehle koi bhi server path chal jaata tha
    (login wala user server ki doosri files padhne ki koshish kar sakta tha)."""
    if not path: return False
    root = os.path.realpath(data_dir(db_path))
    p = os.path.realpath(path)
    return (p == root or p.startswith(root + os.sep)) and os.path.isfile(p) and os.path.splitext(p)[1].lower() in UPLOAD_EXT

def save_upload(db_path: str, filename: str, content_b64: str) -> dict:
    """Dashboard se aayi report (base64) ko data/uploads/ me surakshit naam se rakho."""
    base = os.path.basename(filename or "")
    ext = os.path.splitext(base)[1].lower()
    if ext not in UPLOAD_EXT:
        return {"ok": False, "error": f"Sirf CSV/TSV/TXT report chalegi (mili: '{ext or 'bina extension'}') — Excel ho to 'Save as CSV' karo"}
    try: raw = _b64.b64decode(content_b64 or "", validate=True)
    except Exception: return {"ok": False, "error": "File ka content padha nahi gaya (base64 galat)"}
    if not raw: return {"ok": False, "error": "File khaali hai"}
    if len(raw) > MAX_UPLOAD_BYTES:
        return {"ok": False, "error": f"File {len(raw)//1024//1024}MB hai — seema {MAX_UPLOAD_BYTES//1024//1024}MB"}
    safe = _re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:80] or "report.csv"
    sha = _hl.sha256(raw).hexdigest()
    name = f"{sha[:12]}-{safe}"
    path = os.path.join(uploads_dir(db_path), name)
    with open(path, "wb") as fh: fh.write(raw)
    return {"ok": True, "upload": name, "path": path, "bytes": len(raw), "sha256": sha}

def resolve_upload(db_path: str, name: str):
    """Sirf data/uploads/ ke andar ka naam — '../' jaise raaste nahi."""
    if not name or os.path.basename(name) != name: return None
    p = os.path.join(uploads_dir(db_path), name)
    return p if os.path.isfile(p) else None
