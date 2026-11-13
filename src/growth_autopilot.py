"""Growth Autopilot (V25) — playbook ki pakdi kamiyon ko roz APPROVAL-WALE PROPOSALS me badalna.

Isse chakra poora hota hai:
  data → growth_playbook pakadta hai → autopilot proposal banata hai (payload me rule_ids + campaign/sku)
  → malik approve → lagu → outcome_engine 7/14 din me maapta hai → agent_brain un niyamo ka bharosa badalta hai.

Suraksha ke niyam (full-proof):
- Autopilot KABHI khud kuch live nahi karta — sirf proposal (tier ONE_TAP); kill switch ON ho to executor rokega.
- Idempotent: ek hi kaam (prakar + term/campaign + ISO hafta) dobara proposal nahi banata — roz chalane par dohraav nahi.
- Ek run me zyada se zyada MAX_PER_RUN proposals — approval inbox me baadh nahi.
- Jo niyam brain me DISABLED hai (3 baar haara), us niyam par proposal nahi banta — seekh ka asar seedha.
- Jo term kahin bhi convert hua hai uspar negative KABHI nahi (ads_studio ka niyam).
- Stock-out SKU ke ads pause ka proposal sirf tab jab campaign naam me SKU ho (andaaz se galat campaign band nahi).
"""
import os, sys, json, hashlib, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12

MAX_PER_RUN = 15

def _week(today=None):
    y, w, _ = (today or datetime.date.today()).isocalendar()
    return f"{y}-W{w:02d}"

def _key(kind, ident, week):
    return "AP-" + hashlib.sha256(f"{kind}|{ident}|{week}".encode()).hexdigest()[:24]

def _rule_ok(db, rule_id) -> bool:
    r = db.execute("SELECT status FROM playbook_rules WHERE rule_id=?", (rule_id,)).fetchone()
    return not r or r["status"] != "DISABLED"

def run(store, today=None, dry_run: bool = False) -> dict:
    """Roz ka autopilot. dry_run=True: sirf batata hai kya banega (dashboard preview)."""
    import actions as ACT, growth_playbook as GP, keyword_intel as KI, agent_brain as AB, ads_studio as AS
    db = store.db; ensure_v12(db); AB.ensure_brain(db)
    week = _week(today)
    plans, skipped = [], []

    def plan(kind, ident, payload, rule_id, why, predicted):
        if not _rule_ok(db, rule_id):
            skipped.append({"kind": kind, "ident": ident, "why": f"niyam {rule_id} brain me DISABLED hai (3 baar haara)"}); return
        payload = {**payload, "rule_ids": [rule_id], "source": "growth_autopilot", "week": week, "why": why}
        plans.append({"kind": kind, "ident": ident, "payload": payload, "key": _key(kind, ident, week), "predicted": predicted})

    st = GP.ads_structure(store)
    if st["status"] == "OK":
        hv = AS.harvest_candidates(store)
        # 1) Negatives — sirf woh terms jo kahin convert nahi hue (AMZ-A-03)
        for n in sorted(hv["negatives"], key=lambda x: -x["wasted"]):
            plan("ADD_NEGATIVE_EXACT", f"{n['campaign']}|{n['term']}",
                 {"campaign": n["campaign"], "term": n["term"], "match": "NEGATIVE_EXACT", "wasted": n["wasted"]},
                 "AMZ-A-03", f"₹{n['wasted']} kharch, kahin bhi 0 order",
                 f"Is campaign ka ROAS 7/14 din me badhna chahiye (₹{n['wasted']} bachat ki disha)")
        # 2) Harvest — jeetne wale terms Exact me + source me negative (AMZ-A-02)
        exact = {x["name"] for x in st["campaigns"] if x["type"] == "EXACT"}
        for f in st["findings"]:
            if f["rule_id"] == "AMZ-A-02" and f.get("terms") and "Exact me nahi" in f["message"]:
                for h in f["terms"]:
                    plan("HARVEST_TO_EXACT", f"{h['from_campaign']}|{h['term']}",
                         {"campaign": h["from_campaign"], "term": h["term"], "orders": h["orders"],
                          "target_campaign": sorted(exact)[0] if exact else None,
                          "steps": ["Exact campaign me keyword jodo", "source campaign me negative-exact lagao"]},
                         "AMZ-A-02", f"{h['orders']} orders — abhi sirf {h['from_campaign']} me",
                         "Source campaign ka ROAS sudhrega; term ka kharch kaabu me")
            # 3) Self-competition — Auto/Broad me negative (AMZ-A-02)
            if f["rule_id"] == "AMZ-A-02" and f.get("terms") and "apni hi bid" in f["message"]:
                for o in f["terms"]:
                    for c in o["campaigns"]:
                        if c not in exact:
                            plan("ADD_NEGATIVE_EXACT", f"{c}|{o['term']}",
                                 {"campaign": c, "term": o["term"], "match": "NEGATIVE_EXACT",
                                  "reason": "Exact me pehle se — yahan apni hi bid se ladai"},
                                 "AMZ-A-02", "Exact campaign me pehle se maujud term", "Is campaign ka ROAS sudhrega")
    # 4) SQP scale — convert karti hai par dikhti nahi (AMZ-Q-03)
    sq = KI.sqp_funnel(db)
    if sq["available"]:
        for q in sq["queries"]:
            if q["diagnosis"] == "SCALE_OPPORTUNITY":
                plan("SCALE_QUERY", q["query"], {"query": q["query"], "shares": q["shares"],
                                                 "steps": ["Margin parkho (Growth → break-even ACOS)", "Exact keyword bid +10-20%", "Title/backend me pakka karo"]},
                     "AMZ-Q-03", "Purchase share > impression share, impression share chhota", "Is query ka impression aur purchase share badhna chahiye")
            elif q["diagnosis"] == "TILE_PROBLEM":
                plan("FIX_SEARCH_TILE", q["query"], {"query": q["query"], "shares": q["shares"],
                                                     "steps": ["Main image (AMZ-I-01)", "Title ke pehle 40 akshar", "Price per 100g", "Reviews/badge"]},
                     "AMZ-Q-02", "Dikhta hai par click nahi", "Click share badhna chahiye")
    # 5) Stock-out guard — bina stock ads ka paisa jalta hai
    stock = {r["sku"]: r["q"] for r in db.execute("SELECT sku, SUM(COALESCE(sellable_qty, qty)) q FROM inventory GROUP BY sku")}
    camps = [r["name"] for r in db.execute("SELECT name FROM campaigns WHERE spend>0")]
    for sku, q in stock.items():
        if q is not None and q <= 0:
            for c in camps:
                if sku and sku.lower() in c.lower():
                    plan("PAUSE_CAMPAIGN", f"{c}|stockout", {"kind": "PAUSE_CAMPAIGN", "campaign": c, "sku": sku,
                                                             "reason": "SKU ka bechne-yogya stock 0"},
                         "AMZ-A-03", f"{sku} ka stock 0 — ads ka kharch bekaar", "Stock aate hi resume proposal")

    # Seema me sab prakar ko jagah: baari-baari (round-robin) — warna 30 negatives kamai badhane wale
    # harvest/scale proposals ko kabhi aane hi nahi dete. Stock-out pause sabse pehle (paisa abhi jal raha hai).
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
            "skipped_disabled_rules": skipped,
            "note": "Autopilot sirf proposals banata hai — live badlav approval + kill switch ke peeche"}

