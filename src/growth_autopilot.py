"""Growth Autopilot (V25) — turns the gaps the playbook finds into APPROVAL-GATED PROPOSALS every day.

This closes the loop:
  data → growth_playbook finds a gap → autopilot creates a proposal (payload carries rule_ids + campaign/sku)
  → owner approves → applied → outcome_engine measures after 7/14 days → agent_brain updates confidence in those rules.

Safety rules (full-proof):
- The autopilot NEVER changes anything live itself — proposals only (tier ONE_TAP); with the kill switch ON the executor blocks.
- Idempotent: the same task (type + term/campaign + ISO week) is never proposed twice — daily runs do not duplicate.
- At most MAX_PER_RUN proposals per run — no flood in the approval inbox.
- No proposal for a rule the brain has DISABLED (lost 3 times in a row) — learning has a direct effect.
- Never negates a term that converted anywhere (ads_studio rule).
- Stock-out ad pauses are only proposed when the campaign name contains the SKU (no guessing which campaign to stop).
- Ads data older than STALE_ADS_DAYS → no negative/harvest proposals (acting on stale data is dangerous).
"""
import os, sys, json, hashlib, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12

MAX_PER_RUN = 15
STALE_ADS_DAYS = 21   # no negative/harvest proposals on ads data older than this

def _week(today=None):
    y, w, _ = (today or datetime.date.today()).isocalendar()
    return f"{y}-W{w:02d}"

def _key(kind, ident, week):
    return "AP-" + hashlib.sha256(f"{kind}|{ident}|{week}".encode()).hexdigest()[:24]

def _rule_ok(db, rule_id) -> bool:
    r = db.execute("SELECT status FROM playbook_rules WHERE rule_id=?", (rule_id,)).fetchone()
    return not r or r["status"] != "DISABLED"

def ads_data_age(db, today=None):
    """How old the ads data is: the latest search_terms period_end or ads import date — whichever is newer.
    None if unknown (undated CLI import) — proposals are still created, labelled 'AGE_UNKNOWN'."""
    t = today or datetime.date.today()
    cands = []
    r = db.execute("SELECT MAX(period_end) m FROM search_terms WHERE period_end IS NOT NULL AND period_end<>''").fetchone()
    if r and r["m"]: cands.append(str(r["m"])[:10])
    r = db.execute("""SELECT MAX(imported_at) m FROM import_batches
                      WHERE report_type IN ('search_terms','ads_search_terms','campaigns')""").fetchone()
    if r and r["m"]: cands.append(str(r["m"])[:10])
    if not cands: return None
    try: return (t - datetime.date.fromisoformat(max(cands))).days
    except ValueError: return None

