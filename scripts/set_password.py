"""Password badlo — naya password terminal me chupa kar poochha jata hai (screen/chat/history me nahi aata).
Chalana:  python3 scripts/set_password.py [username]      (default: malik)
Badalne ke baad us user ke saare purane login band ho jaate hain — dobara login karna hoga.
"""
import os, sys, getpass
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
import auth

def _forget_bootstrap_password():
    """~/.nutriscale_owner me pehli baar ka password likha hota hai — badalne ke baad use mita do,
    warna file purana (galat) password dikhati rahegi. User ban chuka hai, isliye bootstrap ki zaroorat nahi."""
    f = os.path.expanduser("~/.nutriscale_owner")
    if not os.path.exists(f): return False
    lines = [l for l in open(f).read().splitlines() if not l.startswith("NUTRISCALE_OWNER_PASSWORD=")]
    with open(f, "w") as fh: fh.write("\n".join(lines) + "\n")
    os.chmod(f, 0o600)
    return True

def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "malik"
    p1 = getpass.getpass(f"'{user}' ka naya password (kam se kam 8 akshar): ")
    p2 = getpass.getpass("Dobara likho: ")
    if p1 != p2:
        print("✘ Dono password alag hain — kuch nahi badla"); sys.exit(1)
    st = Store()
    try:
        r = auth.change_password(st.db, user, p1)
    finally:
        st.close()
    if not r["ok"]:
        print("✘", r["error"]); sys.exit(1)
    print(f"✔ '{user}' ka password badal gaya; purane saare login band. Dashboard par naye password se login karo.")
    if _forget_bootstrap_password():
        print("✔ ~/.nutriscale_owner se purana password hata diya")

if __name__ == "__main__":
    main()
