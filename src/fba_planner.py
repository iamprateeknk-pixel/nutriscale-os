"""A09 FBA + Flipkart Warehouse Planner.
Rule: Hero SKU = marketplace warehouse (Prime/Assured badge + fast delivery + fixed cost).
Slow SKU = your own warehouse (avoid storage fees). Keep 30-45 days of stock; under 15 days = replenish.
"""

def days_of_cover(stock: int, daily_sales: float) -> float:
    return round(stock / daily_sales, 1) if daily_sales else 999.0

def replenishment(stock: int, daily_sales: float, lead_days: int = 7,
                  target_cover_days: int = 35) -> dict:
    cover = days_of_cover(stock, daily_sales)
    need = max(0, round(daily_sales * target_cover_days - stock))
    urgent = cover < (lead_days + 8)   # lead time + safety
    return {"days_of_cover": cover, "reorder_qty": need if urgent else 0,
            "status": "REPLENISH_NOW (create a Tier-1 approval proposal)" if urgent else "OK",
            "festival_note": "Keep 45-60 days of cover 45 days before a peak/festival — inbound gets congested"}

def fba_vs_selfship(selling_price: float, fba_fee: float, self_courier: float,
                    self_packing: float, self_rto_loss: float) -> dict:
    self_total = self_courier + self_packing + self_rto_loss
    return {"fba_cost": fba_fee, "selfship_cost": round(self_total, 2),
            "cheaper": "FBA" if fba_fee <= self_total else "SELF_SHIP",
            "saving_per_order": round(abs(self_total - fba_fee), 2),
            "note": "In FBA the Prime badge + fast delivery also raise conversion — look at the sales impact, not just cost"}

def warehouse_decision(sku_daily_sales: float, shelf_life_days: int) -> str:
    if sku_daily_sales >= 5: return "MARKETPLACE_WAREHOUSE (FBA / Flipkart Assured) — hero SKU"
    if sku_daily_sales >= 1: return "SPLIT — some in FBA, the rest in your own warehouse"
    return "OWN_GODOWN — slow SKU, avoid storage fees"
