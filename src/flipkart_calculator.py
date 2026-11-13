"""Flipkart part of F4 (G7 fix) — Flipkart fees differ from Amazon, so the calculation differs too.
The commission slab changes with price (estimated slabs — verify against Seller Hub).
"""
def flipkart_fees(price: float, weight_grams: int = 500, fulfilled_by_flipkart: bool = True) -> dict:
    # Commission (grocery/food estimate): cheaper item = higher % slab
    commission_pct = 0.14 if price <= 300 else 0.11 if price <= 700 else 0.09
    commission = price * commission_pct
    fixed_fee = 25 if price <= 500 else 40
    shipping = 55 if weight_grams <= 500 else 75 if weight_grams <= 1000 else 110
    if fulfilled_by_flipkart: shipping -= 10   # Smart Fulfilment lowers the shipping impact (estimate)
    collection = price * 0.02                  # payment collection fee andaaz
    total = commission + fixed_fee + shipping + collection
    return {"commission_pct": round(commission_pct * 100, 1), "commission": round(commission, 2),
            "fixed_fee": fixed_fee, "shipping_fee": shipping, "collection_fee": round(collection, 2),
            "total_fees": round(total, 2), "you_receive": round(price - total, 2),
            "note": "Slabs are estimates — Seller Hub's real fee table goes into this file in Phase 1"}

def flipkart_profit(price: float, product_cost: float, packing: float = 25, weight_grams: int = 500) -> dict:
    f = flipkart_fees(price, weight_grams)
    profit = f["you_receive"] - product_cost - packing
    return {**f, "profit_before_ads": round(profit, 2),
            "margin_pct": round(profit / price * 100, 1) if price else 0,
            "break_even_roas": round(100 / (profit / price * 100), 2) if profit > 0 else None}
