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
                       JOIN order_headers oh ON oi.platform=oh.platform AND oi.external_order_id=oh.external_order_id
                       WHERE oi.platform=? AND oh.order_date>=? AND oh.order_date<=? AND COALESCE(oh.status,'') NOT LIKE 'Cancel%'""",
                    (platform, ws, we)).fetchone()
    sw = db.execute("""SELECT COALESCE(SUM(gross),0) g, COALESCE(SUM(net),0) n FROM settlements
                       WHERE platform=? AND period_start<=? AND period_end>=?""", (platform, we, ws)).fetchone()
    terms = db.execute("SELECT COALESCE(SUM(spend),0) sp FROM search_terms WHERE period_start>=? AND period_end<=? AND period_start<>'' AND source LIKE ?",
                       (ws, we, platform + "%")).fetchone()
    wdiff = round((ow["g"] or 0) - (sw["g"] or 0), 2)
    return {"platform": platform, "window": {"from": ws, "to": we, "days": days},
            "orders_in_window": {"net_revenue": ow["g"], "lines": ow["n"]},
            "settlements_overlapping_window": {"gross": sw["g"], "net_payout": sw["n"]},
            "window_difference": wdiff,
            "window_status": "MATCHED" if sw["g"] and abs(wdiff) <= max(ow["g"] * 0.02, 100) else "EXCEPTION",
            "search_terms_spend_in_window": terms["sp"],
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