def weekly_report(store, today=None) -> dict:
    """Har Sunday: is hafte kya hua — proposals, nateeje, brain ka badlav, agle hafte ke event."""
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
    lines = [f"# NutriScale — Haftawar Growth Report ({t.isoformat()})", "",
             "## Is hafte ke proposals"] + ([f"- {p['kind']} · {p['state']}: {p['n']}" for p in props] or ["- koi nahi"]) + \
            ["", "## Maape gaye nateeje (VERIFIED hi seekh banate hain)"] + \
            ([f"- {o['kind']} · {o['attribution']}: {o['wins']}/{o['n']} jeet" for o in outs] or ["- abhi koi nahi"]) + \
            ["", "## Agent Brain", f"- Niyam: {br['total_rules']} (active {br['by_status'].get('ACTIVE', 0)}, disabled {br['by_status'].get('DISABLED', 0)})",
             f"- Apne data se sabak: {br['own_data_lessons']}"] + \
            [f"- {r['rule_id']}: bharosa {round(r['prior']*100)}% → {round(r['confidence']*100)}% ({r['wins']}/{r['wins']+r['losses']})" for r in br["rules_moved_by_results"][:5]] + \
            ["", "## Ads structure"] + ([f"- Score {st['structure_score']}/100, bekaar kharch ₹{st['wasted_spend']:,.0f}, harvest baaki {st['harvest_pending']}"]
                                        if st["status"] == "OK" else ["- campaign data nahi"]) + \
            ["", "## Agle 45 din ke events (ANUMAAN tareekhein)"] + \
            ([f"- {e['event']}: {e['start']} · FBA stock {e['fba_stock_by']} tak · {e['phase']}" for e in ev["events"]] or ["- koi nahi"])
    md = "\n".join(lines) + "\n"
    from db_store import DEFAULT_PATH
    path = getattr(store, "path", None) or DEFAULT_PATH
    saved = None
    if path != ":memory:":
        d = os.path.join(os.path.dirname(os.path.abspath(path)), "reports"); os.makedirs(d, exist_ok=True)
        saved = os.path.join(d, f"weekly-{t.isoformat()}.md")
        with open(saved, "w") as fh: fh.write(md)
    return {"markdown": md, "saved_to": saved, "proposals": props, "outcomes": outs}
