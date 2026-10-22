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
    backs = glob.glob(os.path.join(ROOT, "data", "backups", "*.db")) + glob.glob(os.path.join(ROOT, "backups", "*.db"))
    add("backup_exists", len(backs) > 0, f"{len(backs)} backup file(s)" if backs else "koi backup nahi mila — pehle backup_restore job chalao")
    add("https_pack", os.path.exists(os.path.join(ROOT, "deploy", "Caddyfile")) and
        os.path.exists(os.path.join(ROOT, "docker-compose.prod.yml")), "Caddy + prod compose maujud")
    add("llm_key", bool(os.environ.get("GOS_LLM_API_KEY")), "LLM key mili" if os.environ.get("GOS_LLM_API_KEY") else "LLM key nahi — system rules par chalega (chalega, par AI-copy band)")
    ready = all(c["ok"] for c in checks if not c["check"].startswith("llm"))
    return {"ready_for_pilot": ready, "checks": checks, "at": now_utc(),
            "note": "ready_for_pilot = sirf takneeki taiyaari; asal pilot ke liye keys + sign-off + hosting chahiye"}

def reconciliation_report(store, platform: str = "Amazon") -> dict:
    import ops_finance as OF
    import analytics as AN
    rec = OF.reconciliation(store, platform)
    totals = AN.sales_totals(store.db, platform)
    ads = store.db.execute("SELECT COALESCE(SUM(spend),0) sp, COALESCE(SUM(sales),0) sa FROM campaigns WHERE platform=?",
                           (platform,)).fetchone()
    terms = store.db.execute("SELECT COALESCE(SUM(spend),0) sp FROM search_terms WHERE period_start<>''").fetchone()
    return {"platform": platform, "orders_vs_settlements": rec,
            "sales_totals": totals, "campaigns_table": {"spend": ads["sp"], "sales": ads["sa"]},
            "search_terms_period_tagged_spend": terms["sp"],
            "verdict": "MILaan ke liye data taiyaar hai" if totals["lines"] else "Abhi canonical data nahi — pehle sync/import karo"}

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
