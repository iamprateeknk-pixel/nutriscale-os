"""Acceptance Gates Kit (V16) — bahari audit ne jo 5 live gates ginaye the, unhe chalane yogya banana.
Code-side aakhri taiyaari: keys aate hi EK command se —
  1) preflight: connectors/capabilities/owner/kill-switch/backup/HTTPS pack ki taiyaari report
  2) reconciliation: orders ↔ settlements ↔ ads ka milaan (asal numbers par)
  3) controlled drill: ek asal campaign par approve → execute → vendor-pushti → rollback, poora saboot ke saath
Drill bina 'certified' capability aur bina live=True ke KABHI asal badlav nahi karega."""
import os, sys, json, glob
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def preflight(db) -> dict:
    ensure_v12(db)
    checks = []
    def add(name, ok, detail): checks.append({"check": name, "ok": bool(ok), "detail": detail})
    try:
        from connectors import config as ccfg
        st = ccfg.status_all()
        for name, s in st.items():
            add(f"connector:{name}", s.get("configured"), s.get("detail", ""))
    except Exception as e:
        add("connector:config", False, f"config padh nahi paya: {e}")
    import capabilities as caps
    for plat, cap in (("Amazon", "write_ads"), ("Amazon", "write_listings"), ("Flipkart", "read_orders")):
        c = caps.capability(db, plat, cap)
        add(f"capability:{plat}:{cap}", c["status"] == "certified",
            f"halat={c['status']}" + (" — pilot sign-off baki hai" if c["status"] != "certified" else ""))
    owners = db.execute("SELECT COUNT(*) c FROM users WHERE role='Owner'").fetchone()["c"]
    add("owner_user", owners > 0, f"{owners} Owner khata maujud" if owners else "NUTRISCALE_OWNER_USER/PASSWORD se pehla Owner banao")
    import actions as act
    ks = act.kill_status(db)
    add("kill_switch_off", not ks["engaged"], "ON hai — drill nahi chalega" if ks["engaged"] else "band hai, theek")
    from db_store import DEFAULT_PATH
    _dd = os.path.dirname(DEFAULT_PATH)
    backs = glob.glob(os.path.join(_dd, "backups", "*.db")) + glob.glob(os.path.join(_dd, "*backup*.db"))
    add("backup_exists", len(backs) > 0, f"{len(backs)} backup file(s)" if backs else "koi backup nahi mila — backup_restore job chalao (data/backups/)")
    add("https_pack", os.path.exists(os.path.join(ROOT, "deploy", "Caddyfile")) and
        os.path.exists(os.path.join(ROOT, "docker-compose.prod.yml")), "Caddy + prod compose maujud")
    add("llm_key", bool(os.environ.get("GOS_LLM_API_KEY")), "LLM key mili" if os.environ.get("GOS_LLM_API_KEY") else "LLM key nahi — system rules par chalega (chalega, par AI-copy band)")
    ready = all(c["ok"] for c in checks if not c["check"].startswith("llm"))
    return {"ready_for_pilot": ready, "checks": checks, "at": now_utc(),
            "note": "ready_for_pilot = sirf takneeki taiyaari; asal pilot ke liye keys + sign-off + hosting chahiye"}

def finance_grade_matching(db, platform: str = "Amazon", days: int = 30) -> dict:
    """Finance-grade milaan (V18): har order alag se — canonical bikri banam Finances ki darj fees/gross.
    Har order ek shreni me: MATCHED / FEE_DATA_MISSING / AMOUNT_MISMATCH. Settlements me order-key
    hota hi nahi, isiliye order-stariya milaan Finances se hoga; settlement khidki-stariya rahega."""
    import datetime as _dt
    ensure_v12(db)
    ws = (_dt.date.today() - _dt.timedelta(days=days - 1)).isoformat()
    orders = db.execute("""SELECT oh.external_order_id oid, COALESCE(SUM(oi.gross),0) gross,
                                  COALESCE(SUM(COALESCE(oi.refund,0)),0) refund
                           FROM order_headers oh JOIN order_items oi
                             ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
                           WHERE oh.platform=? AND oh.order_date>=? AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'
                           GROUP BY oh.external_order_id""", (platform, ws)).fetchall()
    # V19 P0: milaan GROSS-se-GROSS aur REFUND-se-REFUND alag-alag — NET ko GROSS se parkhna galat tha
    matched, missing, mismatch, exceptions = 0, 0, 0, []
    for o in orders:
        f = db.execute("SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(COALESCE(refund,0)),0) rf, COUNT(*) n FROM order_fees WHERE platform=? AND external_order_id=?",
                       (platform, o["oid"])).fetchone()
        if not f["n"]:
            missing += 1; exceptions.append({"order": o["oid"], "issue": "FEE_DATA_MISSING"}); continue
        bad = []
        if abs(f["g"] - o["gross"]) > max(1.0, 0.005 * o["gross"]):
            bad.append(f"GROSS_MISMATCH orders={o['gross']} finances={f['g']}")
        if abs(f["rf"] - o["refund"]) > max(1.0, 0.005 * max(o["refund"], 1)):
            bad.append(f"REFUND_MISMATCH orders={o['refund']} finances={f['rf']}")
        if bad:
            mismatch += 1; exceptions.append({"order": o["oid"], "issue": "; ".join(bad)})
        else:
            matched += 1
    total = len(orders)
    return {"orders_checked": total, "matched": matched, "fee_data_missing": missing,
            "amount_mismatch": mismatch, "exceptions": exceptions[:50],
            "match_rate_pct": round(100.0 * matched / total, 1) if total else None,
            "basis": "gross-vs-gross + refund-vs-refund (V19)",
            "verdict": "FINANCE_GRADE_OK" if total and missing == 0 and mismatch == 0 else
                       ("DATA_APARYAPT" if total == 0 else "EXCEPTIONS_HAIN — upar ki suchi parkho")}

