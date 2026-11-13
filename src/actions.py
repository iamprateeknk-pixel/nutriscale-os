"""SEC-02 Kill Switch (server-side, persisted in the DB — NOT reset by a restart) +
SEC-03 Approval State Machine + idempotent execution (API-02 ka core).
State: DRAFT > PROPOSED > APPROVAL_PENDING > APPROVED > QUEUED > EXECUTING >
       APPLIED_VERIFIED / FAILED / CANCELLED / ROLLED_BACK
Truth rule: APPLIED_VERIFIED only with proof of vendor/manual confirmation (vendor_ref) —
changing DB state alone never marks anything 'executed'.
"""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc
import auth as auth_mod

# ---------------- Kill switch ----------------
def set_kill(db, engaged: bool, by: str, reason: str = "") -> dict:
    ensure_v12(db)
    db.execute("INSERT OR REPLACE INTO control_state VALUES ('kill_switch',?,?,?,?)",
               ("ON" if engaged else "OFF", by, now_utc(), reason)); db.commit()
    return kill_status(db)

def kill_status(db) -> dict:
    ensure_v12(db)
    r = db.execute("SELECT * FROM control_state WHERE key='kill_switch'").fetchone()
    if not r: return {"engaged": False, "since": None, "by": None, "reason": ""}
    return {"engaged": r["value"] == "ON", "since": r["updated_at"], "by": r["updated_by"], "reason": r["reason"] or ""}

def writes_allowed(db) -> bool:
    return not kill_status(db)["engaged"]

# ---------------- State machine ----------------
TRANSITIONS = {
    "DRAFT": {"PROPOSED", "CANCELLED"},
    "PROPOSED": {"APPROVAL_PENDING", "CANCELLED"},
    "APPROVAL_PENDING": {"APPROVED", "CANCELLED", "EXPIRED"},
    "APPROVED": {"QUEUED", "CANCELLED"},
    "QUEUED": {"EXECUTING", "CANCELLED"},
    "EXECUTING": {"APPLIED_VERIFIED", "FAILED"},
    "FAILED": {"QUEUED", "ROLLED_BACK", "CANCELLED"},
    "APPLIED_VERIFIED": {"ROLLED_BACK"},
    "CANCELLED": set(), "ROLLED_BACK": set(), "EXPIRED": set(),
}

def _event(db, aid, frm, to, actor, note=""):
    db.execute("INSERT INTO action_events(action_id,from_state,to_state,actor,note,at) VALUES (?,?,?,?,?,?)",
               (aid, frm, to, actor, note, now_utc()))

