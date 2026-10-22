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

def _window_data(db, payload: dict, d0: str, d1: str) -> dict:
    """[d0, d1) khidki ka ASAL dated data — V14: jama-kul (accumulated) totals se tulna galat thi,
    isiliye campaign ke liye period-tagged search_terms aur SKU ke liye dated canonical orders."""
    out = {"campaign": None, "sku_revenue": None, "total_revenue": None}
    camp = payload.get("campaign") or payload.get("campaign_name")
    if camp:
        r = db.execute("""SELECT COALESCE(SUM(spend),0) sp, COALESCE(SUM(sales),0) sa, COUNT(*) n FROM search_terms
                          WHERE campaign=? AND period_start>=? AND period_end<? AND period_start<>''""",
                       (camp, d0, d1)).fetchone()
        if r and r["n"]: out["campaign"] = {"spend": r["sp"], "sales": r["sa"]}
    sku = payload.get("sku")
    if sku:
        r = db.execute("""SELECT COALESCE(SUM(oi.gross),0) g FROM order_items oi JOIN order_headers oh
                          ON oi.platform=oh.platform AND oi.external_order_id=oh.external_order_id
                          WHERE oi.sku=? AND oh.order_date>=? AND oh.order_date<?""", (sku, d0, d1)).fetchone()
        out["sku_revenue"] = r["g"] if r else 0.0
    t = db.execute("""SELECT COALESCE(SUM(oi.gross),0) g, COUNT(*) n FROM order_items oi JOIN order_headers oh
                      ON oi.platform=oh.platform AND oi.external_order_id=oh.external_order_id
                      WHERE oh.order_date>=? AND oh.order_date<?""", (d0, d1)).fetchone()
    if t and t["n"]: out["total_revenue"] = t["g"]
    return out

def _judge_windows(kind: str, b: dict, a: dict):
    """(metric, before, after, success, guardrail_ok) ya None jab dated data hi na ho."""
    if b["campaign"] and a["campaign"]:
        broas = b["campaign"]["sales"] / b["campaign"]["spend"] if b["campaign"]["spend"] else 0.0
        aroas = a["campaign"]["sales"] / a["campaign"]["spend"] if a["campaign"]["spend"] else 0.0
        guard = (a["campaign"]["sales"] >= 0.7 * b["campaign"]["sales"]) if b["campaign"]["sales"] else True
        return "campaign_roas_window", round(broas, 3), round(aroas, 3), aroas > broas, guard
    if b["sku_revenue"] is not None and a["sku_revenue"] is not None and (b["total_revenue"] is not None or a["total_revenue"] is not None):
        guard = True
        if b["total_revenue"] and a["total_revenue"] is not None:
            guard = a["total_revenue"] >= 0.75 * b["total_revenue"]
        return "sku_revenue_window", b["sku_revenue"], a["sku_revenue"], a["sku_revenue"] > b["sku_revenue"], guard
    return None

def measure_due(db, windows=(7, 14)) -> dict:
    """APPLIED_VERIFIED actions: [lagne se pehle ke w din] banam [lagne ke baad ke w din] — asal khidki-tulna.
    Dated data na mile to jhootha nateeja NAHI banta: 2x khidki tak intezaar, phir INSUFFICIENT_DATA darj."""
    ensure_v12(db)
    now = datetime.datetime.now(datetime.timezone.utc)
    done, insufficient = 0, 0
    rows = db.execute("SELECT * FROM action_v12 WHERE state='APPLIED_VERIFIED'").fetchall()
    for r in rows:
        ev = db.execute("SELECT MAX(at) at FROM action_events WHERE action_id=? AND to_state='APPLIED_VERIFIED'",
                        (r["id"],)).fetchone()
        if not ev or not ev["at"]: continue
        applied = datetime.datetime.fromisoformat(ev["at"])
        payload = json.loads(r["payload"] or "{}")
        for w in windows:
            if now < applied + datetime.timedelta(days=w): continue
            if db.execute("SELECT 1 FROM outcomes WHERE action_id=? AND window_days=?", (r["id"], w)).fetchone(): continue
            d = lambda dt: dt.date().isoformat()
            b = _window_data(db, payload, d(applied - datetime.timedelta(days=w)), d(applied))
            a = _window_data(db, payload, d(applied), d(applied + datetime.timedelta(days=w)))
            judged = _judge_windows(r["kind"], b, a)
            if judged is None:
                if now >= applied + datetime.timedelta(days=2 * w):
                    db.execute("INSERT INTO outcomes(action_id,kind,window_days,metric,success,measured_at) VALUES (?,?,?,'INSUFFICIENT_DATA',NULL,?)",
                               (r["id"], r["kind"], w, now_utc())); db.commit(); insufficient += 1
                continue
            metric, bv, av, success, guard = judged
            db.execute("INSERT INTO outcomes(action_id,kind,window_days,metric,before_val,after_val,success,guardrail_ok,measured_at) VALUES (?,?,?,?,?,?,?,?,?)",
                       (r["id"], r["kind"], w, metric, bv, av, 1 if (success and guard) else 0, 1 if guard else 0, now_utc()))
            db.commit(); done += 1
    return {"measured": done, "insufficient_data": insufficient}

def rule_confidence(db) -> list:
    """Action-kind ke hisaab se asal jeet-dar — yahi seekh hai, koi dawa nahi."""
    ensure_v12(db)
    out = []
    for r in db.execute("""SELECT kind, COUNT(*) n, SUM(success) wins FROM outcomes WHERE success IS NOT NULL GROUP BY kind"""):
        n, wins = r["n"], r["wins"] or 0
        out.append({"kind": r["kind"], "measured": n, "wins": wins,
                    "win_rate": round(wins / n, 2) if n else None,
                    "verdict": "BHAROSA" if n >= 3 and wins / n >= 0.6 else ("KAMZOR — naye proposals par sakhti" if n >= 3 and wins / n < 0.4 else "DATA JAMA HO RAHA HAI")})
    return out
