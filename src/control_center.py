"""Control Center — the brain behind the dashboard controls.
Every control has one owner: you. Turning agents off, changing guardrails, and most important — the KILL SWITCH.
Rule: the kill switch never asks for approval. If there is danger, stop first and talk later.
"""
from dataclasses import dataclass, field

@dataclass
class Controls:
    agents_enabled: dict = field(default_factory=lambda: {a: True for a in
        ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09"]})
    daily_spend_cap: float = 2000.0     # Rs — never more ad spend than this in one day
    min_margin_pct: float = 15.0        # no ads on SKUs with a lower margin
    max_bid_change_pct: float = 20.0    # a bigger bid change at once needs Tier-2 approval
    auto_pause_on_stockout: bool = True
    kill_switch: bool = False           # True = ALL ad spend stops, right now

    def can_run_ads(self, sku_margin_pct: float, stock: int) -> dict:
        if self.kill_switch: return {"allowed": False, "reason": "KILL SWITCH ON — all ad spend is stopped (you stopped it)"}
        if not self.agents_enabled.get("A06", True): return {"allowed": False, "reason": "A06 Ads Agent is turned off (from the Control Center)"}
        if self.auto_pause_on_stockout and stock <= 0: return {"allowed": False, "reason": "Stock zero — ads auto-pause"}
        if sku_margin_pct < self.min_margin_pct: return {"allowed": False, "reason": f"Margin {sku_margin_pct}% is below the minimum {self.min_margin_pct}% — ads lose money on this SKU"}
        return {"allowed": True, "reason": "All guardrails pass"}

    def emergency_stop(self) -> str:
        self.kill_switch = True
        return "🛑 KILL SWITCH ON — all campaigns queued for pause. No approval was asked — safety first."

    def resume(self) -> str:
        self.kill_switch = False
        return "▶️ System running again — it works within the guardrails"

    def set_guardrail(self, name: str, value) -> str:
        allowed = {"daily_spend_cap", "min_margin_pct", "max_bid_change_pct"}
        if name not in allowed: return f"Unknown control: {name}"
        if name == "daily_spend_cap" and not (100 <= value <= 100000): return "Keep the spend cap between 100 and 100000"
        if name == "min_margin_pct" and not (0 <= value <= 60): return "Keep the margin floor between 0 and 60%"
        setattr(self, name, value); return f"✔ {name} is now {value} — effective immediately"
