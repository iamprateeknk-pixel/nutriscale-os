"""Season Planner — a ready pack of gift combos/hampers for festivals.
Builds combos from real catalog prices, shows the AOV impact, with listing title and
creative brief. Box/packing cost is an ESTIMATE (confirmed once the cost sheet arrives).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store
from agents.creative_agent import main_image_brief
from agents.listing_agent import generate_title

BOX_COST_EST = 90  # ₹ per gift box — estimate; the real cost comes from the cost sheet

COMBO_DEFS = [
    {"name": "Diwali Delight Box", "items": ["Dried Cranberries 200g", "Brazil Nuts Grade A++ 200g", "Raw Pecan Nuts 200g"],
     "discount_pct": 7, "keywords": ["diwali dry fruits gift box", "dry fruit hamper"]},
    {"name": "Royal Premium Hamper", "items": ["Brazil Nuts Grade A++ 200g", "Raw Macadamia Nuts 200g", "Raw Pecan Nuts 200g", "Dried Blueberries 200g"],
     "discount_pct": 10, "keywords": ["premium dry fruits gift hamper", "corporate diwali gift"]},
    {"name": "Mithaas Budget Box", "items": ["Dried Cranberries 200g", "Dried Blueberries 200g", "Raw Sunflower Seeds 200g"],
     "discount_pct": 8, "keywords": ["dry fruits gift box under 700", "diwali gift combo"]},
]

def build_season_pack(store: Store, current_aov: float = 443.0, season: str = "Diwali") -> dict:
    products = {p["name"].replace("Dry Fruit Farm Premium ", ""): p for p in store.all_products()}
    if not products: return {"combos": [], "note": "Catalog is empty — sync/import products first"}
    combos = []
    for d in COMBO_DEFS:
        missing = [i for i in d["items"] if i not in products]
        if missing: continue
        parts = sum(products[i]["price"] for i in d["items"])
        price = round(parts * (1 - d["discount_pct"] / 100))
        combos.append({**d, "parts_total": round(parts), "gift_price": price,
                       "est_extra_cost": BOX_COST_EST,
                       "aov_multiple": round(price / current_aov, 1),
                       "title": generate_title(f"Dry Fruit Farm {d['name']} Gift Hamper", "Premium", f"{len(d['items'])} x 200g", d["keywords"], "gifting"),
                       "brief_shot7": main_image_brief(d["name"], "Premium Gift", "combo")["shots"][6]["brief"]})
    return {"season": season, "combos": combos, "current_aov": current_aov,
            "note": f"{len(combos)} combos ready. Box cost ₹{BOX_COST_EST} is an estimate — real margin comes from the cost sheet."}

def render_markdown(pack: dict) -> str:
    if not pack.get("combos"): return "# Season Pack\n\n" + pack.get("note", "")
    L = [f"# {pack['season']} Season Pack — Dry Fruit Farm", "",
         f"_Current AOV is only ₹{pack['current_aov']:.0f}. Gift combos are the fix — a 3-5x bigger bill per order._", ""]
    for i, c in enumerate(pack["combos"], 1):
        L += [f"## Combo {i}: {c['name']} — ₹{c['gift_price']:,}",
              f"- Items: {', '.join(c['items'])} (separately ₹{c['parts_total']:,} total, {c['discount_pct']}% off as a combo)",
              f"- **Ek order ka bill: ₹{c['gift_price']:,} — aaj ke AOV ka {c['aov_multiple']}x**",
              f"- Listing title: {c['title']}",
              f"- Photo shot 7 (gifting): {c['brief_shot7']}",
              "- [ ] Create the combo listing (virtual bundle or new SKU) · - [ ] A separate SP-Exact campaign for gift keywords, small budget first",
              ""]
    L += ["## Season preparation checklist",
          "- [ ] Hero SKU (Brazil/Cranberry) stock in FBA 45 days before Diwali — a stockout in season is the most expensive",
          "- [ ] A separate campaign for gift keywords (do not mix with regular keywords — different intent, separate budget)",
          "- [ ] A 'Contact us for bulk orders' line on the listing for corporate/bulk enquiries",
          f"> Note: {pack['note']}"]
    return "\n".join(L)