def run(store, today=None, dry_run: bool = False) -> dict:
    """Daily autopilot. dry_run=True only reports what would be created (dashboard preview)."""
    import actions as ACT, growth_playbook as GP, keyword_intel as KI, agent_brain as AB, ads_studio as AS
    db = store.db; ensure_v12(db); AB.ensure_brain(db)
    week = _week(today)
    plans, skipped = [], []
    expired = {"expired": 0} if dry_run else ACT.expire_stale(db)
    age = ads_data_age(db, today)
    ads_fresh = age is None or age <= STALE_ADS_DAYS
    freshness = ("AGE_UNKNOWN" if age is None else f"{age} days old")

    def plan(kind, ident, payload, rule_id, why, predicted):
        if not _rule_ok(db, rule_id):
            skipped.append({"kind": kind, "ident": ident, "why": f"rule {rule_id} is DISABLED in the brain (lost 3 times in a row)"}); return
        payload = {**payload, "rule_ids": [rule_id], "source": "growth_autopilot", "week": week, "why": why,
                   "data_freshness": freshness}
        plans.append({"kind": kind, "ident": ident, "payload": payload, "key": _key(kind, ident, week), "predicted": predicted})

    st = GP.ads_structure(store)
    if st["status"] == "OK" and not ads_fresh:
        skipped.append({"kind": "ADS_ALL", "ident": "-", "why": f"Ads data is {age} days old (limit {STALE_ADS_DAYS}) — "
                                                                "negatives/harvest on stale data are risky; upload a fresh Search Term report"})
    if st["status"] == "OK" and ads_fresh:
        hv = AS.harvest_candidates(store)
        # 1) Negatives — only terms that never converted anywhere (AMZ-A-03)
        for n in sorted(hv["negatives"], key=lambda x: -x["wasted"]):
            plan("ADD_NEGATIVE_EXACT", f"{n['campaign']}|{n['term']}",
                 {"campaign": n["campaign"], "term": n["term"], "match": "NEGATIVE_EXACT", "wasted": n["wasted"]},
                 "AMZ-A-03", f"₹{n['wasted']} spent, 0 orders anywhere",
                 f"This campaign's ROAS should improve within 7/14 days (towards ₹{n['wasted']} saved)")
        # 2) Harvest — winning terms into Exact + negative in the source (AMZ-A-02)
        exact = {x["name"] for x in st["campaigns"] if x["type"] == "EXACT"}
        for f in st["findings"]:
            if f.get("code") == "HARVEST_PENDING":
                for h in f["terms"]:
                    plan("HARVEST_TO_EXACT", f"{h['from_campaign']}|{h['term']}",
                         {"campaign": h["from_campaign"], "term": h["term"], "orders": h["orders"],
                          "target_campaign": sorted(exact)[0] if exact else None,
                          "steps": ["Add the keyword to an Exact campaign", "Add it as negative-exact in the source campaign"]},
                         "AMZ-A-02", f"{h['orders']} orders — currently only in {h['from_campaign']}",
                         "Source campaign ROAS improves; spend on this term comes under control")
            # 3) Self-competition — negative in Auto/Broad (AMZ-A-02)
            if f.get("code") == "SELF_COMPETITION":
                for o in f["terms"]:
                    for c in o["campaigns"]:
                        if c not in exact:
                            plan("ADD_NEGATIVE_EXACT", f"{c}|{o['term']}",
                                 {"campaign": c, "term": o["term"], "match": "NEGATIVE_EXACT",
                                  "reason": "Already in Exact — here you are bidding against yourself"},
                                 "AMZ-A-02", "Term already exists in an Exact campaign", "This campaign's ROAS improves")
    # 4) SQP scale — converts but is not seen (AMZ-Q-03)
    sq = KI.sqp_funnel(db)
    if sq["available"]:
        for q in sq["queries"]:
            if q["diagnosis"] == "SCALE_OPPORTUNITY":
                plan("SCALE_QUERY", q["query"], {"query": q["query"], "shares": q["shares"],
                                                 "steps": ["Check margin (Growth → break-even ACOS)", "Raise Exact keyword bid +10-20%", "Lock it into title/backend"]},
                     "AMZ-Q-03", "Purchase share > impression share, impression share small", "Impression and purchase share for this query should grow")
            elif q["diagnosis"] == "TILE_PROBLEM":
                plan("FIX_SEARCH_TILE", q["query"], {"query": q["query"], "shares": q["shares"],
                                                     "steps": ["Main image (AMZ-I-01)", "First 40 characters of the title", "Price per 100g", "Reviews/badge"]},
                     "AMZ-Q-02", "Seen but not clicked", "Click share should grow")
    # 5) Stock-out guard — ads without stock burn money
    stock = {r["sku"]: r["q"] for r in db.execute("SELECT sku, SUM(COALESCE(sellable_qty, qty)) q FROM inventory GROUP BY sku")}
    camps = [r["name"] for r in db.execute("SELECT name FROM campaigns WHERE spend>0")]
    for sku, q in stock.items():
        if q is not None and q <= 0:
            for c in camps:
                if sku and sku.lower() in c.lower():
                    plan("PAUSE_CAMPAIGN", f"{c}|stockout", {"kind": "PAUSE_CAMPAIGN", "campaign": c, "sku": sku,
                                                             "reason": "SKU has 0 sellable stock"},
                         "AMZ-A-03", f"{sku} has 0 stock — ad spend is wasted", "Resume proposal once stock arrives")

    # Every type gets room within the cap, in turn (round-robin) — otherwise 30 negatives would crowd out the
    # revenue-growing harvest/scale proposals forever. Stock-out pauses first (money is burning right now).
    order = ["PAUSE_CAMPAIGN", "HARVEST_TO_EXACT", "ADD_NEGATIVE_EXACT", "SCALE_QUERY", "FIX_SEARCH_TILE"]
    buckets = {k: [x for x in plans if x["kind"] == k] for k in order}
    mixed = []
    while any(buckets.values()):
        for k in order:
            if buckets[k]: mixed.append(buckets[k].pop(0))
    plans = mixed
    created, dup = [], 0
    for p in plans[:MAX_PER_RUN]:
        if dry_run: created.append({k: p[k] for k in ("kind", "ident", "predicted")}); continue
        r = ACT.create_proposal(db, p["kind"], "Amazon", "default", p["payload"], "ONE_TAP", "A06-autopilot",
                                p["key"], p["predicted"])
        if r["duplicate"]: dup += 1
        else: created.append({"id": r["id"], "kind": p["kind"], "ident": p["ident"]})
    return {"week": week, "dry_run": dry_run, "candidates": len(plans), "created": created,
            "already_proposed_this_week": dup, "capped": max(0, len(plans) - MAX_PER_RUN),
            "skipped_disabled_rules": [x for x in skipped if x["kind"] != "ADS_ALL"],
            "skipped_stale_data": [x for x in skipped if x["kind"] == "ADS_ALL"],
            "ads_data_age_days": age, "expired_old_proposals": expired["expired"],
            "note": "The autopilot only creates proposals — live changes stay behind approval + the kill switch"}

