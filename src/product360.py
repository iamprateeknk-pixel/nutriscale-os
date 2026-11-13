"""SKU 360° (V13) — the full picture of one SKU in one place: sales, profit (with fee precision),
stock cover, listing status, open work on it. Missing data is shown plainly as 'not available'."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12
import analytics as AN

def product_360(db, sku: str, platform: str = None) -> dict:
    """V15: no channel mixing — with a platform, only that channel; otherwise sales per channel
    separately (sales_by_platform) plus the total and a clear list of channels."""
    ensure_v12(db)
    prod = db.execute("SELECT * FROM products WHERE sku=? AND (? IS NULL OR platform=?) ORDER BY platform LIMIT 1",
                      (sku, platform, platform)).fetchone()
    if not prod: return {"found": False, "sku": sku, "error": "This SKU is not in the catalog"}
    prod = dict(prod)
    by_platform = {}
    for pf in [r["platform"] for r in db.execute("SELECT DISTINCT platform FROM order_items WHERE sku=?", (sku,))]:
        s = next((x for x in AN.sku_sales(db, pf) if x["sku"] == sku), None)
        if s: by_platform[pf] = {"units": s["units"], "revenue": round(s["revenue"], 2)}
    sales = next((r for r in AN.sku_sales(db, platform) if r["sku"] == sku), {"units": 0, "revenue": 0})
    import finance as F
    fin = F.contribution_v2(db, sku, prod["price"], prod["platform"] or "Amazon")
    inv_rows = db.execute("SELECT location, qty, sellable_qty, unsellable_qty FROM inventory WHERE sku=?", (sku,)).fetchall()
    total_qty = sum(r["qty"] for r in inv_rows)
    vel_rep = AN.sku_velocity_report(db, sku, platform=platform)   # V20: with stale warning
    vel = vel_rep["velocity_per_day"]
    from fba_planner import days_of_cover
    cover = days_of_cover(int(total_qty), vel) if vel > 0 else None
    versions = db.execute("SELECT version, status, created_at FROM listing_versions WHERE sku=? ORDER BY version DESC LIMIT 5", (sku,)).fetchall()
    actions = db.execute("SELECT COUNT(*) c FROM action_v12 WHERE payload LIKE ?", (f'%"{sku}"%',)).fetchone()["c"]
    fees_exact = F.sku_fee_rate(db, sku, prod["platform"] or "Amazon")
    # V20: stock channel now from an explicit mapping (stock_channel_map), name-guessing only as fallback;
    # channel math uses SELLABLE qty — damaged/stuck stock cannot inflate cover
    import stock as ST
    stock_by_channel, stock_total_by_channel, unsellable_by_channel, loc_detail = {}, {}, {}, []
    sellable_verified_by_channel, unknown_avail_by_channel = {}, {}
    for r in inv_rows:
        ch, basis = ST.channel_for(db, r["location"])
        s, u = ST.sellable_of(r), ST.unsellable_of(r)
        stock_by_channel[ch] = stock_by_channel.get(ch, 0) + s
        stock_total_by_channel[ch] = stock_total_by_channel.get(ch, 0) + int(r["qty"] or 0)
        if u: unsellable_by_channel[ch] = unsellable_by_channel.get(ch, 0) + u
        # V21: separate evidence for availability — VERIFIED when sellable_qty is recorded, otherwise UNKNOWN
        # (UNKNOWN stock is never silently merged into verified sellable stock)
        verified = r["sellable_qty"] is not None
        if verified: sellable_verified_by_channel[ch] = sellable_verified_by_channel.get(ch, 0) + s
        else: unknown_avail_by_channel[ch] = unknown_avail_by_channel.get(ch, 0) + int(r["qty"] or 0)
        loc_detail.append({"location": r["location"], "qty": r["qty"], "sellable": s, "unsellable": u,
                           "channel": ch, "channel_basis": basis,
                           "availability": "VERIFIED" if verified else "UNKNOWN"})
    view_qty = stock_by_channel.get(platform, 0) if platform else sum(stock_by_channel.values())
    from fba_planner import days_of_cover as _dc
    view_cover = _dc(int(view_qty), vel) if (platform and vel > 0) else (
        _dc(int(view_qty), vel) if vel > 0 else cover)
    return {"found": True, "sku": sku, "name": prod["name"], "platform": prod["platform"],
            "platform_view": platform or "ALL", "channels": sorted(by_platform.keys()),
            "sales_by_platform": by_platform,
            "price": prod["price"], "rating": prod["rating"], "reviews": prod["reviews"],
            "sales": sales, "finance": fin,
            "inventory": {"total_qty": total_qty, "by_location": loc_detail,
                          "stock_by_channel": stock_by_channel,
                          "stock_total_by_channel": stock_total_by_channel,
                          "unsellable_by_channel": unsellable_by_channel,
                          "sellable_verified_by_channel": sellable_verified_by_channel,
                          "unknown_availability_by_channel": unknown_avail_by_channel,
                          "availability_note": ("Some stock availability is NOT verified (sellable_qty not recorded) — "
                                                "it is shown separately above; do not rely on cover for it")
                                               if unknown_avail_by_channel else "All stock availability is verified (sellable recorded)",
                          "view_qty": view_qty, "view_basis": ((platform + " channel SELLABLE stock") if platform else "SELLABLE stock across all channels"),
                          "velocity_per_day": round(vel, 2), "days_of_cover": view_cover,
                          "velocity_report": vel_rep},
            "listing_versions": [dict(r) for r in versions],
            "open_actions_mentioning_sku": actions,
            "fee_exact": fees_exact,
            "note": "Only what the data supports is calculated; empty parts are shown honestly as '0/not available'"}