def create_proposal(db, kind: str, platform: str, account: str, payload: dict, tier: str,
                    created_by: str, idempotency_key: str, predicted: str = "") -> dict:
    """Idempotency: the same key returns the same existing action — a duplicate is never created."""
    ensure_v12(db)
    old = db.execute("SELECT * FROM action_v12 WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    if old: return {**dict(old), "duplicate": True}
    exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat()
    cur = db.execute("""INSERT INTO action_v12(idempotency_key,kind,platform,seller_account,payload,tier,state,created_by,created_at,expires_at,predicted)
                        VALUES (?,?,?,?,?,?, 'APPROVAL_PENDING',?,?,?,?)""",
                     (idempotency_key, kind, platform, account, json.dumps(payload), tier, created_by, now_utc(), exp, predicted))
    db.commit(); aid = cur.lastrowid
    _event(db, aid, "DRAFT", "APPROVAL_PENDING", created_by, "proposal created"); db.commit()
    return {**dict(db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()), "duplicate": False}

def _move(db, aid, to, actor, note="") -> dict:
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r: return {"ok": False, "error": "Action not found"}
    if to not in TRANSITIONS.get(r["state"], set()):
        return {"ok": False, "error": f"Cannot move from state {r['state']} to {to}"}
    db.execute("UPDATE action_v12 SET state=? WHERE id=?", (to, aid))
    _event(db, aid, r["state"], to, actor, note); db.commit()
    return {"ok": True, "id": aid, "state": to}

def expire_stale(db, now: str = None) -> dict:
    """V26: APPROVAL_PENDING proposals past their expiry (7 days) become EXPIRED — old decisions do not linger in the
    inbox, and a proposal built on old data cannot be approved by mistake. History (events) is kept."""
    ensure_v12(db)
    now = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
    ids = [r["id"] for r in db.execute("SELECT id FROM action_v12 WHERE state='APPROVAL_PENDING' AND expires_at IS NOT NULL AND expires_at<?", (now,))]
    for aid in ids: _move(db, aid, "EXPIRED", "system", "no decision within 7 days — expired")
    return {"expired": len(ids), "ids": ids}

def approve(db, aid: int, user: dict) -> dict:
    """Tier-2 (DOUBLE) requires TWO DIFFERENT Owner approvals; Tier-1 needs one approval from a permitted role."""
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r: return {"ok": False, "error": "Action not found"}
    if r["state"] != "APPROVAL_PENDING": return {"ok": False, "error": f"State is {r['state']} — cannot be approved"}
    if datetime.datetime.now(datetime.timezone.utc).isoformat() > (r["expires_at"] or ""):
        return {"ok": False, "error": "Proposal has expired — create a new one"}
    need_perm = "approve_tier2" if r["tier"] == "DOUBLE" else "approve_tier1"
    if not auth_mod.can(user["role"], need_perm):
        return {"ok": False, "error": f"{user['role']} is not allowed to approve this tier"}
    db.execute("INSERT OR IGNORE INTO action_approvals VALUES (?,?,?)", (aid, user["username"], now_utc())); db.commit()
    n = db.execute("SELECT COUNT(DISTINCT username) c FROM action_approvals WHERE action_id=?", (aid,)).fetchone()["c"]
    need = 2 if r["tier"] == "DOUBLE" else 1
    if n < need:
        _event(db, aid, "APPROVAL_PENDING", "APPROVAL_PENDING", user["username"], f"approval {n}/{need} received"); db.commit()
        return {"ok": True, "id": aid, "state": "APPROVAL_PENDING", "approvals": n, "needed": need,
                "note": "One more approval from a DIFFERENT Owner is needed"}
    res = _move(db, aid, "APPROVED", user["username"], "all approvals received")
    res.update({"approvals": n, "needed": need}); return res

def queue_action(db, aid: int, user: dict) -> dict:
    if not writes_allowed(db): return {"ok": False, "error": "KILL_SWITCH_ON — no write will be queued"}
    return _move(db, aid, "QUEUED", user["username"], "queued for execution")

def dry_run(db, aid: int) -> dict:
    """Without changing anything at the vendor: what would change, as a diff + risk. The payload is the basis of the diff."""
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r: return {"ok": False, "error": "Action not found"}
    p = json.loads(r["payload"] or "{}")
    return {"ok": True, "id": aid, "kind": r["kind"], "platform": r["platform"], "diff": p,
            "kill_switch": kill_status(db)["engaged"],
            "note": "This is only a preview — nothing was changed at the vendor."}

def execute(db, aid: int, user: dict, adapter) -> dict:
    """The adapter provides vendor/manual confirmation. Never APPLIED_VERIFIED without confirmation (vendor_ref)."""
    if not writes_allowed(db): return {"ok": False, "error": "KILL_SWITCH_ON — execution blocked"}
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r or r["state"] != "QUEUED": return {"ok": False, "error": "Action is not in QUEUED state"}
    _move(db, aid, "EXECUTING", user["username"], "execution shuru")
    try:
        res = adapter.execute(json.loads(r["payload"] or "{}"), dict(r))
    except Exception as e:
        db.execute("UPDATE action_v12 SET error=? WHERE id=?", (f"{type(e).__name__}: {e}", aid)); db.commit()
        _move(db, aid, "FAILED", user["username"], "adapter fail")
        return {"ok": False, "id": aid, "state": "FAILED", "error": str(e)}
    if res.get("vendor_ref"):
        db.execute("UPDATE action_v12 SET vendor_ref=? WHERE id=?", (res["vendor_ref"], aid)); db.commit()
        _move(db, aid, "APPLIED_VERIFIED", user["username"], f"confirmed: {res['vendor_ref']}")
        try:  # V13: snapshot of this moment (baseline) for outcome measurement
            import outcome_engine; outcome_engine.capture_baseline(db, aid)
        except Exception: pass
        return {"ok": True, "id": aid, "state": "APPLIED_VERIFIED", "vendor_ref": res["vendor_ref"]}
    _move(db, aid, "FAILED", user["username"], "no confirmation — NOT treated as applied")
    return {"ok": False, "id": aid, "state": "FAILED",
            "error": res.get("error", "No vendor/manual confirmation — the action is not treated as applied")}

def rollback(db, aid: int, user: dict, adapter) -> dict:
    """Revert an APPLIED_VERIFIED action to its previous state — ROLLED_BACK only with adapter confirmation."""
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r: return {"ok": False, "error": "Action not found"}
    if r["state"] != "APPLIED_VERIFIED": return {"ok": False, "error": f"State is {r['state']} — rollback only works on applied actions"}
    if not hasattr(adapter, "rollback"):
        return {"ok": False, "error": "This adapter cannot roll back — revert it manually in the vendor console and record it"}
    res = adapter.rollback(dict(r))
    if res.get("ok"):
        _move(db, aid, "ROLLED_BACK", user["username"], res.get("note", "rollback hua"))
        return {"ok": True, "id": aid, "state": "ROLLED_BACK", "note": res.get("note")}
    return {"ok": False, "error": res.get("error", "No rollback confirmation — the state stays as it is")}

class ManualAdapter:
    """Until the live write API is certified: the user makes the change in the vendor console and provides
    proof (screenshot/ref id) — ONLY THEN is it confirmed. Never a false confirmation."""
    name = "MANUAL"
    def __init__(self, confirmations: dict = None):
        self.confirmations = confirmations or {}   # {idempotency_key: vendor_ref}
    def execute(self, payload: dict, action: dict) -> dict:
        ref = self.confirmations.get(action["idempotency_key"])
        if ref: return {"vendor_ref": ref}
        return {"error": "Manual confirmation pending: make the change in the vendor console and record its ref/screenshot — without proof it is never marked 'applied'."}

def action_timeline(db, aid: int) -> list:
    ensure_v12(db)
    return [dict(r) for r in db.execute("SELECT * FROM action_events WHERE action_id=? ORDER BY id", (aid,))]
