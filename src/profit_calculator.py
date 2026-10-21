"""A07 Pricing & Profit Agent — core math.
Har SKU ka asal profit aur usse nikla hua ads guardrail:
break-even ROAS, target ACOS, aur max CPC jo afford ho sakta hai.
Fees approximate hain (Amazon IN grocery ~2026) — asal fee Seller Central se verify karni hai.
"""
from dataclasses import dataclass

@dataclass
class SKU:
    name: str
    selling_price: float      # Rs, customer jo deta hai (GST incl.)
    product_cost: float       # Rs per pack (dry fruit cost)
    packing_cost: float = 0.0
    weight_grams: int = 500
    referral_pct: float = 0.09      # Amazon IN grocery referral ~9% (verify)
    closing_fee: float = 25.0       # Rs per unit approx
    shipping_fee: float = 65.0      # FBA / Easy Ship approx
    return_loss_pct: float = 0.02   # returns/damage ka expected loss
    other_cost: float = 0.0

def contribution(sku: SKU) -> dict:
    fees = sku.selling_price * sku.referral_pct + sku.closing_fee + sku.shipping_fee
    returns = sku.selling_price * sku.return_loss_pct
    total_cost = sku.product_cost + sku.packing_cost + fees + returns + sku.other_cost
    profit = sku.selling_price - total_cost
    margin_pct = (profit / sku.selling_price * 100) if sku.selling_price else 0.0
    # Break-even ACOS = margin before ads. Target ACOS = uska 60% (profit bachana hai)
    be_acos = max(margin_pct, 0.0)
    target_acos = be_acos * 0.60
    be_roas = (100 / be_acos) if be_acos > 0 else float("inf")
    target_roas = (100 / target_acos) if target_acos > 0 else float("inf")
    price_per_kg = sku.selling_price / (sku.weight_grams / 1000)
    return {
        "sku": sku.name, "price": sku.selling_price, "price_per_kg": round(price_per_kg, 0),
        "marketplace_fees": round(fees, 2), "profit_before_ads": round(profit, 2),
        "margin_pct": round(margin_pct, 1), "break_even_acos_pct": round(be_acos, 1),
        "target_acos_pct": round(target_acos, 1), "break_even_roas": round(be_roas, 2),
        "target_roas": round(target_roas, 2),
        "profitable_for_ads": margin_pct >= 20,
    }

def max_cpc(selling_price: float, conversion_rate: float, target_acos_pct: float) -> float:
    """Isse zyada bid = nuksan pakka. CPC = price x CVR x target ACOS"""
    return round(selling_price * conversion_rate * (target_acos_pct / 100), 2)

if __name__ == "__main__":
    badam = SKU("Almonds California 500g", selling_price=649, product_cost=340, packing_cost=25, weight_grams=500)
    print(contribution(badam))
    print("Max CPC @12% CVR:", max_cpc(649, 0.12, contribution(badam)["target_acos_pct"]))