def reporting_completeness(db, platform: str = "Amazon", days: int = 30) -> dict:
    """Reporting sampurnata (V18): khidki ke kitne din ka data asal me maujud hai — teen taraf se."""
    import datetime as _dt
    ensure_v12(db)
    end = _dt.date.today(); start = end - _dt.timedelta(days=days - 1)
    od = db.execute("SELECT COUNT(DISTINCT order_date) c FROM order_headers WHERE platform=? AND order_date>=? AND order_date<=?",
                    (platform, start.isoformat(), end.isoformat())).fetchone()["c"]
    periods = db.execute("SELECT DISTINCT period_start, period_end FROM search_terms WHERE period_start>=? AND period_end<=? AND period_start<>'' AND source LIKE ?",
                         (start.isoformat(), end.isoformat(), platform + "%")).fetchall()
    covered = set()
    for p in periods:
        d1 = _dt.date.fromisoformat(str(p["period_start"])[:10]); d2 = _dt.date.fromisoformat(str(p["period_end"])[:10])
        while d1 <= d2:
            if start <= d1 <= end: covered.add(d1)
            d1 += _dt.timedelta(days=1)
    fee = db.execute("""SELECT COUNT(DISTINCT oh.external_order_id) tot,
                               COUNT(DISTINCT of2.external_order_id) with_fees
                        FROM order_headers oh LEFT JOIN order_fees of2
                          ON of2.platform=oh.platform AND of2.external_order_id=oh.external_order_id
                        WHERE oh.platform=? AND oh.order_date>=?""", (platform, start.isoformat())).fetchone()
    return {"window_days": days,
            "order_days_present": od, "order_days_note": "orders har din hona lazmi nahi — ye sirf maujudgi ki jaankari hai",
            "ads_period_coverage_pct": round(100.0 * len(covered) / days, 1),
            "orders_total": fee["tot"], "orders_with_fee_data": fee["with_fees"],
            "fee_coverage_pct": round(100.0 * fee["with_fees"] / fee["tot"], 1) if fee["tot"] else None}

