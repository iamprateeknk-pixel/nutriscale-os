"""Season Planner — festival ke liye gift combos/hampers ka taiyaar pack.
Catalog ke asal daamon se combo banata hai, AOV ka asar dikhata hai, listing title aur
creative brief ke saath. Dibbe/packing ki lagat ek ANDAAZ hai (cost sheet aane par pakka hoga).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store
from agents.creative_agent import main_image_brief
from agents.listing_agent import generate_title

BOX_COST_EST = 90  # ₹ per gift box — andaaz; asal lagat cost sheet se pakki hogi

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
    if not products: return {"combos": [], "note": "Catalog khaali hai — pehle products sync/import karo"}
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
            "note": f"{len(combos)} combos taiyaar. Dibbe ki lagat ₹{BOX_COST_EST} andaaz hai — asal margin cost sheet se pakka hoga."}

def render_markdown(pack: dict) -> str:
    if not pack.get("combos"): return "# Season Pack\n\n" + pack.get("note", "")
    L = [f"# {pack['season']} Season Pack — Dry Fruit Farm", "",
         f"_Aaj ka AOV sirf ₹{pack['current_aov']:.0f} hai. Gift combos wahi ilaaj hain — ek order me 3-5 guna bada bill._", ""]
    for i, c in enumerate(pack["combos"], 1):
        L += [f"## Combo {i}: {c['name']} — ₹{c['gift_price']:,}",
              f"- Items: {', '.join(c['items'])} (alag-alag kul ₹{c['parts_total']:,}, combo par {c['discount_pct']}% kam)",
              f"- **Ek order ka bill: ₹{c['gift_price']:,} — aaj ke AOV ka {c['aov_multiple']}x**",
              f"- Listing title: {c['title']}",
              f"- Photo shot 7 (gifting): {c['brief_shot7']}",
              "- [ ] Combo ki listing banao (virtual bundle ya naya SKU) · - [ ] Gift keywords par alag SP-Exact campaign, chhota budget pehle",
              ""]
    L += ["## Season ki tayari ki checklist",
          "- [ ] Hero SKUs (Brazil/Cranberry) ka stock Diwali se 45 din pehle FBA me — stockout season me sabse mehenga padta hai",
          "- [ ] Gift wale keywords ke liye alag campaign (aam keywords se milana mat — iraada alag hai, budget alag)",
          "- [ ] Corporate/bulk puch-tach ke liye listing par 'Bulk orders ke liye sampark karein' wali line",
          f"> Note: {pack['note']}"]
    return "\n".join(L)
