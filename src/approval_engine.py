"""A12 Approval Governor — the heart of Approval-Only Autonomous Mode.
An agent creates a proposal -> its tier is decided -> Tier0 executes AUTO,
Tier1 is a one-tap user approval, Tier2 a double confirmation. Every action goes into the audit log.
"""
from dataclasses import dataclass, field
from enum import Enum

class Tier(Enum):
    AUTO = 0          # no approval, the system does it itself
    ONE_TAP = 1       # user: Approve / Reject / Change
    DOUBLE = 2        # big money/risk — confirm twice

@dataclass
class Proposal:
    agent: str
    action_type: str          # e.g. ADD_NEGATIVE, BID_CHANGE, LISTING_PATCH, PRICE_CHANGE, BUDGET_CHANGE, FBA_SHIPMENT
    description: str
    change_pct: float = 0.0   # % change in bid/price/budget
    money_impact: float = 0.0 # expected impact in Rs
    reversible: bool = True
    status: str = "PENDING"
    audit: list = field(default_factory=list)

def decide_tier(p: Proposal) -> Tier:
    # Tier 0: small, reversible, money-saving actions
    if p.action_type in ("ADD_NEGATIVE", "ALERT", "AUTO_PAUSE_NO_STOCK", "REPORT"):
        return Tier.AUTO
    if p.action_type == "BID_CHANGE" and abs(p.change_pct) <= 10 and p.reversible:
        return Tier.AUTO
    # Tier 2: high risk
    if p.action_type == "BUDGET_CHANGE" and p.change_pct > 50: return Tier.DOUBLE
    if p.action_type == "PRICE_CHANGE" and p.change_pct < -10: return Tier.DOUBLE
    if p.action_type in ("NEW_SKU_LAUNCH", "BULK_PURCHASE"): return Tier.DOUBLE
    # Everything else is Tier 1
    return Tier.ONE_TAP

class ApprovalEngine:
    def __init__(self, daily_spend_cap: float):
        self.cap = daily_spend_cap
        self.log: list[Proposal] = []
    def submit(self, p: Proposal) -> dict:
        tier = decide_tier(p)
        if tier == Tier.AUTO:
            p.status = "EXECUTED_AUTO"; p.audit.append("Tier0: within guardrails, auto-execute")
        elif tier == Tier.ONE_TAP:
            p.status = "WAITING_USER_APPROVAL"; p.audit.append("Tier1: approval card sent to the user")
        else:
            p.status = "WAITING_DOUBLE_CONFIRM"; p.audit.append("Tier2: double confirmation needed")
        self.log.append(p)
        return {"action": p.action_type, "tier": tier.name, "status": p.status, "desc": p.description}
    def approve(self, p: Proposal) -> str:
        if p.status.startswith("WAITING"):
            p.status = "APPROVED_EXECUTING"; p.audit.append("Approved by the user — executing via API")
        return p.status
    def reject(self, p: Proposal, reason: str = "") -> str:
        p.status = "REJECTED"; p.audit.append(f"Rejected by the user: {reason}")
        return p.status

# Guardrail: no stock, no ads
def guardrail_check(stock_units: int, rating: float, proposed_daily_spend: float, cap: float) -> dict:
    blocks = []
    if stock_units <= 0: blocks.append("STOCK_ZERO: ads auto-pause")
    if rating and rating < 4.0: blocks.append("RATING_LOW: ad spend for this SKU frozen")
    if proposed_daily_spend > cap: blocks.append(f"SPEND_CAP: proposed {proposed_daily_spend} > cap {cap}")
    return {"allowed": not blocks, "blocks": blocks}
