"""V4 Architecture Registry — agents only where judgment is needed, everything else is a FLOW.
Flow = deterministic code, zero LLM cost, 100% repeatable. Agent = can drift, so it is expensive and audit-heavy.
"""

AGENTS = {
    "A01": ("Market Research", "Making sense of trends/news — judgment"),
    "A02": ("Competitor Intelligence", "Understanding the intent behind competitor moves — judgment"),
    "A03": ("Keyword Domination", "Recognising buying intent — language judgment"),
    "A04": ("Listing Optimization", "Writing copy that sells — creativity"),
    "A05": ("Creative", "Image/video design judgment"),
    "A06": ("Ads Manager", "Rank push vs harvest — money + strategy judgment"),
    "A07": ("Pricing Strategist", "Strategy using the F4 calculator — judgment"),
    "A08": ("Review / Customer Voice", "Real problems from the language of complaints — language judgment"),
    "A09": ("Governance (Orchestrator+Approval+Learning+Algo Impact)", "Owner of the system — coordination judgment"),
}

FLOWS = {
    "F1":  ("Data Sync Flow", "No previous agent — G1 gap", "Scheduled API sync, retry, failure alert"),
    "F2":  ("Unicommerce Ops Flow", "formerly agent A13", "Order sync, stock reconciliation, allocation — all formulas"),
    "F3":  ("Inventory & FBA Flow", "formerly agent A09", "Days of cover, reorder point, shipment checklist — formula/calendar"),
    "F4":  ("Profit Calculation Flow", "the math part of A07", "Margin/fee calculation — a calculator is not made into an agent"),
    "F5":  ("Offer & Festival Flow", "formerly agent A10", "Festival calendar, deal eligibility, coupon templates — fixed rules"),
    "F6":  ("Retention Flow", "formerly agent A11", "Day-25/30 refill reminder triggers — automation, no thinking"),
    "F7":  ("Guardrail & Alert Flow", "part of A12", "If-then rules like stock zero -> pause ads"),
    "F8":  ("War-Room Report Flow", "new", "Daily data compilation — agent insights plug in here"),
    "F9":  ("Algorithm Watch Flow", "new — G5 gap", "Crawl official announcements + catch diffs (A09 does impact analysis)"),
    "F10": ("Seller Health Flow", "new — G8 gap", "Daily ODR/cancellation/late-dispatch check, red alert near limits"),
}

def classify(task_type: str) -> str:
    """When new work arrives, ask first: does it need judgment or a formula?"""
    judgment_tasks = {"trend_analysis", "copy_writing", "strategy", "sentiment", "competitor_intent", "pricing_strategy"}
    return "AGENT" if task_type in judgment_tasks else "FLOW"

def summary() -> dict:
    return {"agents": len(AGENTS), "flows": len(FLOWS),
            "note": "V3 had 14 agents. V4: 9 agents + 10 flows — about half the AI cost, double the reliability."}

if __name__ == "__main__":
    print(summary())
