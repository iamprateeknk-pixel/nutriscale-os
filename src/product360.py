"""SKU 360° (V13) — ek SKU ki poori tasveer ek jagah: bikri, munafa (fee precision ke saath),
stock cover, listing halat, uspar khule kaam. Jo data nahi, woh saaf 'uplabdh nahi'."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12
import analytics as AN

def product_360(db, sku: str, platform: str = None) -> dict:
    """V15: channel-mixing band — platform diya to sirf wahi channel; warna har channel ki bikri
    alag (sales_by_platform) aur kul ke saath channels ki suchi saaf dikhegi."""
    ensure_v12(db)
    prod = db.execute("SELECT * FROM products WHERE sku=? AND (? IS NULL OR platform=?) ORDER BY platform LIMIT 1",
                      (sku, platform, platform)).fetchone()
    if not prod: return {"found": False, "sku": sku, "error": "Catalog me ye SKU nahi hai"}
    prod = dict(prod)
    by_platform = {}
    for pf in [r["platform"] for r in db.execute("SELECT DISTINCT platform FROM order_items WHERE sku=?", (sku,))]:
        s = next((x for x in AN.sku_sales(db, pf) if x["sku"] == sku), None)
        if s: by_platform[pf] = {"units": s["units"], "revenue": round(s["revenue"], 2)}
    sales = next((r for r in AN.sku_sales(db, platform) if r["sku"] == sku), {"units": 0, "revenue": 0})
    import finance as F
    fin = F.contribution_v2(db, sku, prod["price"], prod["platform"] or "Amazon")
    inv_rows = db.execute("SELECT location, qty FROM inventory WHERE sku=?", (sku,)).fetchall()
    total_qty = sum(r["qty"] for r in inv_rows)
    vel = AN.sku_velocity_per_day(db, sku, platform=platform)   # V18: channel view = channel ki raftaar; ALL view = kul
    from fba_planner import days_of_cover
    cover = days_of_cover(int(total_qty), vel) if vel > 0 else None
    versions = db.execute("SELECT version, status, created_at FROM listing_versions WHERE sku=? ORDER BY version DESC LIMIT 5", (sku,)).fetchall()
    actions = db.execute("SELECT COUNT(*) c FROM action_v12 WHERE payload LIKE ?", (f'%"{sku}"%',)).fetchone()["c"]
    fees_exact = F.sku_fee_rate(db, sku, prod["platform"] or "Amazon")
    return {"found": True, "sku": sku, "name": prod["name"], "platform": prod["platform"],
            "platform_view": platform or "ALL", "channels": sorted(by_platform.keys()),
            "sales_by_platform": by_platform,
            "price": prod["price"], "rating": prod["rating"], "reviews": prod["reviews"],
            "sales": sales, "finance": fin,
            "inventory": {"total_qty": total_qty, "by_location": [dict(r) for r in inv_rows],
                          "velocity_per_day": round(vel, 2), "days_of_cover": cover},
            "listing_versions": [dict(r) for r in versions],
            "open_actions_mentioning_sku": actions,
            "fee_exact": fees_exact,
            "note": "Jo hisaab data se bana wahi hai; khaali hisse '0/uplabdh nahi' sach ke saath dikhe hain"}
