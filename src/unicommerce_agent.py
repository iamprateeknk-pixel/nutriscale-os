"""A13 Unicommerce Ops Agent — one stock truth, all channels in sync.
The biggest job: 3-way reconciliation (Unicommerce vs Amazon vs Flipkart).
Mismatch = overselling = order cancellations = damaged account health. Never let it happen.
"""

def reconcile(master_stock: dict, channel_stock: dict) -> dict:
    """master_stock: Unicommerce is the truth. channel_stock: {channel: {sku: qty}}"""
    issues = []
    for channel, stocks in channel_stock.items():
        for sku, qty in stocks.items():
            truth = master_stock.get(sku)
            if truth is None:
                issues.append(f"{channel}/{sku}: SKU missing from the master — mapping is missing")
            elif qty > truth:
                issues.append(f"{channel}/{sku}: channel shows {qty}, real stock {truth} — OVERSELL RISK, reduce it now")
            elif qty < truth:
                issues.append(f"{channel}/{sku}: channel shows {qty}, real {truth} — stock is hidden, sales are being missed")
    return {"ok": not issues, "issues": issues}

def allocate_stock(sku: str, total_stock: int, channel_velocity: dict) -> dict:
    """Split stock by each channel's sales speed — the faster channel first."""
    total_v = sum(channel_velocity.values())
    if total_v == 0: return {sku: {}, "note": "No velocity data"}
    alloc, left = {}, total_stock
    chans = sorted(channel_velocity, key=channel_velocity.get, reverse=True)
    for i, ch in enumerate(chans):
        if i == len(chans) - 1: alloc[ch] = left
        else:
            q = round(total_stock * channel_velocity[ch] / total_v); alloc[ch] = q; left -= q
    return {sku: alloc}

def rto_report(returns: list[dict]) -> dict:
    """returns: [{sku, channel, type: RTO/RETURN, cost}] — where the losses are."""
    by_sku = {}
    for r in returns:
        by_sku[r["sku"]] = by_sku.get(r["sku"], 0) + r.get("cost", 0)
    worst = max(by_sku, key=by_sku.get) if by_sku else None
    return {"total_return_loss": sum(by_sku.values()), "worst_sku": worst, "by_sku": by_sku,
            "action": "Check the worst SKU's listing/packing/quality — wrong expectations = more returns" if worst else "OK"}
