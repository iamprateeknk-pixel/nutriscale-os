"""Flow Pipelines — deterministic kaam, koi agent/LLM nahi.
Har flow: steps fixed, har baar waisa hi chalega, fail ho to retry/alert. Yahi bharosa hai.
"""

class Flow:
    """Seedha pipeline runner — step fail ho to wahin rukega aur alert dega, andaz nahi lagayega."""
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

# --- F6 Retention Flow ka trigger (koi soch nahi, calendar hai) ---
CONSUMPTION_DAYS = {"500g": 25, "1kg": 45, "250g": 15}   # pack kitne din chalta hai (andaaz, data se sahi hoga)
def retention_trigger(pack_size: str, days_since_purchase: int) -> dict:
    cycle = CONSUMPTION_DAYS.get(pack_size, 25)
    if days_since_purchase == cycle - 3:
        return {"send": True, "message": "Refill reminder (pack khatm hone se 3 din pehle) + repeat-order coupon"}
    if days_since_purchase == cycle + 2:
        return {"send": True, "message": "Win-back: pack khatm ho gaya hoga — bada pack upgrade offer"}
    return {"send": False, "message": "Samay nahi aaya"}

# --- F10 Seller Health Flow (account hai to sab hai) ---
HEALTH_LIMITS = {"odr_pct": 1.0, "cancellation_pct": 2.5, "late_dispatch_pct": 4.0}  # Amazon ke mashhoor target
def seller_health_check(metrics: dict) -> dict:
    alerts = []
    for k, limit in HEALTH_LIMITS.items():
        v = metrics.get(k)
        if v is None: continue
        if v >= limit: alerts.append(f"🔴 {k}: {v}% limit {limit}% CROSS — account khatre me, turant action")
        elif v >= limit * 0.8: alerts.append(f"🟠 {k}: {v}% limit {limit}% ke paas hai — dhyan do")
    return {"healthy": not any(a.startswith("🔴") for a in alerts), "alerts": alerts or ["🟢 Saare health metrics safe hain"]}
