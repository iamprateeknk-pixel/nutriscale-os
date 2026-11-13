"""Agent Base + LLM Provider interface.
Today agents run on the RuleProvider (the engines' math). Once an LLM API key is added
to the config, the LLMProvider plugs in — the rest of the agent code does not change.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from approval_engine import Proposal, decide_tier
from db_store import Store

class LLMNotConfigured(Exception):
    pass

class LLMError(Exception):
    pass

class LLMProvider:
    """Gateway to the LLM — OpenAI-compatible API (OpenAI/Anthropic-compatible/Gemini-compatible/local all work).
    Without a key it refuses plainly — it never fakes 'AI thinking'.
    Env: GOS_LLM_API_KEY, GOS_LLM_MODEL, GOS_LLM_BASE_URL (default https://api.openai.com/v1).
    Python stdlib only (urllib) — no extra library."""
    def __init__(self, transport=None):
        self.key = os.environ.get("GOS_LLM_API_KEY", "")
        self.model = os.environ.get("GOS_LLM_MODEL", "")
        self.base_url = os.environ.get("GOS_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self._transport = transport  # injectable for tests
    @property
    def available(self) -> bool:
        return bool(self.key and self.model)
    def _post(self, url: str, payload: dict, headers: dict) -> dict:
        if self._transport: return self._transport(url, payload, headers)
        import urllib.request, json as _json
        req = urllib.request.Request(url, data=_json.dumps(payload).encode(),
                                     headers={**headers, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=45) as resp:
            return _json.loads(resp.read().decode())
    def generate(self, prompt: str, system: str = "") -> str:
        if not self.available:
            raise LLMNotConfigured("LLM key/model not configured (env: GOS_LLM_API_KEY, GOS_LLM_MODEL). "
                                   "Until then agents run on the RuleProvider (engines) — this is deliberate.")
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        try:
            out = self._post(f"{self.base_url}/chat/completions",
                             {"model": self.model, "messages": msgs, "temperature": 0.7},
                             {"Authorization": f"Bearer {self.key}"})
            return out["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMError(f"LLM call failed ({type(e).__name__}: {e}) — agents keep running in rule mode.")

class BaseAgent:
    id = "A00"; name = "Base"
    def __init__(self, store: Store):
        self.store = store
        self.llm = LLMProvider()
    def run(self) -> list:
        raise NotImplementedError
    def file_proposal(self, action_type: str, description: str, change_pct: float = 0.0,
                      money_impact: float = 0.0, predicted: str = "") -> dict:
        """Record a proposal in the DB with its tier — Tier0 is EXECUTED_AUTO immediately, others WAITING."""
        p = Proposal(self.id, action_type, description, change_pct=change_pct, money_impact=money_impact)
        tier = decide_tier(p)
        status = "EXECUTED_AUTO" if tier.name == "AUTO" else (
            "WAITING_DOUBLE_CONFIRM" if tier.name == "DOUBLE" else "WAITING_USER_APPROVAL")
        aid = self.store.log_action(self.id, action_type, description, tier.name, status, predicted)
        return {"id": aid, "agent": self.id, "action_type": action_type, "desc": description,
                "tier": tier.name, "status": status, "predicted": predicted}
