"""Agent Base + LLM Provider interface.
Aaj agents RuleProvider par chalte hain (engines ka math). Kal ko LLM API key
config me daalte hi LLMProvider plug ho jayega — agent ka baki code nahi badlega.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from approval_engine import Proposal, decide_tier
from db_store import Store

class LLMNotConfigured(Exception):
    pass

class LLMProvider:
    """LLM ka darwaza. Key na ho to saaf mana karega — nakli 'AI soch' nahi banayega."""
    def __init__(self):
        self.key = os.environ.get("GOS_LLM_API_KEY", "")
        self.model = os.environ.get("GOS_LLM_MODEL", "")
    @property
    def available(self) -> bool:
        return bool(self.key and self.model)
    def generate(self, prompt: str) -> str:
        if not self.available:
            raise LLMNotConfigured("LLM key/model configured nahi (env: GOS_LLM_API_KEY, GOS_LLM_MODEL). "
                                   "Tab tak agents RuleProvider (engines) par chalte hain — ye jaan-bujh kar aisa hai.")
        raise LLMNotConfigured("LLM HTTP call Phase-2 ke agle kadam me judega; interface taiyaar hai.")

class BaseAgent:
    id = "A00"; name = "Base"
    def __init__(self, store: Store):
        self.store = store
        self.llm = LLMProvider()
    def run(self) -> list:
        raise NotImplementedError
    def file_proposal(self, action_type: str, description: str, change_pct: float = 0.0,
                      money_impact: float = 0.0, predicted: str = "") -> dict:
        """Proposal ko tier ke saath DB me darj karo — Tier0 turant EXECUTED_AUTO, baaki WAITING."""
        p = Proposal(self.id, action_type, description, change_pct=change_pct, money_impact=money_impact)
        tier = decide_tier(p)
        status = "EXECUTED_AUTO" if tier.name == "AUTO" else (
            "WAITING_DOUBLE_CONFIRM" if tier.name == "DOUBLE" else "WAITING_USER_APPROVAL")
        aid = self.store.log_action(self.id, action_type, description, tier.name, status, predicted)
        return {"id": aid, "agent": self.id, "action_type": action_type, "desc": description,
                "tier": tier.name, "status": status, "predicted": predicted}
