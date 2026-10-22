"""Outcome Engine (V13) — Self-learning ko asal sales se jodna.
Ab tak seekh aadhi thi: action lagta tha, par uska nateeja khud maapa nahi jata tha.
Ab: execute hote hi BASELINE tasveer banti hai; 7 aur 14 din par wahi metric dobara
maapi jati hai; behtari + guardrail (bikri zyada na giri ho) se success tay hota hai;
nateeje outcomes table me aur rule-confidence inhi asal nateejo se banti hai.
Note: campaigns table current-state rakhti hai — isiliye baseline execute ke samay lena hi
ekmatra imaandaar tareeka hai; purane actions (bina baseline) ko SKIP kiya jayega, guess nahi.
"""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

def _campaign_metrics(db, payload: dict) -> dict:
    name = payload.get("campaign") or payload.get("campaign_name")
    cid = payload.get("campaign_id")
    if name:
        r = db.execute("SELECT spend, sales FROM campaigns WHERE name=?", (name,)).fetchone()
        if r: return {"spend": r["spend"] or 0, "sales": r["sales"] or 0}
    return {"spend": 0.0, "sales": 0.0, "note": "campaign snapshot nahi mila"}

def _sku_metrics(db, payload: dict) -> dict:
    import analytics as AN
    sku = payload.get("sku")
    if not sku: return {}
    for row in AN.sku_sales(db):
        if row["sku"] == sku: return {"sku_revenue": row["revenue"] or 0, "sku_units": row["units"] or 0}
    return {"sku_revenue": 0.0, "sku_units": 0}

def snapshot(db, payload: dict) -> dict:
    m = {}
    m.update(_campaign_metrics(db, payload))
    m.update(_sku_metrics(db, payload))
    return m

def capture_baseline(db, action_id: int):
    ensure_v12(db)
    r = db.execute("SELECT payload FROM action_v12 WHERE id=?", (action_id,)).fetchone()
    if not r: return
    payload = json.loads(r["payload"] or "{}")
    db.execute("UPDATE action_v12 SET baseline=? WHERE id=?",
               (json.dumps(snapshot(db, payload)), action_id)); db.commit()

def _judge(kind: str, before: dict, after: dict):
    """(metric, before, after, success, guardrail_ok). ROAS behtar = safal; bikri 25% se zyada giri to guardrail fail."""
    b_roas = (before.get("sales", 0) / before["spend"]) if before.get("spend") else 0.0
    a_roas = (after.get("sales", 0) / after["spend"]) if after.get("spend") else 0.0
    if before.get("spend") or after.get("spend"):
        guardrail = True
        if before.get("sales"):
            guardrail = after.get("sales", 0) >= 0.75 * before["sales"]
        return "campaign_roas", round(b_roas, 3), round(a_roas, 3), (a_roas > b_roas), guardrail
    b_rev, a_rev = before.get("sku_revenue", 0), after.get("sku_revenue", 0)
    return "sku_revenue", b_rev, a_rev, (a_rev > b_rev), True

def measure_due(db, windows=(7, 14)) -> dict:
    """APPLIED_VERIFIED actions jinki khidki beet gayi — unka asal nateeja maapo."""
    ensure_v12(db)
    now = datetime.datetime.now(datetime.timezone.utc)
    done, skipped = 0, 0
    rows = db.execute("SELECT * FROM action_v12 WHERE state='APPLIED_VERIFIED'").fetchall()
    for r in rows:
        if not r["baseline"]:
            skipped += 1; continue
        try:
            applied_at = datetime.datetime.fromisoformat(
                db.execute("SELECT MAX(at) at FROM action_events WHERE action_id=? AND to_state='APPLIED_VERIFIED'",
                           (r["id"],)).fetchone()["at"])
        except Exception:
            skipped += 1; continue
        before = json.loads(r["baseline"]); payload = json.loads(r["payload"] or "{}")
        for w in windows:
            if (now - applied_at).days < w: continue
            exists = db.execute("SELECT 1 FROM outcomes WHERE action_id=? AND window_days=?", (r["id"], w)).fetchone()
            if exists: continue
            after = snapshot(db, payload)
            metric, b, a, success, guard = _judge(r["kind"], before, after)
            db.execute("INSERT OR IGNORE INTO outcomes(action_id,kind,window_days,metric,before_val,after_val,success,guardrail_ok,measured_at) VALUES (?,?,?,?,?,?,?,?,?)",
                       (r["id"], r["kind"], w, metric, b, a, 1 if (success and guard) else 0, 1 if guard else 0, now_utc()))
            db.commit(); done += 1
    return {"measured": done, "skipped_no_baseline": skipped}

def rule_confidence(db) -> list:
    """Action-kind ke hisaab se asal jeet-dar — yahi seekh hai, koi dawa nahi."""
    ensure_v12(db)
    out = []
    for r in db.execute("""SELECT kind, COUNT(*) n, SUM(success) wins FROM outcomes GROUP BY kind"""):
        n, wins = r["n"], r["wins"] or 0
        out.append({"kind": r["kind"], "measured": n, "wins": wins,
                    "win_rate": round(wins / n, 2) if n else None,
                    "verdict": "BHAROSA" if n >= 3 and wins / n >= 0.6 else ("KAMZOR — naye proposals par sakhti" if n >= 3 and wins / n < 0.4 else "DATA JAMA HO RAHA HAI")})
    return out
