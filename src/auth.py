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

def verify_login(db, username: str, password: str):
    ensure_v12(db)
    r = db.execute("SELECT * FROM users WHERE username=? AND active=1", (username,)).fetchone()
    if not r or _hash(password, bytes.fromhex(r["salt"])) != r["pass_hash"]: return None
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
