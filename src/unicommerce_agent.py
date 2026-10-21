"""A13 Unicommerce Ops Agent — ek stock truth, saare channels sync.
Sabse bada kaam: 3-way reconciliation (Unicommerce vs Amazon vs Flipkart).
Mismatch = overselling = order cancellation = account health kharab. Ye nahi hone dena.
"""

def reconcile(master_stock: dict, channel_stock: dict) -> dict:
    """master_stock: Unicommerce ka sach. channel_stock: {channel: {sku: qty}}"""
    issues = []
    for channel, stocks in channel_stock.items():
        for sku, qty in stocks.items():
            truth = master_stock.get(sku)
            if truth is None:
                issues.append(f"{channel}/{sku}: master me SKU hi nahi — mapping missing hai")
            elif qty > truth:
                issues.append(f"{channel}/{sku}: channel par {qty} dikh raha, asal stock {truth} — OVERSELL RISK, turant kam karo")
            elif qty < truth:
                issues.append(f"{channel}/{sku}: channel par {qty}, asal {truth} — stock chhupa hai, sales miss ho rahi hain")
    return {"ok": not issues, "issues": issues}

def allocate_stock(sku: str, total_stock: int, channel_velocity: dict) -> dict:
    """Stock ko channel ki bikri ki speed ke hisaab se baanto — tez channel ko pehle."""
    total_v = sum(channel_velocity.values())
    if total_v == 0: return {sku: {}, "note": "Velocity data nahi"}
    alloc, left = {}, total_stock
    chans = sorted(channel_velocity, key=channel_velocity.get, reverse=True)
    for i, ch in enumerate(chans):
        if i == len(chans) - 1: alloc[ch] = left
        else:
            q = round(total_stock * channel_velocity[ch] / total_v); alloc[ch] = q; left -= q
    return {sku: alloc}

def rto_report(returns: list[dict]) -> dict:
    """returns: [{sku, channel, type: RTO/RETURN, cost}] — ghata kahan hai."""
    by_sku = {}
    for r in returns:
        by_sku[r["sku"]] = by_sku.get(r["sku"], 0) + r.get("cost", 0)
    worst = max(by_sku, key=by_sku.get) if by_sku else None
    return {"total_return_loss": sum(by_sku.values()), "worst_sku": worst, "by_sku": by_sku,
            "action": "Worst SKU ki listing/packing/quality check karo — galat expectation = zyada return" if worst else "OK"}
