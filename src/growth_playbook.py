"""Growth Playbook (V24) — market research ke niyam (marketplace_knowledge) ko TUMHARE data par chalana.

Har function ka nateeja rule_id ke saath hai (source wahin), aur jahan data nahi wahan saaf 'DATA_NEEDED' —
koi andaaz asli number ban kar nahi dikhta.
  break_even()        AMZ-A-04  — SKU ka break-even / target ACOS (cost + fee se)
  ads_structure()     AMZ-A-01..03 — campaign structure ki jaanch: auto/exact alag?, harvest, self-competition
  event_calendar()    IN-E-01/02 — aane wale sale/tyohaar + taiyaari ki aakhri tareekh
  review_plan()       AMZ-R-01/02 — Vine-yogya SKUs, kam rating wale SKUs (sirf policy-safe raaste)
  today()             home screen: aaj ke sabse zaroori kaam, ek jagah
"""
import os, sys, re, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12
import marketplace_knowledge as MK

# ---------------- Break-even ACOS ----------------
def break_even(db, sku: str, price: float = None, platform: str = "Amazon", desired_net_margin_pct: float = 10.0) -> dict:
    import finance as F
    if price is None:
        r = db.execute("SELECT price FROM products WHERE sku=? AND (platform=? OR ? IS NULL) LIMIT 1", (sku, platform, platform)).fetchone()
        price = r["price"] if r else None
    if not price:
        return {"sku": sku, "status": "DATA_NEEDED", "rule_id": "AMZ-A-04", "note": "Price nahi mila — product catalog me daalo"}
    c = F.contribution_v2(db, sku, price, platform)
    if not c.get("known"):
        return {"sku": sku, "status": "DATA_NEEDED", "rule_id": "AMZ-A-04", "price": price,
                "note": "Cost darj nahi — break-even ACOS cost ke bina banta hi nahi (Profit screen par COGS daalo)"}
    be = c["contribution"] / price if price else 0
    target = be - desired_net_margin_pct / 100
    return {"sku": sku, "status": "OK", "rule_id": "AMZ-A-04", "price": price, "pre_ad_profit": c["contribution"],
            "break_even_acos_pct": round(be * 100, 1), "target_acos_pct": round(target * 100, 1) if target > 0 else None,
            "break_even_roas": round(1 / be, 2) if be > 0 else None,
            "fee_precision": c.get("fee_precision"), "fee_source": c.get("fee_source"),
            "note": ("Ads se pehle hi ghaata — pehle price/cost theek karo, ads scale mat karo" if be <= 0 else
                     f"ACOS {round(be*100,1)}% se upar = har ad-bikri par ghaata; {desired_net_margin_pct:.0f}% munafa chahiye to ACOS "
                     + (f"{round(target*100,1)}% tak" if target > 0 else "is margin par mumkin nahi")),
            "launch_note": MK.rule("AMZ-A-05")["rule"]}

# ---------------- Campaign structure ----------------
def _ctype(name: str) -> str:
    n = (name or "").lower()
    if re.search(r"\bauto", n): return "AUTO"
    if re.search(r"\bexact|\bexa\b|_ex\b|\bskag", n): return "EXACT"
    if re.search(r"\bphrase", n): return "PHRASE"
    if re.search(r"\bbroad", n): return "BROAD"
    if re.search(r"\basin|\bpat\b|\bproduct target|\bpt\b|competitor", n): return "PRODUCT_TARGETING"
    if re.search(r"\bbrand|\bdefen", n): return "BRAND_DEFENSE"
    return "UNKNOWN"

