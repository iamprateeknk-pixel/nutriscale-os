"""Connector Config — credentials ek jagah, code me kabhi nahi.
Order: environment variables > config/connectors.json file.
File banana hai to: config/connectors.example.json ko copy karke connectors.json banao aur apni keys bharo.
"""
import json, os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CONFIG_PATH = os.path.join(ROOT, "config", "connectors.json")

REQUIRED = {
    "amazon_sp":  ["client_id", "client_secret", "refresh_token", "aws_access_key", "aws_secret_key", "marketplace_id"],
    "amazon_ads": ["client_id", "client_secret", "refresh_token", "profile_id"],
    "flipkart":   ["app_id", "app_secret"],
    "unicommerce": ["tenant_url", "username", "password"],
}

class NotConfigured(Exception):
    """Jab credentials na hon — system rukega, jhootha data nahi banayega."""
    pass

def _load_file() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f: return json.load(f)
    return {}

DEFAULTS = {"amazon_sp": {"marketplace_id": "A21TJRUUN4KGV"}}  # Amazon India — public jaankari, secret nahi

def get_section(name: str) -> dict:
    data = dict(DEFAULTS.get(name, {})); data.update(_load_file().get(name, {}))
    # env override: GOS_AMAZON_SP_CLIENT_ID type naam
    prefix = f"GOS_{name.upper()}_"
    for k in REQUIRED.get(name, []):
        v = os.environ.get(prefix + k.upper())
        if v: data[k] = v
    return data

def missing_keys(name: str) -> list:
    data = get_section(name)
    return [k for k in REQUIRED.get(name, []) if not data.get(k)]

def require(name: str) -> dict:
    miss = missing_keys(name)
    if miss:
        raise NotConfigured(
            f"'{name}' connector configured nahi hai. Missing: {', '.join(miss)}. "
            f"config/connectors.json me ye bharo — tareeka CONNECTORS_SETUP.md me hai.")
    return get_section(name)

def status_all() -> dict:
    return {name: {"configured": not missing_keys(name), "missing": missing_keys(name)} for name in REQUIRED}
