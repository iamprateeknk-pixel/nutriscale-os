"""SEC-01 Auth + RBAC — stdlib PBKDF2 password, token sessions, role matrix.
Roles: Owner (sab kuch), GrowthLead (proposals/approve Tier-1), Analyst (read+draft),
AgencyViewer (sirf read, koi action nahi), Operations (imports/jobs), Developer (read + ops status).
"""
import os, sys, hashlib, secrets, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

ROLES = ["Owner", "GrowthLead", "Analyst", "AgencyViewer", "Operations", "Developer"]
# permission: kaun kya kar sakta hai
PERMS = {
    "read":            {"Owner", "GrowthLead", "Analyst", "AgencyViewer", "Operations", "Developer"},
    "propose":         {"Owner", "GrowthLead", "Analyst"},
    "approve_tier1":   {"Owner", "GrowthLead"},
    "approve_tier2":   {"Owner"},                      # Tier-2 sirf Owner, do alag pushtiyaan
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
    if role not in ROLES: return {"ok": False, "error": f"Role galat hai: {role}"}
    if len(password) < 8: return {"ok": False, "error": "Password kam se kam 8 akshar ka ho"}
    salt = secrets.token_bytes(16)
    db.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,1,?)",
               (username, _hash(password, salt), salt.hex(), role, now_utc())); db.commit()
    return {"ok": True, "username": username, "role": role}

# ---------------- TOTP MFA (SEC-01 ka baki hissa, V12.1) ----------------
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
    """Authenticator app (Google/Microsoft Authenticator) ke liye secret — ek baar dikhega, sambhal kar rakho."""
    ensure_v12(db); _ensure_totp_col(db)
    secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
    db.execute("UPDATE users SET totp_secret=? WHERE username=?", (secret, username)); db.commit()
    return {"secret": secret, "uri": f"otpauth://totp/NutriScale:{username}?secret={secret}&issuer=NutriScaleOS",
            "note": "Is secret ko authenticator app me daalo — iske baad login par 6-ank ka code bhi lagega"}

def _failed_logins(db, username: str) -> int:
    """Pichli safal login ke baad, pichle 10 minute me kitni galat koshishein (rate-limit, V12.2)."""
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
                "message": "Bohot galat koshishein — khaata 10 minute ke liye band hai (rate limit)"}
    r = db.execute("SELECT * FROM users WHERE username=? AND active=1", (username,)).fetchone()
    if not r or _hash(password, bytes.fromhex(r["salt"])) != r["pass_hash"]:
        _record_attempt(db, username, False); return None
    secret = r["totp_secret"] if "totp_secret" in r.keys() else None
    if secret:
        if not totp_code or str(totp_code) not in _totp_codes(secret):
            return {"mfa_required": True, "username": username,
                    "message": "Is khaate par MFA chalu hai — authenticator ka 6-ank code bhi do"}
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
    """Backend ke liye: (user, error_response). error None ho to aage badho."""
    auth = headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    user = user_from_token(db, token)
    if not user: return None, (401, {"error": "LOGIN_REQUIRED", "message": "Pehle login karo — bina pehchan ke koi data nahi dikhega."})
    if not can(user["role"], perm):
        return None, (403, {"error": "FORBIDDEN", "message": f"{user['role']} ko '{perm}' ki ijazat nahi hai."})
    return user, None
