"""SEC-02 Kill Switch (server-side, DB me persist — restart se reset NAHI hota) +
SEC-03 Approval State Machine + idempotent execution (API-02 ka core).
State: DRAFT > PROPOSED > APPROVAL_PENDING > APPROVED > QUEUED > EXECUTING >
       APPLIED_VERIFIED / FAILED / CANCELLED / ROLLED_BACK
Sach ka niyam: APPLIED_VERIFIED tabhi jab vendor/manual pushti ka saboot (vendor_ref) mile —
sirf DB state badalne se kabhi 'executed' nahi likha jayega.
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
    "APPROVAL_PENDING": {"APPROVED", "CANCELLED"},
    "APPROVED": {"QUEUED", "CANCELLED"},
    "QUEUED": {"EXECUTING", "CANCELLED"},
    "EXECUTING": {"APPLIED_VERIFIED", "FAILED"},
    "FAILED": {"QUEUED", "ROLLED_BACK", "CANCELLED"},
    "APPLIED_VERIFIED": {"ROLLED_BACK"},
    "CANCELLED": set(), "ROLLED_BACK": set(),
}

def _event(db, aid, frm, to, actor, note=""):
    db.execute("INSERT INTO action_events(action_id,from_state,to_state,actor,note,at) VALUES (?,?,?,?,?,?)",
               (aid, frm, to, actor, note, now_utc()))

def create_proposal(db, kind: str, platform: str, account: str, payload: dict, tier: str,
                    created_by: str, idempotency_key: str, predicted: str = "") -> dict:
    """Idempotency: wahi key dobara aaye to wahi purana action milega — duplicate kabhi nahi banega."""
    ensure_v12(db)
    old = db.execute("SELECT * FROM action_v12 WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    if old: return {**dict(old), "duplicate": True}
    exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat()
    cur = db.execute("""INSERT INTO action_v12(idempotency_key,kind,platform,seller_account,payload,tier,state,created_by,created_at,expires_at,predicted)
                        VALUES (?,?,?,?,?,?, 'APPROVAL_PENDING',?,?,?,?)""",
                     (idempotency_key, kind, platform, account, json.dumps(payload), tier, created_by, now_utc(), exp, predicted))
    db.commit(); aid = cur.lastrowid
    _event(db, aid, "DRAFT", "APPROVAL_PENDING", created_by, "proposal bana"); db.commit()
    return {**dict(db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()), "duplicate": False}

def _move(db, aid, to, actor, note="") -> dict:
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r: return {"ok": False, "error": "Action mila nahi"}
    if to not in TRANSITIONS.get(r["state"], set()):
        return {"ok": False, "error": f"State {r['state']} se {to} jaana mumkin nahi"}
    db.execute("UPDATE action_v12 SET state=? WHERE id=?", (to, aid))
    _event(db, aid, r["state"], to, actor, note); db.commit()
    return {"ok": True, "id": aid, "state": to}

def approve(db, aid: int, user: dict) -> dict:
    """Tier-2 (DOUBLE) par DO ALAG Owner pushtiyaan lazmi; Tier-1 ek sahi-role pushti."""
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r: return {"ok": False, "error": "Action mila nahi"}
    if r["state"] != "APPROVAL_PENDING": return {"ok": False, "error": f"State {r['state']} hai, approval nahi ho sakta"}
    if datetime.datetime.now(datetime.timezone.utc).isoformat() > (r["expires_at"] or ""):
        return {"ok": False, "error": "Proposal ki miyad khatm — naya proposal banao"}
    need_perm = "approve_tier2" if r["tier"] == "DOUBLE" else "approve_tier1"
    if not auth_mod.can(user["role"], need_perm):
        return {"ok": False, "error": f"{user['role']} ko is star ki pushti ki ijazat nahi"}
    db.execute("INSERT OR IGNORE INTO action_approvals VALUES (?,?,?)", (aid, user["username"], now_utc())); db.commit()
    n = db.execute("SELECT COUNT(DISTINCT username) c FROM action_approvals WHERE action_id=?", (aid,)).fetchone()["c"]
    need = 2 if r["tier"] == "DOUBLE" else 1
    if n < need:
        _event(db, aid, "APPROVAL_PENDING", "APPROVAL_PENDING", user["username"], f"pushti {n}/{need} mili"); db.commit()
        return {"ok": True, "id": aid, "state": "APPROVAL_PENDING", "approvals": n, "needed": need,
                "note": "Ek aur ALAG Owner ki pushti chahiye"}
    res = _move(db, aid, "APPROVED", user["username"], "saari pushtiyaan mil gayi")
    res.update({"approvals": n, "needed": need}); return res

def queue_action(db, aid: int, user: dict) -> dict:
    if not writes_allowed(db): return {"ok": False, "error": "KILL_SWITCH_ON — koi write queue nahi hoga"}
    return _move(db, aid, "QUEUED", user["username"], "execution ke liye queue")

def dry_run(db, aid: int) -> dict:
    """Vendor par kuch badle bina: kya badlega, uska diff + risk. Payload hi diff ka aadhaar hai."""
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r: return {"ok": False, "error": "Action mila nahi"}
    p = json.loads(r["payload"] or "{}")
    return {"ok": True, "id": aid, "kind": r["kind"], "platform": r["platform"], "diff": p,
            "kill_switch": kill_status(db)["engaged"],
            "note": "Ye sirf purvavalokan hai — vendor par kuch nahi badla gaya."}

def execute(db, aid: int, user: dict, adapter) -> dict:
    """Adapter vendor/manual pushti deta hai. Pushti (vendor_ref) bina APPLIED_VERIFIED kabhi nahi."""
    if not writes_allowed(db): return {"ok": False, "error": "KILL_SWITCH_ON — execution roka gaya"}
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r or r["state"] != "QUEUED": return {"ok": False, "error": "Action QUEUED state me nahi hai"}
    _move(db, aid, "EXECUTING", user["username"], "execution shuru")
    try:
        res = adapter.execute(json.loads(r["payload"] or "{}"), dict(r))
    except Exception as e:
        db.execute("UPDATE action_v12 SET error=? WHERE id=?", (f"{type(e).__name__}: {e}", aid)); db.commit()
        _move(db, aid, "FAILED", user["username"], "adapter fail")
        return {"ok": False, "id": aid, "state": "FAILED", "error": str(e)}
    if res.get("vendor_ref"):
        db.execute("UPDATE action_v12 SET vendor_ref=? WHERE id=?", (res["vendor_ref"], aid)); db.commit()
        _move(db, aid, "APPLIED_VERIFIED", user["username"], f"pushti mili: {res['vendor_ref']}")
        return {"ok": True, "id": aid, "state": "APPLIED_VERIFIED", "vendor_ref": res["vendor_ref"]}
    _move(db, aid, "FAILED", user["username"], "pushti nahi mili — applied NAHI mana jayega")
    return {"ok": False, "id": aid, "state": "FAILED",
            "error": res.get("error", "Vendor/manual pushti nahi mili — action applied nahi mana gaya")}

def rollback(db, aid: int, user: dict, adapter) -> dict:
    """APPLIED_VERIFIED action ko purani halat par wapas — adapter ki pushti ke saath hi ROLLED_BACK."""
    r = db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
    if not r: return {"ok": False, "error": "Action mila nahi"}
    if r["state"] != "APPLIED_VERIFIED": return {"ok": False, "error": f"State {r['state']} hai — rollback sirf applied par"}
    if not hasattr(adapter, "rollback"):
        return {"ok": False, "error": "Is adapter me rollback ki suvidha nahi — vendor console se haath se wapas karo aur darj karo"}
    res = adapter.rollback(dict(r))
    if res.get("ok"):
        _move(db, aid, "ROLLED_BACK", user["username"], res.get("note", "rollback hua"))
        return {"ok": True, "id": aid, "state": "ROLLED_BACK", "note": res.get("note")}
    return {"ok": False, "error": res.get("error", "Rollback ki pushti nahi mili — state waisi hi rahegi")}

class ManualAdapter:
    """Jab tak live write-API certified nahi: user vendor console me khud badlav karke
    uska saboot (screenshot/ref id) deta hai, TAB pushti milti hai. Jhoothi pushti kabhi nahi."""
    name = "MANUAL"
    def __init__(self, confirmations: dict = None):
        self.confirmations = confirmations or {}   # {idempotency_key: vendor_ref}
    def execute(self, payload: dict, action: dict) -> dict:
        ref = self.confirmations.get(action["idempotency_key"])
        if ref: return {"vendor_ref": ref}
        return {"error": "Manual pushti baki hai: vendor console me badlav karke uska ref/screenshot darj karo — bina saboot ke 'applied' nahi likha jayega."}

def action_timeline(db, aid: int) -> list:
    ensure_v12(db)
    return [dict(r) for r in db.execute("SELECT * FROM action_events WHERE action_id=? ORDER BY id", (aid,))]
