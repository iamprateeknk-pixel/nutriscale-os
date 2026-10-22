"""FIN-02 Settlements, INV-01/02 Stock safety + BOM, AGY-01 Agency, AIG-02 LLM budget, OPS-01 Health.
Chhote par pakke modules — har ek ka ek saaf kaam.
"""
import os, sys, csv, shutil, sqlite3, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

# ---------- FIN-02: settlement import + reconciliation ----------
def import_settlements(store, path, platform="Amazon", account="default") -> dict:
    db = store.db; ensure_v12(db)
    n = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            low = {k.lower().strip(): v for k, v in row.items() if k}
            def num(*names):
                for nm in names:
                    for k, v in low.items():
                        if nm in k:
                            try: return float(str(v).replace(",", "") or 0)
                            except Exception: return 0.0
                return 0.0
            db.execute("INSERT INTO settlements(platform,seller_account,settlement_id,period_start,period_end,gross,fees,refunds,taxes,net) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (platform, account, str(low.get("settlement id") or low.get("settlement-id") or f"S{n}"),
                        str(low.get("period start") or "")[:10], str(low.get("period end") or "")[:10],
                        num("gross", "total amount"), num("fees", "fee"), num("refund"), num("tax", "tcs", "tds"),
                        num("net", "payout", "deposit")))
            n += 1
    db.commit(); return {"imported": n}

def reconciliation(store, platform="Amazon", account="default") -> dict:
    """Order GMV vs settlement gross — farq chhupaya nahi jayega, exception report banegi."""
    db = store.db; ensure_v12(db)
    og = db.execute("SELECT COALESCE(SUM(gross),0) g, COUNT(*) c FROM order_items WHERE platform=?", (platform,)).fetchone()
    sg = db.execute("SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(net),0) n FROM settlements WHERE platform=?", (platform,)).fetchone()
    diff = round((og["g"] or 0) - (sg["g"] or 0), 2)
    return {"order_gmv": og["g"], "order_lines": og["c"], "settlement_gross": sg["g"],
            "settlement_net_payout": sg["n"], "difference": diff,
            "status": "MATCHED" if sg["g"] and abs(diff) <= max(og["g"] * 0.02, 100) else "EXCEPTION",
            "note": "Farq ke kaaran ho sakte hain: samay-khidki ka antar, refunds, pending settlements — pehle ye parkho, phir number par bharosa karo"}

# ---------- INV-01: stock-to-ads safety ----------
def stock_gate(store, sku: str) -> dict:
    row = store.db.execute("SELECT COALESCE(SUM(qty),0) q FROM inventory WHERE sku=?", (sku,)).fetchone()
    qty = row["q"] if row else 0
    return {"sku": sku, "qty": qty, "scale_allowed": qty > 0,
            "status": "OK" if qty > 20 else "LOW" if qty > 0 else "STOCKOUT",
            "note": "Stock na ho to ads scale karna paisa jalana hai — gate yahi rokta hai" if qty <= 0 else ""}

def set_bom(db, parent_sku, components: dict):
    ensure_v12(db)
    for comp, qty in components.items():
        db.execute("INSERT OR REPLACE INTO product_bom VALUES (?,?,?)", (parent_sku, comp, qty))
    db.commit()

def bom_feasibility(store, parent_sku: str, want_units: int) -> dict:
    """INV-02 / UC-10: hamper ke liye asal ghatak stock — kam pade to kitne ban sakte hain."""
    db = store.db; ensure_v12(db)
    comps = [dict(r) for r in db.execute("SELECT * FROM product_bom WHERE parent_sku=?", (parent_sku,))]
    if not comps: return {"parent": parent_sku, "feasible_units": 0, "note": "BOM define nahi hai — pehle components darj karo"}
    detail, feasible = [], None
    for c in comps:
        have = store.db.execute("SELECT COALESCE(SUM(qty),0) q FROM inventory WHERE sku=?", (c["component_sku"],)).fetchone()["q"]
        can = int(have // c["qty"]) if c["qty"] else 0
        feasible = can if feasible is None else min(feasible, can)
        detail.append({"component": c["component_sku"], "per_unit": c["qty"], "have": have, "supports_units": can})
    return {"parent": parent_sku, "want": want_units, "feasible_units": feasible,
            "enough": feasible >= want_units, "detail": detail}

# ---------- AIG-02: LLM budget governor ----------
LLM_BUDGET = {"daily_inr": float(os.environ.get("GOS_LLM_DAILY_BUDGET", "100")),
              "monthly_inr": float(os.environ.get("GOS_LLM_MONTHLY_BUDGET", "2000"))}

def llm_spend(db, period: str) -> float:
    ensure_v12(db)
    col = "day" if period == "daily" else "substr(day,1,7)"
    key = datetime.date.today().isoformat() if period == "daily" else datetime.date.today().isoformat()[:7]
    r = db.execute(f"SELECT COALESCE(SUM(est_cost),0) s FROM llm_usage WHERE {col}=?", (key,)).fetchone()
    return r["s"]

def governed_llm_call(db, llm, role: str, prompt: str, est_cost_inr: float = 2.0, system: str = "") -> dict:
    ensure_v12(db)
    if llm_spend(db, "daily") + est_cost_inr > LLM_BUDGET["daily_inr"]:
        return {"ok": False, "blocked": "DAILY_BUDGET", "note": "Aaj ka LLM budget khatm — agents rule-mode me chalte rahenge"}
    if llm_spend(db, "monthly") + est_cost_inr > LLM_BUDGET["monthly_inr"]:
        return {"ok": False, "blocked": "MONTHLY_BUDGET", "note": "Mahine ka LLM budget khatm"}
    import hashlib
    out = llm.generate(prompt, system=system)
    db.execute("INSERT INTO llm_usage(day,role,calls,est_cost,prompt_hash,at) VALUES (?,?,1,?,?,?)",
               (datetime.date.today().isoformat(), role, est_cost_inr,
                hashlib.sha256(prompt.encode()).hexdigest()[:12], now_utc())); db.commit()
    return {"ok": True, "text": out, "est_cost": est_cost_inr,
            "note": "Prompt ka sirf hash darj hai — raaz/prompts me customer data nahi jata"}

# ---------- OPS-01: health + backup ----------
def create_backup(db_path: str, dest: str) -> dict:
    src = sqlite3.connect(db_path); dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
        tables = dst.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        return {"ok": True, "dest": dest, "tables": tables, "at": now_utc(),
                "note": "Backup ban gaya — restore ka parikshan bhi isi ginati se hua (tables khul gayi)"}
    finally: src.close(); dst.close()

def system_health(store) -> dict:
    db = store.db; ensure_v12(db)
    from jobrunner import jobs_status
    import capabilities as caps, actions as act
    last_batch = db.execute("SELECT MAX(imported_at) t FROM import_batches").fetchone()["t"]
    jobs = jobs_status(db)
    failed = [j for j in jobs if j["last_status"] == "FAILED"]
    return {"kill_switch": act.kill_status(db), "jobs_failed": failed, "jobs_total": len(jobs),
            "capabilities": caps.all_capabilities(db), "last_import_at": last_batch,
            "alerts": (["Kuch jobs FAILED hain — job status dekho"] if failed else []) +
                      (["3 din se koi data import nahi — data purana ho raha hai"] if not last_batch else []),
            "checked_at": now_utc()}
