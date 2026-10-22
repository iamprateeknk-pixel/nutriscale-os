"""SEC-04 ka hissa: repo me galti se ghusi hui chaabiyan pakdo.
Chalana: python3 scripts/secret_scan.py [path] — masla mile to exit code 1.
Patterns: AWS keys, private keys, lambe token-jaise strings, password= assignments.
Jhoothe alarm kam rakhne ke liye test/example shabdon wali lines chhodi jati hain."""
import os, re, sys

PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
    (r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-/+]{16,}['\"]", "hardcoded secret jaisa assignment"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"sk-[A-Za-z0-9]{24,}", "OpenAI-jaisa key"),
]
SKIP_WORDS = ("example", "placeholder", "your-", "xxxx", "test", "dummy", "namuna", "env", "getenv", "os.environ")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "data"}
SKIP_FILES = {"secret_scan.py"}

def scan(root: str) -> list:
    hits = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f in SKIP_FILES or not f.endswith((".py", ".js", ".html", ".json", ".md", ".yml", ".yaml", ".txt", ".toml", ".sh")): continue
            p = os.path.join(base, f)
            try: lines = open(p, encoding="utf-8", errors="ignore").read().splitlines()
            except Exception: continue
            for i, line in enumerate(lines, 1):
                if any(w in line.lower() for w in SKIP_WORDS): continue
                for pat, label in PATTERNS:
                    if re.search(pat, line):
                        hits.append(f"{os.path.relpath(p, root)}:{i} — {label}")
    return hits

if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..")
    hits = scan(root)
    if hits:
        print("⚠️ SECRET JAISI CHEEZEIN MILI:"); [print(" ", h) for h in hits]; sys.exit(1)
    print("✔ Secret scan saaf hai — koi chaabi repo me nahi mili")
