"""Connector Config — credentials in one place, never in code.
Order: environment variables > config/connectors.json file.
To create the file: copy config/connectors.example.json to connectors.json and fill in your keys.
"""
import json, os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CONFIG_PATH = os.path.join(ROOT, "config", "connectors.json")

REQUIRED = {
    # V12/INT-01: Amazon's new rules (apps built after 2023) — SP-API does NOT need AWS keys,
    # LWA alone (client_id/secret/refresh_token) is enough. Old AWS keys in the config are ignored.
    "amazon_sp":  ["client_id", "client_secret", "refresh_token", "marketplace_id"],
    "amazon_ads": ["client_id", "client_secret", "refresh_token", "profile_id"],
    "flipkart":   ["app_id", "app_secret"],
    "unicommerce": ["tenant_url", "username", "password"],
}

class NotConfigured(Exception):
    """When credentials are missing — the system stops; it never invents data."""
    pass

def _load_file() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f: return json.load(f)
    return {}

DEFAULTS = {"amazon_sp": {"marketplace_id": "A21TJRUUN4KGV"}}  # Amazon India — public information, not a secret

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
            f"'{name}' connector is not configured. Missing: {', '.join(miss)}. "
            f"Fill these in config/connectors.json — see CONNECTORS_SETUP.md.")
    return get_section(name)

def status_all() -> dict:
    return {name: {"configured": not missing_keys(name), "missing": missing_keys(name)} for name in REQUIRED}
