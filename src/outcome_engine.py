"""Outcome Engine (V13) — connects self-learning to real sales.
Until now learning was half done: an action was applied, but its outcome was never measured.
Now: a BASELINE snapshot is taken at execution; the same metric is measured again after 7 and 14 days;
improvement + a guardrail (sales did not drop too much) decide success;
outcomes go into the outcomes table and rule confidence is built only from these real outcomes.
Note: the campaigns table holds current state — so taking the baseline at execution time is the only
honest method; older actions (without a baseline) are SKIPPED, never guessed.
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
    return {"spend": 0.0, "sales": 0.0, "note": "campaign snapshot not found"}

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

def _window_data(db, payload: dict, d0: str, d1: str, window_days: int = 7) -> dict:
    """REAL dated data for the [d0, d1) window — V14 window measurement, V15 adds ID resolution + a coverage gate.
    A campaign is measured only when period coverage spans >=70% of the window's days;
    a SKU only when both windows together have at least 4 order lines (otherwise INSUFFICIENT)."""
    out = {"campaign": None, "sku_revenue": None, "total_revenue": None}
    camp = payload.get("campaign") or payload.get("campaign_name")
    if not camp and payload.get("campaign_id"):
        from platform_core import campaign_name_for
        camp = campaign_name_for(db, payload.get("platform", "Amazon"), payload["campaign_id"])
    if camp:
        import datetime as _dt
        r = db.execute("""SELECT COALESCE(SUM(spend),0) sp, COALESCE(SUM(sales),0) sa, COUNT(*) n FROM search_terms
                          WHERE campaign=? AND period_start>=? AND period_end<? AND period_start<>''""",
                       (camp, d0, d1)).fetchone()
        periods = db.execute("""SELECT DISTINCT period_start, period_end FROM search_terms
                                WHERE campaign=? AND period_start>=? AND period_end<? AND period_start<>''""",
                             (camp, d0, d1)).fetchall()
        lo, hi = _dt.date.fromisoformat(d0), _dt.date.fromisoformat(d1) - _dt.timedelta(days=1)
        covered = set()
        for p in periods:
            d = _dt.date.fromisoformat(str(p["period_start"])[:10])
            e = _dt.date.fromisoformat(str(p["period_end"])[:10])
            while d <= e:
                if lo <= d <= hi: covered.add(d)
                d += _dt.timedelta(days=1)
        if camp:
            out["_campaign_coverage"] = round(100.0 * len(covered) / window_days, 1)
        if r and r["n"] and len(covered) >= 0.7 * window_days:
            out["campaign"] = {"spend": r["sp"], "sales": r["sa"]}
    sku = payload.get("sku")
    plat = payload.get("platform")
    if sku:
        # V20: SKU measurement is limited to the action's own platform — other channels' sales are not attributed to it
        r = db.execute("""SELECT COALESCE(SUM(oi.gross - COALESCE(oi.refund,0)),0) g FROM order_items oi JOIN order_headers oh
                          ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
                          WHERE oi.sku=? AND (? IS NULL OR oi.platform=?) AND oh.order_date>=? AND oh.order_date<? AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'""",
                       (sku, plat, plat, d0, d1)).fetchone()
        out["sku_revenue"] = r["g"] if r else 0.0
    t = db.execute("""SELECT COALESCE(SUM(oi.gross - COALESCE(oi.refund,0)),0) g, COUNT(*) n, COUNT(DISTINCT oh.order_date) od FROM order_items oi JOIN order_headers oh
                      ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
                      WHERE (? IS NULL OR oi.platform=?) AND oh.order_date>=? AND oh.order_date<? AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'""", (plat, plat, d0, d1)).fetchone()
    if t and t["n"]: out["total_revenue"] = t["g"]
    out["_lines"] = t["n"] if t else 0
    out["_order_days"] = t["od"] if t else 0
    out["_order_day_coverage"] = round(100.0 * (t["od"] if t else 0) / window_days, 1)
    return out

def _min_order_days(window_days: int) -> int:
    """Minimum order-days per window for VERIFIED (V21 threshold)."""
    import math
    return max(2, math.ceil(0.25 * window_days))

def _contamination(db, action_id: int, payload: dict, applied, window_days: int) -> list:
    """Cross-channel / same-target contamination (V20): if ANOTHER APPLIED_VERIFIED action on the same SKU or
    campaign landed around this measurement window, the outcome cannot be attributed to a single one —
    the uplift claim stops there and no learning is drawn from it."""
    import datetime as _dt
    sku, camp = payload.get("sku"), payload.get("campaign") or payload.get("campaign_name")
    cid = payload.get("campaign_id")
    lo = (applied - _dt.timedelta(days=window_days)).isoformat()
    hi = (applied + _dt.timedelta(days=window_days)).isoformat()
    hits = []
    rows = db.execute("""SELECT a.id, a.kind, a.platform, a.payload FROM action_v12 a
                         JOIN action_events e ON e.action_id=a.id AND e.to_state='APPLIED_VERIFIED'
                         WHERE a.id<>? AND e.at>=? AND e.at<?""", (action_id, lo, hi)).fetchall()
    for o in rows:
        try: op = json.loads(o["payload"] or "{}")
        except Exception: op = {}
        same = (sku and op.get("sku") == sku) or (camp and (op.get("campaign") == camp or op.get("campaign_name") == camp)) \
               or (cid and str(op.get("campaign_id") or "") == str(cid))
        if same:
            hits.append({"action_id": o["id"], "kind": o["kind"], "platform": o["platform"],
                         "cross_channel": o["platform"] != payload.get("platform")})
    return hits

