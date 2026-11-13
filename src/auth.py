"""SEC-01 Auth + RBAC — stdlib PBKDF2 password, token sessions, role matrix.
Roles: Owner (everything), GrowthLead (proposals/approve Tier-1), Analyst (read+draft),
AgencyViewer (read only, no actions), Operations (imports/jobs), Developer (read + ops status).
"""
import os, sys, hashlib, secrets, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

ROLES = ["Owner", "GrowthLead", "Analyst", "AgencyViewer", "Operations", "Developer"]
# permissions: who can do what
PERMS = {
    "read":            {"Owner", "GrowthLead", "Analyst", "AgencyViewer", "Operations", "Developer"},
    "propose":         {"Owner", "GrowthLead", "Analyst"},
    "approve_tier1":   {"Owner", "GrowthLead"},
    "approve_tier2":   {"Owner"},                      # Tier-2 Owner only, two different approvals
    "execute":         {"Owner", "GrowthLead"},
    "kill":            {"Owner"},
    "import":          {"Owner", "Operations", "GrowthLead"},
    "manage_users":    {"Owner"},
    "costs":           {"Owner", "GrowthLead"},
}

def can(role: str, perm: str) -> bool:
    return role in PERMS.get(perm, set())

def _hash(pw: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 120_000).hex()

def create_user(db, username: str, password: str, role: str) -> dict:
    ensure_v12(db)
    if role not in ROLES: return {"ok": False, "error": f"Invalid role: {role}"}
    if len(password) < 8: return {"ok": False, "error": "Password must be at least 8 characters"}
    salt = secrets.token_bytes(16)
    # Named columns: the MFA migration adds totp_secret, so a positional insert breaks on such databases
    db.execute("INSERT OR REPLACE INTO users(username, pass_hash, salt, role, active, created_at) VALUES (?,?,?,?,1,?)",
               (username, _hash(password, salt), salt.hex(), role, now_utc())); db.commit()
    return {"ok": True, "username": username, "role": role}

def change_password(db, username: str, new_password: str) -> dict:
    """New salt + hash; all existing login sessions are revoked (old tokens stop working)."""
    ensure_v12(db)
    if len(new_password) < 8: return {"ok": False, "error": "Password must be at least 8 characters"}
    if not db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        return {"ok": False, "error": f"User '{username}' not found"}
    salt = secrets.token_bytes(16)
    db.execute("UPDATE users SET pass_hash=?, salt=? WHERE username=?", (_hash(new_password, salt), salt.hex(), username))
    db.execute("DELETE FROM sessions WHERE username=?", (username,))
    db.commit()
    return {"ok": True, "username": username, "sessions_revoked": True}

# ---------------- TOTP MFA (rest of SEC-01, V12.1) ----------------
import base64, hmac, struct, time as _time

def _ensure_totp_col(db):
    cols = [c[1] for c in db.execute("PRAGMA table_info(users)")]
    if "totp_secret" not in cols:
        db.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT"); db.commit()

def _totp_codes(secret_b32: str) -> set:
    key = base64.b32decode(secret_b32.upper() + "=" * (-len(secret_b32) % 8))
    out = set()
    for w in (-1, 0, 1):
        counter = int(_time.time()) // 30 + w
        h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
        o = h[-1] & 0x0F
        out.add(f"{(struct.unpack('>I', h[o:o+4])[0] & 0x7FFFFFFF) % 1000000:06d}")
    return out

def enable_totp(db, username: str) -> dict:
    """Secret for an authenticator app (Google/Microsoft Authenticator) — shown once, keep it safe."""
    ensure_v12(db); _ensure_totp_col(db)
    secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
    db.execute("UPDATE users SET totp_secret=? WHERE username=?", (secret, username)); db.commit()
    return {"secret": secret, "uri": f"otpauth://totp/NutriScale:{username}?secret={secret}&issuer=NutriScaleOS",
            "note": "Add this secret to your authenticator app — from now on login also needs the 6-digit code"}

def _failed_logins(db, username: str) -> int:
    """Failed attempts in the last 10 minutes since the last successful login (rate limit, V12.2)."""
    import datetime as _dt
    ensure_v12(db)
    cutoff = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=10)).isoformat(timespec="seconds")
    ls = db.execute("SELECT MAX(at) m FROM login_attempts WHERE username=? AND success=1", (username,)).fetchone()["m"] or ""
    r = db.execute("SELECT COUNT(*) c FROM login_attempts WHERE username=? AND success=0 AND at>? AND at>?",
                   (username, cutoff, ls)).fetchone()
    return r["c"]

def _record_attempt(db, username: str, success: bool):
    from platform_core import now_utc
    db.execute("INSERT INTO login_attempts VALUES (?,?,?)", (username, now_utc(), 1 if success else 0)); db.commit()

def verify_login(db, username: str, password: str, totp_code: str = None):
    ensure_v12(db); _ensure_totp_col(db)
    if _failed_logins(db, username) >= 5:
        return {"locked": True, "username": username,
                "message": "Too many failed attempts — the account is locked for 10 minutes (rate limit)"}
    r = db.execute("SELECT * FROM users WHERE username=? AND active=1", (username,)).fetchone()
    if not r or _hash(password, bytes.fromhex(r["salt"])) != r["pass_hash"]:
        _record_attempt(db, username, False); return None
    secret = r["totp_secret"] if "totp_secret" in r.keys() else None
    if secret:
        if not totp_code or str(totp_code) not in _totp_codes(secret):
            return {"mfa_required": True, "username": username,
                    "message": "MFA is enabled on this account — also enter the 6-digit authenticator code"}
    _record_attempt(db, username, True)
    token = secrets.token_urlsafe(32)
    exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)).isoformat()
    db.execute("INSERT INTO sessions VALUES (?,?,?,?)",
               (hashlib.sha256(token.encode()).hexdigest(), username, exp, now_utc())); db.commit()
    return {"token": token, "username": username, "role": r["role"], "expires_at": exp}

def user_from_token(db, token: str):
    if not token: return None
    ensure_v12(db)
    th = hashlib.sha256(token.encode()).hexdigest()
    r = db.execute("""SELECT u.username, u.role FROM sessions s JOIN users u ON u.username=s.username
                      WHERE s.token_hash=? AND s.expires_at>? AND u.active=1""", (th, now_utc())).fetchone()
    return dict(r) if r else None

def require(db, headers: dict, perm: str):
    """For the backend: (user, error_response). Proceed when error is None."""
    auth = headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    user = user_from_token(db, token)
    if not user: return None, (401, {"error": "LOGIN_REQUIRED", "message": "Please log in first — no data is shown without authentication."})
    if not can(user["role"], perm):
        return None, (403, {"error": "FORBIDDEN", "message": f"{user['role']} does not have '{perm}' permission."})
    return user, None