def reconciliation_report(store, platform: str = "Amazon", days: int = 30) -> dict:
    """V17: scoped milaan — platform + a/c + ek hi samay-khidki (30 din) ke andar teeno taraf.
    Settlements ka apna period hota hai: khidki se takraane wale hi gine jayenge."""
    import datetime as _dt
    import ops_finance as OF
    import analytics as AN
    db = store.db
    end = _dt.date.today(); start = end - _dt.timedelta(days=days - 1)
    ws, we = start.isoformat(), end.isoformat()
    rec_all = OF.reconciliation(store, platform)
    ow = db.execute("""SELECT COALESCE(SUM(oi.gross - COALESCE(oi.refund,0)),0) g, COUNT(*) n FROM order_items oi
                       JOIN order_headers oh ON oi.platform=oh.platform AND oi.seller_account=oh.seller_account AND oi.external_order_id=oh.external_order_id
                       WHERE oi.platform=? AND oh.order_date>=? AND oh.order_date<=? AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'""",
                    (platform, ws, we)).fetchone()
    sw = db.execute("""SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(net),0) n FROM settlements
                       WHERE platform=? AND period_start<=? AND period_end>=?""", (platform, we, ws)).fetchone()
    # V19: overlap wale settlement ki POORI rakam khidki ki nahi hoti — din-anupaat anumaan alag se,
    # aur sthiti saaf taur par NON-FINAL (transaction-level data aane tak final milaan dawa nahi)
    _pro = db.execute("""SELECT gross, period_start, period_end FROM settlements
                         WHERE platform=? AND period_start<=? AND period_end>=?""", (platform, we, ws)).fetchall()
    _ws_d, _we_d = _dt.date.fromisoformat(ws), _dt.date.fromisoformat(we)
    prorated = 0.0
    for _s in _pro:
        try:
            ps, pe = _dt.date.fromisoformat(str(_s["period_start"])[:10]), _dt.date.fromisoformat(str(_s["period_end"])[:10])
            span = (pe - ps).days + 1; ov = (min(pe, _we_d) - max(ps, _ws_d)).days + 1
            prorated += (_s["gross"] or 0) * max(0, ov) / max(1, span)
        except Exception:
            prorated += _s["gross"] or 0
    terms = db.execute("SELECT COALESCE(SUM(spend),0) sp FROM search_terms WHERE period_start>=? AND period_end<=? AND period_start<>'' AND source LIKE ?",
                       (ws, we, platform + "%")).fetchone()
    wdiff = round((ow["g"] or 0) - (sw["g"] or 0), 2)
    return {"platform": platform, "window": {"from": ws, "to": we, "days": days},
            "orders_in_window": {"net_revenue": ow["g"], "lines": ow["n"]},
            "settlements_overlapping_window": {"gross_full": sw["g"], "net_payout": sw["n"],
                                               "gross_prorated_estimate": round(prorated, 2),
                                               "comparison_status": "NON_FINAL — settlement period khidki se bada ho sakta hai; poori rakam khidki ki nahi. Final milaan transaction-level settlement data se hoga"},
            "window_difference_full_amounts": wdiff,
            "window_status": "MATCHED" if sw["g"] and abs(wdiff) <= max(ow["g"] * 0.02, 100) else "EXCEPTION",
            "search_terms_spend_in_window": terms["sp"],
            "finance_grade_matching": finance_grade_matching(db, platform, days),
            "completeness": reporting_completeness(db, platform, days),
            "lifetime_reference": {"orders_vs_settlements_all": rec_all,
                                   "sales_totals": AN.sales_totals(db, platform)},
            "note": "Khidki ke bahar ke settlements/orders is milaan me NAHI hain — farq pehle khidki se parkho"}

def controlled_drill(db, payload: dict, actor: dict, live: bool = False, adapter=None, store=None) -> dict:
    """Audit gate #3 ka astra: approve → execute → vendor pushti → rollback — poora saboot sahit.
    live=False par sirf YOJANA banti hai (koi badlav nahi). live=True par bhi pehle:
    kill-switch band + write_ads certified — warna BLOCKED with wajah."""
    import actions as act
    steps = []
    def step(name, ok, detail): steps.append({"step": name, "ok": bool(ok), "detail": detail})
    ks = act.kill_status(db)
    if ks["engaged"]:
        step("kill_switch", False, "Kill switch ON hai — drill roka gaya")
        return {"verdict": "BLOCKED", "steps": steps}
    step("kill_switch", True, "band hai")
    if not live:
        step("plan", True, "Yojana: proposal -> Owner approve -> queue -> adapter execute (refetch pushti) -> rollback (purani halat pushti). "
                           "Asal chalane ke liye live=True + write_ads certified + asal campaign payload chahiye")
        return {"verdict": "PLAN_ONLY", "steps": steps,
                "note": "Koi badlav NAHI hua — ye sirf taiyaari ki report hai"}
    import capabilities as caps
    c = caps.capability(db, payload.get("platform", "Amazon"), "write_ads")
    if c["status"] != "certified":
        step("capability_gate", False, f"write_ads halat={c['status']} — pehle pilot sign-off se certified karo")
        return {"verdict": "BLOCKED", "steps": steps}
    step("capability_gate", True, "certified")
    if adapter is None:
        from vendor_adapters import AmazonAdsWriteAdapter
        adapter = AmazonAdsWriteAdapter(store)
    import uuid
    p = act.create_proposal(db, payload.get("kind", "PAUSE_CAMPAIGN"), payload.get("platform", "Amazon"), "pilot",
                            payload, "ONE_TAP", actor["username"], "drill-" + uuid.uuid4().hex[:12],
                            "V16 controlled drill")
    step("proposal", True, f"action #{p['id']}")
    act.approve(db, p["id"], actor); step("approve", True, actor["username"])
    act.queue_action(db, p["id"], actor); step("queue", True, "QUEUED")
    r = act.execute(db, p["id"], actor, adapter)
    step("execute+vendor_verify", r.get("state") == "APPLIED_VERIFIED", json.dumps(r, default=str)[:200])
    if r.get("state") != "APPLIED_VERIFIED":
        return {"verdict": "EXECUTE_FAILED", "action_id": p["id"], "steps": steps}
    rb = act.rollback(db, p["id"], actor, adapter)
    step("rollback+verify", rb.get("ok"), rb.get("note") or rb.get("error", ""))
    return {"verdict": "DRILL_PASS" if rb.get("ok") else "ROLLBACK_FAILED",
            "action_id": p["id"], "steps": steps,
            "note": "Campaign apni purani halat par wapas hai — ye saboot GATE-D pilot sign-off ke kaam aayega"}
