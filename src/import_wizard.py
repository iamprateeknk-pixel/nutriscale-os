"""INT-04 CSV Wizard — every report is PREVIEWED first, then COMMITTED.
Preview: file hash, detected type, header mapping, bad-row count, duplicate or not.
Commit: import + receipt + exceptions (list of bad rows) — re-imports are blocked as duplicates.
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
    if "search query" in h: return "brand_analytics"   # V20: Brand Analytics SQP — check before search terms
    if "customer search term" in h or "search term" in h: return "search_terms"
    if "order-id" in h or "amazon-order-id" in h: return "orders"
    if "asin" in h and "impressions" in h: return "brand_analytics"   # V22: SCP (ASIN funnel) report
    if "bsr" in h or "sales rank" in h or "best sellers rank" in h: return "catalog_snapshot"   # V22
    if "campaign" in h and ("total cost" in h or "spend" in h): return "campaigns"
    if "sku" in h and ("cogs" in h or "cost" in h) and "quantity" not in h and "stock" not in h: return "costs"   # V27 cost sheet
    if "sku" in h and ("quantity" in h or "stock" in h): return "inventory"
    return "unknown"

# ---------------- V27: report dates + cost sheet ----------------
import datetime as _dt
DATE_COLUMNS = {"date", "start date", "end date", "report date", "reporting date", "day", "purchase-date",
                "purchase date", "order date", "snapshot date", "captured date", "week", "reporting range end"}
_TEXT_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y", "%d.%m.%Y")

def _parse_dates(values: list):
    """Parse one column's values. Slash/dash numeric dates are decided per column: a first part > 12 means
    DD/MM, a second part > 12 means MM/DD; if neither shows, DD/MM is assumed (the Amazon.in/Flipkart default)."""
    # drop a time part ("2026-11-01T10:00:00", "01/11/2026 10:00"), keep "01 Nov 2026" intact
    vals = [_re.sub(r"(T|\s+)\d{1,2}:\d{2}.*$", "", str(v).strip()) for v in values if str(v or "").strip()]
    out, assumed = [], False
    num = [v for v in vals if _re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{4}$", v)]
    if num:
        parts = [_re.split(r"[/-]", v) for v in num]
        if any(int(a) > 12 for a, _, _ in parts): order = "DMY"
        elif any(int(b) > 12 for _, b, _ in parts): order = "MDY"
        else: order, assumed = "DMY", True
        for a, b, y in parts:
            d, m = (int(a), int(b)) if order == "DMY" else (int(b), int(a))
            try: out.append(_dt.date(int(y), m, d))
            except ValueError: pass
    for v in vals:
        if v in num: continue
        for fmt in _TEXT_FORMATS:
            try: out.append(_dt.datetime.strptime(v, fmt).date()); break
            except ValueError: continue
    return out, assumed

def detect_period(rows: list, headers: list, today=None) -> dict:
    """The period a report really covers, read from its own date columns (not the upload date).
    Returns {} when the report carries no usable dates."""
    t = today or _dt.date.today()
    cols = [h for h in headers if str(h).strip().lower() in DATE_COLUMNS]
    found, assumed = [], False
    for c in cols:
        ds, a = _parse_dates([r.get(c) for r in rows])
        found += [d for d in ds if _dt.date(2015, 1, 1) <= d <= t + _dt.timedelta(days=1)]
        assumed = assumed or (a and bool(ds))
    if not found: return {}
    start, end = min(found), max(found)
    return {"start": start.isoformat(), "end": end.isoformat(), "age_days": (t - end).days,
            "columns": cols, "assumed_day_first": assumed}

def _num_or_none(v):
    v = str(v if v is not None else "").replace("₹", "").replace(",", "").strip()
    if v == "": return None
    try: return float(v)
    except ValueError: return "bad"

def _pick(row, *names):
    low = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    for n in names:
        if n in low and str(low[n] or "").strip() != "": return low[n]
    return None

def import_costs(db, rows: list, source: str, approved_by: str) -> dict:
    """Cost sheet: one row per SKU — sku, cogs (product cost), packaging, shipping, other, effective_from.
    Every row is validated; bad rows are listed, never guessed. A missing packaging/shipping is 0, a missing
    or non-positive product cost is an error (an unknown cost is never treated as zero)."""
    import finance as F
    ok, exceptions = [], []
    for i, r in enumerate(rows, start=2):   # row 1 is the header
        sku = str(_pick(r, "sku", "seller sku", "seller-sku", "msku") or "").strip()
        if not sku: exceptions.append({"row": i, "error": "SKU is empty"}); continue
        cogs = _num_or_none(_pick(r, "cogs", "product cost", "unit cost", "cost", "cost price", "purchase cost"))
        extras = {k: _num_or_none(_pick(r, *names)) for k, names in
                  {"packaging": ("packaging", "packing", "packing cost", "packaging cost"),
                   "shipping": ("shipping", "shipping cost", "inbound shipping", "freight", "courier"),
                   "other": ("other", "other cost", "other variable", "other_variable")}.items()}
        if cogs is None or cogs == "bad" or cogs <= 0:
            exceptions.append({"row": i, "sku": sku, "error": "Product cost (cogs) must be a number above 0"}); continue
        bad = [k for k, v in extras.items() if v == "bad" or (isinstance(v, float) and v < 0)]
        if bad: exceptions.append({"row": i, "sku": sku, "error": "Not a valid amount: " + ", ".join(bad)}); continue
        eff = str(_pick(r, "effective_from", "effective from", "date") or "").strip() or None
        if eff:
            ds, _ = _parse_dates([eff])
            if not ds: exceptions.append({"row": i, "sku": sku, "error": f"Date not understood: {eff}"}); continue
            eff = ds[0].isoformat()
        other = (extras["shipping"] or 0) + (extras["other"] or 0)
        ok.append(F.set_cost(db, sku, cogs, extras["packaging"] or 0, other, source, approved_by, effective_from=eff))
    return {"imported": len(ok), "skus": [c["sku"] for c in ok], "exceptions": exceptions}

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
    period = detect_period(rows, headers)
    return {"sha256": h, "kind": kind, "rows": len(rows), "bad_rows_est": bad, "period": period,
            "headers": headers[:12], "duplicate": bool(dup),
            "note": "Duplicate file — committing will NOT import it again" if dup else
                    ("Detected: " + kind if kind != "unknown" else "Report type not recognised — choose the kind manually")}

def commit_import(store, path: str, kind: str = None, platform: str = "Amazon",
                  account: str = "default", period: tuple = ("", ""), imported_by: str = "wizard") -> dict:
    db = store.db
    pv = preview_import(db, path, platform, account)
    kind = kind or pv["kind"]
    if pv["duplicate"] and kind != "orders":
        return {"ok": False, "duplicate": True, "receipt": pv, "exceptions": [],
                "note": "This file was already imported — duplicate blocked"}
    exceptions = []
    # V27: a report's own dates decide its period (and so its age), not the day it was uploaded
    if not (period and period[0]) and pv.get("period"):
        period = (pv["period"]["start"], pv["period"]["end"])
    if kind == "search_terms":
        res = csv_import.import_ads_search_terms(path, store, platform, period_start=period[0], period_end=period[1],
                                                 detail=True)
        n = res.get("inserted", 0); how = "legacy table: search_terms" + (f" · period {period[0]}..{period[1]}" if period[0] else "")
        if res.get("status") not in (None, "INSERTED"):
            return {"ok": False, "duplicate": False, "imported": 0, "exceptions": [], "receipt": pv,
                    "note": res.get("detail", res["status"]), "period_status": res["status"]}
    elif kind == "costs":
        rows, _ = _sniff(path)
        r = import_costs(db, rows, "cost sheet upload", imported_by)
        n, exceptions, how = r["imported"], r["exceptions"], "cost_versions (versioned costs — FIN-01)"
        if not n:
            return {"ok": False, "duplicate": False, "imported": 0, "exceptions": exceptions, "receipt": pv,
                    "note": "No valid cost rows — see the errors per row"}
    elif kind == "campaigns":
        n = csv_import.import_campaign_report(path, store, platform); how = "legacy table: campaigns (summed per campaign)"
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
        return {"ok": False, "note": "Kind not recognised — check the preview, then choose the kind", "receipt": pv}
    if not pv["duplicate"]:
        db.execute("INSERT OR IGNORE INTO import_batches(platform,seller_account,report_type,period_start,period_end,file_sha256,rows_ok,rows_bad,imported_by,imported_at,receipt) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (platform, account, kind, period[0], period[1], pv["sha256"], n, pv["bad_rows_est"], imported_by, now_utc(), how)); db.commit()
    return {"ok": True, "duplicate": pv["duplicate"], "imported": n, "exceptions": exceptions, "how": how, "receipt": pv}

# ---------------- V26: dashboard upload + path safety ----------------
import re as _re, base64 as _b64, hashlib as _hl
UPLOAD_EXT = {".csv", ".tsv", ".txt"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

def data_dir(db_path: str) -> str:
    return os.path.dirname(os.path.abspath(db_path))

def uploads_dir(db_path: str) -> str:
    d = os.path.join(data_dir(db_path), "uploads"); os.makedirs(d, exist_ok=True); return d

def allowed_path(db_path: str, path: str) -> bool:
    """API imports only accept files inside the data/ folder — previously any server path worked
    (a logged-in user could try to read other files on the server)."""
    if not path: return False
    root = os.path.realpath(data_dir(db_path))
    p = os.path.realpath(path)
    return (p == root or p.startswith(root + os.sep)) and os.path.isfile(p) and os.path.splitext(p)[1].lower() in UPLOAD_EXT

def save_upload(db_path: str, filename: str, content_b64: str) -> dict:
    """Store a report uploaded from the dashboard (base64) in data/uploads/ under a safe name."""
    base = os.path.basename(filename or "")
    ext = os.path.splitext(base)[1].lower()
    if ext not in UPLOAD_EXT:
        return {"ok": False, "error": f"Only CSV/TSV/TXT reports are accepted (got: '{ext or 'no extension'}') — for Excel use 'Save as CSV'"}
    try: raw = _b64.b64decode(content_b64 or "", validate=True)
    except Exception: return {"ok": False, "error": "Could not read the file content (invalid base64)"}
    if not raw: return {"ok": False, "error": "File is empty"}
    if len(raw) > MAX_UPLOAD_BYTES:
        return {"ok": False, "error": f"File is {len(raw)//1024//1024}MB — limit {MAX_UPLOAD_BYTES//1024//1024}MB"}
    safe = _re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:80] or "report.csv"
    sha = _hl.sha256(raw).hexdigest()
    name = f"{sha[:12]}-{safe}"
    path = os.path.join(uploads_dir(db_path), name)
    with open(path, "wb") as fh: fh.write(raw)
    return {"ok": True, "upload": name, "path": path, "bytes": len(raw), "sha256": sha}

def resolve_upload(db_path: str, name: str):
    """Only names inside data/uploads/ — no paths like '../'."""
    if not name or os.path.basename(name) != name: return None
    p = os.path.join(uploads_dir(db_path), name)
    return p if os.path.isfile(p) else None