def ads_structure(store) -> dict:
    db = store.db
    camps = {r["campaign"] for r in db.execute("SELECT DISTINCT campaign FROM search_terms WHERE campaign IS NOT NULL AND campaign<>''")}
    camps |= {r["name"] for r in db.execute("SELECT name FROM campaigns")}
    if not camps:
        return {"status": "DATA_NEEDED", "rule_ids": ["AMZ-A-01"], "findings": [],
                "note": "Campaign data nahi — Ads Console se Search Term + Campaign report import karo"}
    types = {c: _ctype(c) for c in camps}
    counts = {}
    for t in types.values(): counts[t] = counts.get(t, 0) + 1
    findings = []
    if not counts.get("AUTO"):
        findings.append({"severity": "WARN", "rule_id": "AMZ-A-02", "message": "Koi Auto (khoj) campaign nahi dikha — naye search terms kahan se milenge?",
                         "action": "Har hero SKU ke liye ek chhota Auto campaign (2-4 hafte), phir harvest"})
    if not counts.get("EXACT"):
        findings.append({"severity": "WARN", "rule_id": "AMZ-A-01", "message": "Koi Exact (kamai) campaign nahi dikha — jeetne wale terms ka kharch kaabu me nahi",
                         "action": "Jo terms 2+ order de chuke, unka alag Exact campaign"})
    if counts.get("UNKNOWN", 0) > len(camps) / 2:
        findings.append({"severity": "TIP", "rule_id": "AMZ-A-01",
                         "message": f"{counts['UNKNOWN']} campaigns ke naam se unka kaam pata nahi chalta",
                         "action": "Naam me kaam likho: 'SP | Kaju W240 | AUTO', 'SP | Kaju W240 | EXACT' — tabhi system aur tum dono samjhenge"})
    # Self-competition: ek hi term AUTO/BROAD aur EXACT dono me paisa kha raha hai
    rows = db.execute("SELECT term, campaign, SUM(spend) sp, SUM(purchases) pu FROM search_terms GROUP BY term, campaign").fetchall()
    by_term = {}
    for r in rows: by_term.setdefault(r["term"], []).append(dict(r))
    overlap = []
    for t, lst in by_term.items():
        ts = {types.get(x["campaign"], "UNKNOWN") for x in lst}
        if "EXACT" in ts and ts & {"AUTO", "BROAD", "PHRASE"}:
            overlap.append({"term": t, "campaigns": [x["campaign"] for x in lst],
                            "spend_outside_exact": round(sum(x["sp"] or 0 for x in lst if types.get(x["campaign"]) != "EXACT"), 2)})
    if overlap:
        findings.append({"severity": "WARN", "rule_id": "AMZ-A-02",
                         "message": f"{len(overlap)} terms Exact ke saath Auto/Broad me bhi kharch kar rahe hain (apni hi bid se ladai)",
                         "action": "Auto/Broad campaign me in terms par negative-exact lagao", "terms": overlap[:15]})
    import ads_studio as AS
    hv = AS.harvest_candidates(store, MK.rule("AMZ-A-02")["value"]["harvest_min_orders"])
    exact_terms = {t for t, lst in by_term.items() if any(types.get(x["campaign"]) == "EXACT" for x in lst)}
    pending = [h for h in hv["harvest"] if h["term"] not in exact_terms and types.get(h["from_campaign"]) != "EXACT"]
    if pending:
        findings.append({"severity": "TIP", "rule_id": "AMZ-A-02", "message": f"{len(pending)} jeetne wale terms abhi Exact me nahi",
                         "action": "Exact campaign me harvest karo (approval ke saath)", "terms": pending[:15]})
    waste = round(sum(n["wasted"] for n in hv["negatives"]), 2)
    if waste:
        findings.append({"severity": "WARN", "rule_id": "AMZ-A-03", "message": f"₹{waste:,.0f} un terms par gaya jo kahin convert nahi hue",
                         "action": "Negative-exact proposals banao (haftawar Search Term review)", "terms": hv["negatives"][:15]})
    score = max(0, 100 - 15 * sum(f["severity"] == "WARN" for f in findings) - 5 * sum(f["severity"] == "TIP" for f in findings))
    return {"status": "OK", "structure_score": score, "campaign_types": counts, "campaigns": [{"name": c, "type": t} for c, t in sorted(types.items())],
            "findings": findings, "wasted_spend": waste, "harvest_pending": len(pending),
            "rule_ids": ["AMZ-A-01", "AMZ-A-02", "AMZ-A-03"],
            "note": "Campaign ka prakar NAAM se pehchana gaya hai — galat pehchan ho to naam me AUTO/EXACT likho"}

