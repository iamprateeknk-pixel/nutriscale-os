"""V4 Architecture Registry — Agent sirf wahan jahan judgment chahiye, baaki FLOW.
Flow = deterministic code, zero LLM cost, 100% repeatable. Agent = bhatak sakta hai, isiliye mehenga aur audit-heavy hai.
"""

AGENTS = {
    "A01": ("Market Research", "Trend/news se matlab nikalna — judgment"),
    "A02": ("Competitor Intelligence", "Competitor ke move ki niyat samajhna — judgment"),
    "A03": ("Keyword Domination", "Khareed-intent pehchanna — language judgment"),
    "A04": ("Listing Optimization", "Bechne wali copy likhna — creativity"),
    "A05": ("Creative", "Image/video design judgment"),
    "A06": ("Ads Manager", "Rank-Push vs Harvest — paisa + strategy judgment"),
    "A07": ("Pricing Strategist", "Calculator F4 use karke ran-neeti — judgment"),
    "A08": ("Review / Customer Voice", "Shikayat ki bhasha se asal samasya — language judgment"),
    "A09": ("Governance (Orchestrator+Approval+Learning+Algo Impact)", "System ka malik — coordination judgment"),
}

FLOWS = {
    "F1":  ("Data Sync Flow", "Purana agent nahi tha — G1 gap", "Schedule par API sync, retry, fail alert"),
    "F2":  ("Unicommerce Ops Flow", "purana A13 Agent", "Order sync, stock reconciliation, allocation — sab formula"),
    "F3":  ("Inventory & FBA Flow", "purana A09 Agent", "Days-of-cover, reorder point, shipment checklist — formula/calendar"),
    "F4":  ("Profit Calculation Flow", "A07 ka math hissa", "Margin/fee hisaab — calculator ko agent nahi banate"),
    "F5":  ("Offer & Festival Flow", "purana A10 Agent", "Festival calendar, deal eligibility, coupon template — fixed niyam"),
    "F6":  ("Retention Flow", "purana A11 Agent", "Day-25/30 refill reminder triggers — automation, soch nahi"),
    "F7":  ("Guardrail & Alert Flow", "A12 ka hissa", "Stock zero -> ads pause type if-then rules"),
    "F8":  ("War-Room Report Flow", "naya", "Roz data compile — agents ki insights isme plug hongi"),
    "F9":  ("Algorithm Watch Flow", "naya — G5 gap", "Official announcements crawl + diff pakadna (impact analysis A09 karega)"),
    "F10": ("Seller Health Flow", "naya — G8 gap", "ODR/cancellation/late-dispatch roz check, limit ke paas laal alert"),
}

def classify(task_type: str) -> str:
    """Naya kaam aaye to pehle ye poochho: isme judgment hai ya formula?"""
    judgment_tasks = {"trend_analysis", "copy_writing", "strategy", "sentiment", "competitor_intent", "pricing_strategy"}
    return "AGENT" if task_type in judgment_tasks else "FLOW"

def summary() -> dict:
    return {"agents": len(AGENTS), "flows": len(FLOWS),
            "note": "V3 me 14 agents the. V4: 9 agents + 10 flows — AI kharcha ~aadha, reliability dugni."}

if __name__ == "__main__":
    print(summary())
