"""Control Center — dashboard ke controls ka dimaag.
Har control ka ek malik hai: tum. Agent band, guardrail badalna, aur sabse bada — KILL SWITCH.
Niyam: Kill Switch kabhi approval nahi mangega. Khatra ho to pehle roko, baat baad me.
"""
from dataclasses import dataclass, field

@dataclass
class Controls:
    agents_enabled: dict = field(default_factory=lambda: {a: True for a in
        ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09"]})
    daily_spend_cap: float = 2000.0     # Rs — ek din me isse zyada ad spend kabhi nahi
    min_margin_pct: float = 15.0        # isse kam margin wali SKU par ads nahi chalenge
    max_bid_change_pct: float = 20.0    # ek baar me isse bada bid badlav Tier-2 approval mangega
    auto_pause_on_stockout: bool = True
    kill_switch: bool = False           # True = SAARA ad spend band, abhi ke abhi

    def can_run_ads(self, sku_margin_pct: float, stock: int) -> dict:
        if self.kill_switch: return {"allowed": False, "reason": "KILL SWITCH ON — saara ad spend band hai (tumne roka hai)"}
        if not self.agents_enabled.get("A06", True): return {"allowed": False, "reason": "A06 Ads Agent band hai (Control Center se)"}
        if self.auto_pause_on_stockout and stock <= 0: return {"allowed": False, "reason": "Stock zero — ads auto-pause"}
        if sku_margin_pct < self.min_margin_pct: return {"allowed": False, "reason": f"Margin {sku_margin_pct}% minimum {self.min_margin_pct}% se kam — is SKU par ads ghata hai"}
        return {"allowed": True, "reason": "Saare guardrail pass"}

    def emergency_stop(self) -> str:
        self.kill_switch = True
        return "🛑 KILL SWITCH ON — saare campaigns pause queue me. Koi approval nahi manga gaya, pehle suraksha."

    def resume(self) -> str:
        self.kill_switch = False
        return "▶️ System phir chaalu — guardrails ke andar kaam karega"

    def set_guardrail(self, name: str, value) -> str:
        allowed = {"daily_spend_cap", "min_margin_pct", "max_bid_change_pct"}
        if name not in allowed: return f"Galat control: {name}"
        if name == "daily_spend_cap" and not (100 <= value <= 100000): return "Spend cap 100–100000 ke beech rakho"
        if name == "min_margin_pct" and not (0 <= value <= 60): return "Margin floor 0–60% ke beech rakho"
        setattr(self, name, value); return f"✔ {name} ab {value} hai — isi pal se lagu"