# ---------------- Sale events ----------------
# Tareekhein har saal badalti hain — ye AANUMANIT khidkiyaan hain (pichhle saalon ka pattern). Official tareekh
# Seller Central > Sale Event Planner se pakki karo; confirmed=True sirf tab jab tum khud pakki tareekh daalo.
EVENT_WINDOWS = [
    {"name": "Republic Day Sale", "month": 1, "day": 12, "days": 6, "focus": "daily snacking packs, coupons"},
    {"name": "Valentine / gifting", "month": 2, "day": 7, "days": 8, "focus": "chhote gift box"},
    {"name": "Holi", "month": 3, "day": 5, "days": 14, "focus": "gift box, mithai-ke-saath dry fruits"},
    {"name": "Prime Day India", "month": 7, "day": 12, "days": 3, "focus": "Lightning Deals, Prime-only deals"},
    {"name": "Raksha Bandhan", "month": 8, "day": 1, "days": 14, "focus": "rakhi gift box/hamper"},
    {"name": "Great Indian Festival / Diwali", "month": 9, "day": 25, "days": 40, "focus": "gift hamper, 1kg packs, corporate gifting"},
    {"name": "Wedding season", "month": 11, "day": 15, "days": 45, "focus": "bulk/gift box, premium grades"},
    {"name": "Christmas / New Year gifting", "month": 12, "day": 15, "days": 18, "focus": "gift box, trail mix"},
]

def event_calendar(today=None, horizon_days: int = 120, confirmed: dict = None) -> dict:
    t = today or datetime.date.today()
    if isinstance(t, str): t = datetime.date.fromisoformat(t)
    v = MK.rule("IN-E-01")["value"]
    out = []
    for e in EVENT_WINDOWS:
        for yr in (t.year, t.year + 1):
            start = datetime.date(yr, e["month"], e["day"])
            if confirmed and e["name"] in confirmed: start = datetime.date.fromisoformat(confirmed[e["name"]])
            end = start + datetime.timedelta(days=e["days"])
            if end < t or (start - t).days > horizon_days: continue
            fba = start - datetime.timedelta(days=v["fba_lead_days"][1])
            ready = start - datetime.timedelta(days=v["ready_lead_days"])
            days_to = (start - t).days
            phase = ("CHAL RAHA HAI" if start <= t <= end else
                     "FBA STOCK BHEJO" if t <= fba + datetime.timedelta(days=5) and t >= fba - datetime.timedelta(days=10) else
                     "LISTING/COUPON/ADS TAIYAAR KARO" if fba < t <= ready else
                     "AAKHRI HAFTA" if ready < t < start else "YOJANA BANAO")
            out.append({"event": e["name"], "start": start.isoformat(), "end": end.isoformat(), "days_to_start": days_to,
                        "fba_stock_by": fba.isoformat(), "ready_by": ready.isoformat(), "phase": phase, "focus": e["focus"],
                        "confirmed": bool(confirmed and e["name"] in confirmed)})
            break
    out.sort(key=lambda x: x["start"])
    return {"today": t.isoformat(), "events": out, "rule_ids": ["IN-E-01", "IN-E-02"],
            "note": "Tareekhein ANUMAAN hain (pichhle saalon ka pattern) — Sale Event Planner se pakki karo"}

# ---------------- Reviews ----------------
def review_plan(db) -> dict:
    rows = [dict(r) for r in db.execute("SELECT sku, name, platform, rating, reviews FROM products")]
    if not rows: return {"status": "DATA_NEEDED", "items": [], "note": "Product catalog khaali"}
    mx = MK.rule("AMZ-R-01")["value"]["max_reviews"]
    items = []
    for p in rows:
        if p["platform"] == "Amazon" and (p["reviews"] or 0) < mx:
            items.append({"sku": p["sku"], "name": p["name"], "reviews": p["reviews"] or 0, "rating": p["rating"],
                          "action": "Vine-yogya (30 se kam reviews) — Brand Registry ho to Vine me daalo", "rule_id": "AMZ-R-01"})
        if p["rating"] and p["rating"] < 4.0:
            items.append({"sku": p["sku"], "name": p["name"], "reviews": p["reviews"] or 0, "rating": p["rating"],
                          "action": "Rating 4 se kam — shikayatein padho (product/pack/taazgi), pehle product theek karo", "rule_id": "AMZ-R-01"})
    return {"status": "OK", "items": items, "rule_ids": ["AMZ-R-01", "AMZ-R-02"],
            "policy": MK.rule("AMZ-R-02")["rule"]}