def weekly_report(store, today=None) -> dict:
    """Every Sunday: what happened this week — proposals, outcomes, brain changes, upcoming events."""
    import growth_playbook as GP, agent_brain as AB
    db = store.db; ensure_v12(db)
    t = today or datetime.date.today()
    since = (t - datetime.timedelta(days=7)).isoformat()
    props = [dict(r) for r in db.execute("SELECT kind, state, COUNT(*) n FROM action_v12 WHERE created_at>=? GROUP BY kind, state", (since,))]
    outs = [dict(r) for r in db.execute("""SELECT kind, attribution, SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) wins, COUNT(*) n
                                           FROM outcomes WHERE measured_at>=? GROUP BY kind, attribution""", (since,))]
    br = AB.brain_report(db)
    ev = GP.event_calendar(t, horizon_days=45)
    st = GP.ads_structure(store)
    lines = [f"# NutriScale — Weekly Growth Report ({t.isoformat()})", "",
             "## Proposals this week"] + ([f"- {p['kind']} · {p['state']}: {p['n']}" for p in props] or ["- none"]) + \
            ["", "## Measured outcomes (only VERIFIED ones drive learning)"] + \
            ([f"- {o['kind']} · {o['attribution']}: {o['wins']}/{o['n']} wins" for o in outs] or ["- none yet"]) + \
            ["", "## Agent Brain", f"- Rules: {br['total_rules']} (active {br['by_status'].get('ACTIVE', 0)}, disabled {br['by_status'].get('DISABLED', 0)})",
             f"- Lessons from your data: {br['own_data_lessons']}"] + \
            [f"- {r['rule_id']}: confidence {round(r['prior']*100)}% → {round(r['confidence']*100)}% ({r['wins']}/{r['wins']+r['losses']})" for r in br["rules_moved_by_results"][:5]] + \
            ["", "## Ads structure"] + ([f"- Score {st['structure_score']}/100, wasted spend ₹{st['wasted_spend']:,.0f}, harvest pending {st['harvest_pending']}"]
                                        if st["status"] == "OK" else ["- no campaign data"]) + \
            ["", "## Events in the next 45 days (ESTIMATED dates)"] + \
            ([f"- {e['event']}: {e['start']} · FBA stock by {e['fba_stock_by']} · {e['phase']}" for e in ev["events"]] or ["- none"])
    md = "\n".join(lines) + "\n"
    from db_store import DEFAULT_PATH
    path = getattr(store, "path", None) or DEFAULT_PATH
    saved = None
    if path != ":memory:":
        d = os.path.join(os.path.dirname(os.path.abspath(path)), "reports"); os.makedirs(d, exist_ok=True)
        saved = os.path.join(d, f"weekly-{t.isoformat()}.md")
        with open(saved, "w") as fh: fh.write(md)
    return {"markdown": md, "saved_to": saved, "proposals": props, "outcomes": outs}
