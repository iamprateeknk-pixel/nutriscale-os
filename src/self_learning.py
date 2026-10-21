"""A14 Self-Learning Core — agent apne results aur web ki knowledge se roz strong banta hai.
3 hisse: (1) Knowledge Store, (2) Outcome Learner (rule confidence), (3) Agent Strength Score.
Niyam: lagatar 3 baar fail rule = auto-disable. Seekh pehle backtest, phir live.
"""
from dataclasses import dataclass, field

# ---------- 1. Knowledge Store ----------
@dataclass
class KnowledgeItem:
    lesson: str
    source: str
    reliability: float        # 0-1, source ka bharosa
    agent: str
    applied_count: int = 0
    success_count: int = 0
    @property
    def trust(self) -> float:
        """Bharosa = source reliability x asal results. Sirf padhne se nahi, parakhne se bharosa banta hai."""
        if self.applied_count == 0: return round(self.reliability * 0.5, 3)  # naya gyaan: aadha bharosa
        return round(self.reliability * 0.4 + (self.success_count / self.applied_count) * 0.6, 3)

class KnowledgeStore:
    def __init__(self): self.items: list[KnowledgeItem] = []
    def learn(self, lesson: str, source: str, reliability: float, agent: str) -> KnowledgeItem:
        k = KnowledgeItem(lesson, source, reliability, agent); self.items.append(k); return k
    def record_application(self, k: KnowledgeItem, success: bool):
        k.applied_count += 1; k.success_count += 1 if success else 0
    def best_for_agent(self, agent: str, min_trust: float = 0.5) -> list:
        return sorted([k for k in self.items if k.agent == agent and k.trust >= min_trust],
                      key=lambda k: k.trust, reverse=True)

# ---------- 2. Outcome Learner — rules apne results se seekhte hain ----------
@dataclass
class RuleStats:
    rule: str            # e.g. "BID_UP_20" — context ke saath key banti hai: "A06:BID_UP_20:Almonds"
    confidence: float = 0.5
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    enabled: bool = True

class OutcomeLearner:
    """Confidence up/down asal measured result se hota hai (7/14 din baad)."""
    def __init__(self, lr: float = 0.1): self.lr = lr; self.rules: dict[str, RuleStats] = {}
    def _get(self, key: str) -> RuleStats:
        return self.rules.setdefault(key, RuleStats(key))
    def record(self, agent: str, rule: str, context: str, success: bool) -> RuleStats:
        key = f"{agent}:{rule}:{context}"
        r = self._get(key)
        if success:
            r.wins += 1; r.consecutive_losses = 0
            r.confidence = min(0.99, r.confidence + self.lr * (1 - r.confidence))
        else:
            r.losses += 1; r.consecutive_losses += 1
            r.confidence = max(0.01, r.confidence - self.lr * 1.5 * r.confidence)
            if r.consecutive_losses >= 3: r.enabled = False   # 3 baar fail = auto-disable
        return r
    def should_use(self, agent: str, rule: str, context: str) -> bool:
        r = self.rules.get(f"{agent}:{rule}:{context}")
        return True if r is None else (r.enabled and r.confidence >= 0.25)

# ---------- 3. Agent Strength Score ----------
def strength_score(wins: int, losses: int, knowledge_count: int, days_active: int) -> dict:
    total = wins + losses
    success_rate = (wins / total) if total else 0.5
    experience = min(days_active / 90, 1.0)           # 90 din me full tajurba
    score = round((success_rate * 70 + experience * 20 + min(knowledge_count / 50, 1.0) * 10), 1)
    grade = "STRONG" if score >= 75 else "IMPROVING" if score >= 50 else "LEARNING"
    return {"strength_score": score, "success_rate_pct": round(success_rate * 100, 1), "grade": grade,
            "note": "Score har Sunday pichle Sunday se upar jana chahiye — yahi 'strong day by day' ka saboot hai"}
