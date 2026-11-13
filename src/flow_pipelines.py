"""Flow Pipelines — deterministic work, no agent/LLM.
Every flow has fixed steps, runs the same way every time, and retries/alerts on failure. That is the trust.
"""

class Flow:
    """A straight pipeline runner — stops at a failing step and alerts, never guesses."""
    def __init__(self, name: str): self.name = name; self.steps = []; self.log = []
    def step(self, fn): self.steps.append(fn); return self
    def run(self, ctx: dict) -> dict:
        for i, fn in enumerate(self.steps):
            try:
                ctx = fn(ctx) or ctx; self.log.append(f"step {i+1} OK: {fn.__name__}")
            except Exception as e:
                self.log.append(f"step {i+1} FAIL: {fn.__name__}: {e}")
                return {"flow": self.name, "status": "FAILED_ESCALATE_TO_A09", "log": self.log, "ctx": ctx}
        return {"flow": self.name, "status": "DONE", "log": self.log, "ctx": ctx}

# --- F6 Retention Flow trigger (no thinking, just a calendar) ---
CONSUMPTION_DAYS = {"500g": 25, "1kg": 45, "250g": 15}   # how long a pack lasts (estimate, refined by data)
def retention_trigger(pack_size: str, days_since_purchase: int) -> dict:
    cycle = CONSUMPTION_DAYS.get(pack_size, 25)
    if days_since_purchase == cycle - 3:
        return {"send": True, "message": "Refill reminder (3 days before the pack runs out) + repeat-order coupon"}
    if days_since_purchase == cycle + 2:
        return {"send": True, "message": "Win-back: the pack has probably run out — offer a bigger-pack upgrade"}
    return {"send": False, "message": "Not time yet"}

# --- F10 Seller Health Flow (no account, no business) ---
HEALTH_LIMITS = {"odr_pct": 1.0, "cancellation_pct": 2.5, "late_dispatch_pct": 4.0}  # Amazon's well-known targets
def seller_health_check(metrics: dict) -> dict:
    alerts = []
    for k, limit in HEALTH_LIMITS.items():
        v = metrics.get(k)
        if v is None: continue
        if v >= limit: alerts.append(f"🔴 {k}: {v}% CROSSED the {limit}% limit — account at risk, act now")
        elif v >= limit * 0.8: alerts.append(f"🟠 {k}: {v}% is close to the {limit}% limit — pay attention")
    return {"healthy": not any(a.startswith("🔴") for a in alerts), "alerts": alerts or ["🟢 All health metrics are safe"]}