def _judge_windows(kind: str, b: dict, a: dict):
    """(metric, before, after, success, guardrail_ok) or None when there is no dated data."""
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
    """APPLIED_VERIFIED actions: [w days before applying] vs [w days after] — a real window comparison.
    Without dated data no fake outcome is created: wait up to 2x the window, then record INSUFFICIENT_DATA."""
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
        payload.setdefault("platform", r["platform"])
        for w in windows:
            if now < applied + datetime.timedelta(days=w): continue
            if db.execute("SELECT 1 FROM outcomes WHERE action_id=? AND window_days=?", (r["id"], w)).fetchone(): continue
            d = lambda dt: dt.date().isoformat()
            b = _window_data(db, payload, d(applied - datetime.timedelta(days=w)), d(applied), w)
            a = _window_data(db, payload, d(applied), d(applied + datetime.timedelta(days=w)), w)
            # V15 coverage gate: if the SKU path has very few order lines the outcome would be a guess — stop
            if not (b["campaign"] and a["campaign"]) and (b["_lines"] + a["_lines"]) < 4:
                b["sku_revenue"] = a["sku_revenue"] = None
            judged = _judge_windows(r["kind"], b, a)
            if judged is None:
                if now >= applied + datetime.timedelta(days=2 * w):
                    db.execute("INSERT INTO outcomes(action_id,kind,window_days,metric,success,measured_at,attribution) VALUES (?,?,?,'INSUFFICIENT_DATA',NULL,?,?)",
                               (r["id"], r["kind"], w, now_utc(), "INSUFFICIENT_DATA")); db.commit(); insufficient += 1
                continue
            metric, bv, av, success, guard = judged
            # V20 attribution: contamination first, then source coverage — only then VERIFIED
            contam = _contamination(db, r["id"], payload, applied, w)
            if metric == "campaign_roas_window":
                coverage = min(b.get("_campaign_coverage") or 0, a.get("_campaign_coverage") or 0)
            else:
                coverage = min(b.get("_order_day_coverage") or 0, a.get("_order_day_coverage") or 0)
            if contam:
                attribution, succ_val = "CONTAMINATED", None
            elif metric == "campaign_roas_window":
                attribution, succ_val = "VERIFIED", 1 if (success and guard) else 0   # the campaign path already requires the 70% coverage gate
            elif (b["_lines"] + a["_lines"]) >= 8 and b["_order_days"] >= _min_order_days(w) and a["_order_days"] >= _min_order_days(w):
                # V21: VERIFIED needs a real sample — >=8 order lines in total and in each window
                # at least max(2, 25% of the window) order days. 'Verified' on one day of data was a lie.
                attribution, succ_val = "VERIFIED", 1 if (success and guard) else 0
            else:
                attribution, succ_val = "LOW_COVERAGE", 1 if (success and guard) else 0
            db.execute("INSERT INTO outcomes(action_id,kind,window_days,metric,before_val,after_val,success,guardrail_ok,measured_at,attribution,coverage_pct) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (r["id"], r["kind"], w, metric, bv, av, succ_val, 1 if guard else 0, now_utc(), attribution, coverage))
            db.commit(); done += 1
    return {"measured": done, "insufficient_data": insufficient}

def rule_confidence(db) -> list:
    """Real win rate per action kind — V20: learning comes ONLY from VERIFIED outcomes.
    CONTAMINATED / LOW_COVERAGE / old outcomes without attribution are counted
    but never form a win rate — a fake uplift poisons learning."""
    ensure_v12(db)
    out = []
    for r in db.execute("""SELECT kind, COUNT(*) total,
                                  SUM(CASE WHEN attribution='VERIFIED' THEN 1 ELSE 0 END) vn,
                                  SUM(CASE WHEN attribution='VERIFIED' AND success=1 THEN 1 ELSE 0 END) vw,
                                  SUM(CASE WHEN attribution='CONTAMINATED' THEN 1 ELSE 0 END) cn
                           FROM outcomes WHERE success IS NOT NULL OR attribution='CONTAMINATED' GROUP BY kind"""):
        vn, vw = r["vn"] or 0, r["vw"] or 0
        out.append({"kind": r["kind"], "measured": vn, "wins": vw,
                    "win_rate": round(vw / vn, 2) if vn else None,
                    "total_outcomes": r["total"], "contaminated": r["cn"] or 0,
                    "verdict": "BHAROSA" if vn >= 3 and vw / vn >= 0.6 else (
                        "WEAK — stricter on new proposals" if vn >= 3 and vw / vn < 0.4 else
                        "COLLECTING DATA (only VERIFIED outcomes drive learning)")})
    return out