# ---------------- Today (home screen) ----------------
def today(store) -> dict:
    db = store.db; ensure_v12(db)
    import actions as ACT, agent_brain as AB, keyword_intel as KI
    pending = db.execute("SELECT COUNT(*) c FROM action_v12 WHERE state IN ('APPROVAL_PENDING','APPROVED','QUEUED')").fetchone()["c"]
    pending += db.execute("SELECT COUNT(*) c FROM actions WHERE status LIKE 'WAITING%'").fetchone()["c"]
    n_terms = db.execute("SELECT COUNT(*) c FROM search_terms").fetchone()["c"]
    n_orders = db.execute("SELECT COUNT(*) c FROM order_items").fetchone()["c"] + db.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
    n_products = db.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]
    n_costs = db.execute("SELECT COUNT(DISTINCT sku) c FROM cost_versions").fetchone()["c"]
    n_sqp = db.execute("SELECT COUNT(*) c FROM brand_analytics").fetchone()["c"]
    last_import = db.execute("SELECT MAX(imported_at) t FROM import_batches").fetchone()["t"]
    from connectors import config as cfg
    connected = [k for k, v in cfg.status_all().items() if v["configured"]]
    checklist = [
        {"step": "Search Term report import", "done": n_terms > 0, "why": "Keyword plan, negatives, harvest — sab isi se"},
        {"step": "Orders import", "done": n_orders > 0, "why": "Bikri, raftaar, stock cover, nateeje ka maap"},
        {"step": "Product catalog (SKU, price, rating)", "done": n_products > 0, "why": "Listing builder, review plan, break-even"},
        {"step": "SKU cost (COGS) darj", "done": n_costs > 0, "why": "Break-even ACOS aur munafa — iske bina scale band"},
        {"step": "Brand Analytics SQP file", "done": n_sqp > 0, "why": "Market share funnel — sabse keemti keyword data"},
        {"step": "API connector (SP-API/Ads)", "done": bool(connected), "why": "Roz ka data khud aaye, CSV ki zaroorat khatam"},
    ]
    tasks = []
    if pending: tasks.append({"priority": 1, "area": "approvals", "title": f"{pending} faisle tumhari approval ka intezaar kar rahe hain", "screen": "approvals"})
    st = ads_structure(store)
    if st["status"] == "OK":
        if st["wasted_spend"]: tasks.append({"priority": 1, "area": "ads", "title": f"₹{st['wasted_spend']:,.0f} bina-bikri wale terms par gaya — negatives lagao", "screen": "ads", "rule_id": "AMZ-A-03"})
        if st["harvest_pending"]: tasks.append({"priority": 2, "area": "ads", "title": f"{st['harvest_pending']} jeetne wale terms Exact me daalo", "screen": "ads", "rule_id": "AMZ-A-02"})
    sq = KI.sqp_funnel(db)
    if sq["available"]:
        c = sq["diagnosis_counts"]
        if c.get("SCALE_OPPORTUNITY"): tasks.append({"priority": 1, "area": "keywords", "title": f"{c['SCALE_OPPORTUNITY']} queries convert karti hain par dikhti nahi — scale karo", "screen": "sqp", "rule_id": "AMZ-Q-03"})
        if c.get("TILE_PROBLEM"): tasks.append({"priority": 2, "area": "listings", "title": f"{c['TILE_PROBLEM']} queries par click nahi milta — main image/title/price sudharo", "screen": "sqp", "rule_id": "AMZ-Q-02"})
    ev = event_calendar()
    nxt = ev["events"][0] if ev["events"] else None
    if nxt and nxt["days_to_start"] <= 45:
        tasks.append({"priority": 2 if nxt["days_to_start"] > 14 else 1, "area": "events",
                      "title": f"{nxt['event']}: {nxt['phase']} — FBA stock {nxt['fba_stock_by']} tak, taiyaari {nxt['ready_by']} tak",
                      "screen": "growth", "rule_id": "IN-E-01"})
    for i, c in enumerate(checklist):
        if not c["done"]:
            tasks.append({"priority": 3, "area": "setup", "title": c["step"] + " — " + c["why"], "screen": "integrations"})
            break
    tasks.sort(key=lambda x: x["priority"])
    br = AB.brain_report(db)
    return {"tasks": tasks[:8], "checklist": checklist, "setup_pct": round(sum(c["done"] for c in checklist) / len(checklist) * 100),
            "pending_approvals": pending, "next_event": nxt, "brain": {"rules": br["total_rules"], "by_status": br["by_status"],
                                                                     "own_data_lessons": br["own_data_lessons"]},
            "data": {"search_terms": n_terms, "order_lines": n_orders, "products": n_products, "costs": n_costs,
                     "sqp_rows": n_sqp, "last_import_at": last_import, "connectors": connected}}
