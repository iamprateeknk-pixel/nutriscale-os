"""V12 Platform Core — canonical schema (DAT-01), control state (SEC-02), jobs (JOB-01) ki neev.
Purani tables ko chheda nahi gaya; ye V12 ki nayi tables ensure karta hai.
Har table me platform + seller_account — tenant galti se data mix na ho.
"""
import sqlite3, hashlib, json, datetime

V12_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  username TEXT PRIMARY KEY, pass_hash TEXT, salt TEXT, role TEXT, active INT DEFAULT 1, created_at TEXT);
CREATE TABLE IF NOT EXISTS sessions(
  token_hash TEXT PRIMARY KEY, username TEXT, expires_at TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS control_state(
  key TEXT PRIMARY KEY, value TEXT, updated_by TEXT, updated_at TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS action_v12(
  id INTEGER PRIMARY KEY AUTOINCREMENT, idempotency_key TEXT UNIQUE, kind TEXT, platform TEXT,
  seller_account TEXT, payload TEXT, diff TEXT, tier TEXT, state TEXT DEFAULT 'DRAFT',
  created_by TEXT, created_at TEXT, expires_at TEXT, predicted TEXT, vendor_ref TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS action_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, action_id INT, from_state TEXT, to_state TEXT,
  actor TEXT, note TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS action_approvals(
  action_id INT, username TEXT, at TEXT, PRIMARY KEY(action_id, username));
CREATE TABLE IF NOT EXISTS import_batches(
  id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, seller_account TEXT, report_type TEXT,
  period_start TEXT, period_end TEXT, file_sha256 TEXT, rows_ok INT, rows_bad INT, imported_by TEXT,
  imported_at TEXT, receipt TEXT, UNIQUE(platform, seller_account, file_sha256, report_type, period_start, period_end));
CREATE TABLE IF NOT EXISTS order_headers(
  platform TEXT, seller_account TEXT, external_order_id TEXT, order_date TEXT, status TEXT,
  total REAL, currency TEXT DEFAULT 'INR', PRIMARY KEY(platform, seller_account, external_order_id));
CREATE TABLE IF NOT EXISTS order_items(
  platform TEXT, seller_account TEXT, external_order_id TEXT, line_id TEXT, sku TEXT, asin TEXT,
  qty REAL, gross REAL, refund REAL DEFAULT 0, PRIMARY KEY(platform, seller_account, external_order_id, line_id));
CREATE TABLE IF NOT EXISTS settlements(
  id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, seller_account TEXT, settlement_id TEXT,
  period_start TEXT, period_end TEXT, gross REAL, fees REAL, refunds REAL, taxes REAL, net REAL, source_batch INT);
CREATE TABLE IF NOT EXISTS cost_versions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT, effective_from TEXT, cogs REAL, packaging REAL,
  other_variable REAL, source TEXT, approved_by TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS fact_registry(
  id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT, fact_type TEXT, fact_value TEXT,
  evidence_ref TEXT, verified_by TEXT, verified_at TEXT);
CREATE TABLE IF NOT EXISTS job_state(
  job TEXT PRIMARY KEY, next_run TEXT, last_run TEXT, last_status TEXT, attempts INT DEFAULT 0, locked_by TEXT, locked_at TEXT);
CREATE TABLE IF NOT EXISTS job_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT, started_at TEXT, finished_at TEXT, status TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS listing_versions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT, platform TEXT, version INT, title TEXT, bullets TEXT,
  backend_terms TEXT, status TEXT DEFAULT 'DRAFT', created_by TEXT, created_at TEXT, approved_by TEXT,
  previous_version_id INT, claim_proofs TEXT);
CREATE TABLE IF NOT EXISTS product_bom(
  parent_sku TEXT, component_sku TEXT, qty REAL, PRIMARY KEY(parent_sku, component_sku));
CREATE TABLE IF NOT EXISTS llm_usage(
  id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT, role TEXT, calls INT, est_cost REAL, prompt_hash TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS capabilities(
  platform TEXT, capability TEXT, status TEXT, reason TEXT, certified_at TEXT, PRIMARY KEY(platform, capability));
CREATE TABLE IF NOT EXISTS rank_observations(
  id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, term TEXT, sku TEXT, rank_type TEXT,
  position INT, page INT, locale TEXT, device TEXT, source TEXT, captured_at TEXT);
CREATE TABLE IF NOT EXISTS peer_products(
  id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, peer_ref TEXT, url TEXT, title TEXT,
  nut_type TEXT, grade TEXT, pack_g REAL, processing TEXT, source TEXT, added_by TEXT, added_at TEXT);
CREATE TABLE IF NOT EXISTS peer_snapshots(
  id INTEGER PRIMARY KEY AUTOINCREMENT, peer_id INT, captured_at TEXT, price REAL, mrp REAL,
  coupon REAL, rating REAL, reviews INT, image_count INT, in_stock INT, delivery_days INT,
  title TEXT, source TEXT, capture_id TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS login_attempts(
  username TEXT, at TEXT, success INT);
CREATE TABLE IF NOT EXISTS outcomes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, action_id INT, action_ref TEXT, kind TEXT, window_days INT,
  metric TEXT, before REAL, after REAL, before_val REAL, after_val REAL,
  success INT, guardrail_ok INT, executed INT, measured_at TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS order_fees(
  platform TEXT, external_order_id TEXT, sku TEXT, gross REAL, fees REAL,
  PRIMARY KEY(platform, external_order_id, sku));
CREATE TABLE IF NOT EXISTS experiments(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, sku TEXT, platform TEXT, hypothesis TEXT,
  primary_metric TEXT, intervention TEXT, baseline_note TEXT, start_date TEXT, end_date TEXT,
  status TEXT DEFAULT 'PLANNED', verdict TEXT, verdict_note TEXT, owner TEXT, contamination TEXT);
"""

def ensure_v12(db) -> None:
    db.executescript(V12_SCHEMA); db.commit()
    # V12.2: search_terms par dedup ke liye batch/period columns (purani tables par bhi)
    try:
        cols = [c[1] for c in db.execute("PRAGMA table_info(search_terms)")]
        for col in ("batch_id", "period_start", "period_end"):
            if col not in cols:
                db.execute(f"ALTER TABLE search_terms ADD COLUMN {col} TEXT")
        db.commit()
    except Exception:
        pass
    # V13: action baseline (execute ke samay ki tasveer — outcome maap ka aadhaar)
    try:
        acols = [c[1] for c in db.execute("PRAGMA table_info(action_v12)")]
        if acols and "baseline" not in acols:
            db.execute("ALTER TABLE action_v12 ADD COLUMN baseline TEXT"); db.commit()
    except Exception:
        pass
    # V13: outcomes superset — experiments (purana roop) aur outcome_engine (naya) ek hi table
    try:
        ocols = [c[1] for c in db.execute("PRAGMA table_info(outcomes)")]
        if ocols:
            for col, typ in (("action_id", "INT"), ("action_ref", "TEXT"), ("kind", "TEXT"),
                             ("before_val", "REAL"), ("after_val", "REAL"), ("success", "INT"),
                             ("guardrail_ok", "INT"), ("measured_at", "TEXT")):
                if col not in ocols:
                    db.execute(f"ALTER TABLE outcomes ADD COLUMN {col} {typ}")
            db.commit()
    except Exception:
        pass

def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
    return h.hexdigest()
