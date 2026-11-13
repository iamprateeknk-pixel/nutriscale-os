"""Change a password — the new password is asked for hidden in the terminal (never shown on screen, in chat or in history).
Usage:  python3 scripts/set_password.py [username]      (default: malik)
After the change, all existing logins of that user are signed out — log in again.
"""
import os, sys, getpass
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
import auth

def _forget_bootstrap_password():
    """~/.nutriscale_owner holds the first-run password — remove it after a change,
    otherwise the file keeps showing the old (wrong) password. The user already exists, so the bootstrap is not needed."""
    f = os.path.expanduser("~/.nutriscale_owner")
    if not os.path.exists(f): return False
    lines = [l for l in open(f).read().splitlines() if not l.startswith("NUTRISCALE_OWNER_PASSWORD=")]
    with open(f, "w") as fh: fh.write("\n".join(lines) + "\n")
    os.chmod(f, 0o600)
    return True

def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "malik"
    p1 = getpass.getpass(f"New password for '{user}' (at least 8 characters): ")
    p2 = getpass.getpass("Type it again: ")
    if p1 != p2:
        print("✘ The passwords do not match — nothing changed"); sys.exit(1)
    st = Store()
    try:
        r = auth.change_password(st.db, user, p1)
    finally:
        st.close()
    if not r["ok"]:
        print("✘", r["error"]); sys.exit(1)
    print(f"✔ Password for '{user}' changed; all old logins signed out. Log in to the dashboard with the new password.")
    if _forget_bootstrap_password():
        print("✔ Removed the old password from ~/.nutriscale_owner")

if __name__ == "__main__":
    main()
