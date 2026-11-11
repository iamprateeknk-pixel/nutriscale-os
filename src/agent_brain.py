"""Agent Brain (V23) — agents ki pakki yaaddasht + khud seekhne ka chakra.

Kya karta hai:
1. PLAYBOOK: marketplace_knowledge ke niyam DB me (playbook_rules) — har niyam ka bharosa = source ka PRIOR.
2. NATEEJO SE SEEKH: outcome_engine ke VERIFIED nateeje (sirf VERIFIED — CONTAMINATED/LOW_COVERAGE nahi) jis action
   ke payload me `rule_ids` the, un niyamo ka bharosa Bayesian tareeke se badalta hai:
       confidence = (prior * K + wins) / (K + wins + losses),  K = 4 (prior ka wazan 4 nateejo jitna)
   Lagatar 3 haar = DISABLED (insaan dobara chalu kare). Kam bharosa = PROBATION (agent sirf salah dega).
3. APNE DATA SE SEEKH: search terms / SQP / listing audit se naye sabak khud banta hai (source = OWN_DATA),
   har run par UPDATE hota hai — dohraav nahi, aur saboot ki ginati ke saath.
4. ADVISE: agent kaam se pehle puchta hai "mere topic par abhi kaunse niyam bharose-layak hain".

Imaandaari: brain kabhi khud live badlav nahi karta — sirf salah/proposal, approval gate wahi rehta hai.
"""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc
import marketplace_knowledge as MK

PRIOR_WEIGHT = 4
DISABLE_AFTER_LOSSES = 3

def ensure_brain(db):
    ensure_v12(db)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS playbook_rules(
      rule_id TEXT PRIMARY KEY, platform TEXT, topic TEXT, agents TEXT, statement TEXT, action TEXT,
      source_status TEXT, sources TEXT, prior REAL, wins INT DEFAULT 0, losses INT DEFAULT 0,
      consecutive_losses INT DEFAULT 0, confidence REAL, status TEXT DEFAULT 'ACTIVE',
      evidence TEXT, origin TEXT, checked_on TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS learning_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, rule_id TEXT, event TEXT, outcome_id INT,
      detail TEXT, at TEXT, UNIQUE(rule_id, event, outcome_id));
    """); db.commit()

def _status(conf, consecutive_losses, current="ACTIVE"):
    if current == "DISABLED": return "DISABLED"
    if consecutive_losses >= DISABLE_AFTER_LOSSES: return "DISABLED"
    if conf < 0.4: return "PROBATION"
    return "ACTIVE"

def _confidence(prior, wins, losses):
    return round((prior * PRIOR_WEIGHT + wins) / (PRIOR_WEIGHT + wins + losses), 3)

def seed_playbook(db) -> dict:
    """Research wale niyam playbook me — naye jodo, purane ka text/source taaza karo, seekha hua (wins/losses) kabhi mat mitao."""
    ensure_brain(db); added = refreshed = 0
    for r in MK.KNOWLEDGE:
        ex = db.execute("SELECT wins, losses, consecutive_losses, status FROM playbook_rules WHERE rule_id=?", (r["id"],)).fetchone()
        if ex:
            conf = _confidence(r["reliability"], ex["wins"], ex["losses"])
            db.execute("""UPDATE playbook_rules SET statement=?, action=?, source_status=?, sources=?, prior=?, confidence=?,
                          checked_on=?, updated_at=? WHERE rule_id=?""",
                       (r["rule"], r["action"], r["status"], json.dumps(r["sources"]), r["reliability"], conf,
                        r["checked_on"], now_utc(), r["id"])); refreshed += 1
        else:
            db.execute("""INSERT INTO playbook_rules(rule_id,platform,topic,agents,statement,action,source_status,sources,prior,
                          confidence,status,origin,checked_on,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?, 'ACTIVE','RESEARCH',?,?)""",
                       (r["id"], r["platform"], r["topic"], ",".join(r["agents"]), r["rule"], r["action"], r["status"],
                        json.dumps(r["sources"]), r["reliability"], r["reliability"], r["checked_on"], now_utc())); added += 1
    db.commit()
    return {"added": added, "refreshed": refreshed}

def learn_from_outcomes(db) -> dict:
    """Sirf VERIFIED nateeje. Har (rule, outcome) jod ek hi baar gina jata hai (learning_events UNIQUE)."""
    ensure_brain(db)
    cols = [c[1] for c in db.execute("PRAGMA table_info(outcomes)")]
    if "attribution" not in cols: return {"applied": 0, "note": "outcomes me attribution column nahi"}
    rows = db.execute("""SELECT o.id oid, o.success, o.kind, a.payload FROM outcomes o JOIN action_v12 a ON a.id=o.action_id
                         WHERE o.attribution='VERIFIED' AND o.success IS NOT NULL ORDER BY o.id""").fetchall()
    applied, skipped_no_rules = 0, 0
    for r in rows:
        try: rule_ids = json.loads(r["payload"] or "{}").get("rule_ids") or []
        except Exception: rule_ids = []
        if not rule_ids: skipped_no_rules += 1; continue
        for rid in rule_ids:
            pr = db.execute("SELECT * FROM playbook_rules WHERE rule_id=?", (rid,)).fetchone()
            if not pr: continue
            try:
                db.execute("INSERT INTO learning_events(rule_id,event,outcome_id,detail,at) VALUES (?,?,?,?,?)",
                           (rid, "WIN" if r["success"] else "LOSS", r["oid"], f"kind={r['kind']}", now_utc()))
            except Exception:
                continue  # yeh nateeja pehle hi gina ja chuka
            w, l = pr["wins"] + (1 if r["success"] else 0), pr["losses"] + (0 if r["success"] else 1)
            cl = 0 if r["success"] else pr["consecutive_losses"] + 1
            conf = _confidence(pr["prior"], w, l)
            db.execute("UPDATE playbook_rules SET wins=?, losses=?, consecutive_losses=?, confidence=?, status=?, updated_at=? WHERE rule_id=?",
                       (w, l, cl, conf, _status(conf, cl, pr["status"]), now_utc(), rid))
            applied += 1
    db.commit()
    return {"applied": applied, "verified_outcomes": len(rows), "outcomes_without_rule_ids": skipped_no_rules}

def _upsert_own(db, rid, platform, topic, agents, statement, action, evidence: dict, prior: float):
    ex = db.execute("SELECT wins, losses, status FROM playbook_rules WHERE rule_id=?", (rid,)).fetchone()
    if ex:
        db.execute("""UPDATE playbook_rules SET statement=?, action=?, evidence=?, prior=?, confidence=?, updated_at=? WHERE rule_id=?""",
                   (statement, action, json.dumps(evidence, ensure_ascii=False), prior,
                    _confidence(prior, ex["wins"], ex["losses"]), now_utc(), rid))
    else:
        db.execute("""INSERT INTO playbook_rules(rule_id,platform,topic,agents,statement,action,source_status,sources,prior,confidence,
                      status,evidence,origin,checked_on,updated_at) VALUES (?,?,?,?,?,?, 'OWN_DATA','[]',?,?, 'ACTIVE',?, 'OWN_DATA',?,?)""",
                   (rid, platform, topic, agents, statement, action, prior, prior, json.dumps(evidence, ensure_ascii=False),
                    datetime.date.today().isoformat(), now_utc()))

def learn_from_data(store, min_orders: int = 3) -> dict:
    """Apne asal data se sabak — kaunse shabd bechte hain, kaunse paisa khaate hain, SQP kya keh raha hai."""
    db = store.db; ensure_brain(db)
    lessons = 0
    terms = [dict(r) for r in db.execute("""SELECT term, SUM(clicks) cl, SUM(purchases) pu, SUM(spend) sp, SUM(sales) sa
                                            FROM search_terms GROUP BY term""")]
    tot_cl = sum(t["cl"] or 0 for t in terms); tot_pu = sum(t["pu"] or 0 for t in terms)
    avg_cvr = tot_pu / tot_cl if tot_cl else 0
    winners = [t for t in terms if (t["pu"] or 0) >= min_orders and t["cl"] and t["pu"] / t["cl"] >= avg_cvr]
    winners.sort(key=lambda t: -(t["pu"] or 0))
    if winners:
        top = winners[:8]
        # Saboot jitna zyada, prior utna (0.55..0.85) — par asal pushti nateejo se hi
        prior = round(min(0.85, 0.55 + 0.03 * sum(t["pu"] for t in top) / max(1, len(top))), 2)
        _upsert_own(db, "OWN-KW-WINNERS", "Amazon", "keyword_research", "A03,A04",
                    "Apne data me ye terms ausat se behtar convert karte hain: " + ", ".join(t["term"] for t in top),
                    "Title/Item Highlights me pehle inhi ko jagah do; exact-match ads me alag rakho",
                    {"terms": [{"term": t["term"], "orders": t["pu"], "clicks": t["cl"],
                                "cvr_pct": round(t["pu"] / t["cl"] * 100, 1)} for t in top],
                     "account_avg_cvr_pct": round(avg_cvr * 100, 2)}, prior); lessons += 1
    losers = sorted([t for t in terms if (t["sp"] or 0) >= 200 and not t["pu"]], key=lambda t: -(t["sp"] or 0))
    if losers:
        _upsert_own(db, "OWN-KW-WASTE", "Amazon", "ads", "A06,A03",
                    "Ye terms paisa khaate hain, bikri nahi: " + ", ".join(t["term"] for t in losers[:8]),
                    "Negative keyword proposal banao (approval ke saath); listing me in shabdon ki zaroorat nahi",
                    {"terms": [{"term": t["term"], "spend": round(t["sp"], 2), "clicks": t["cl"]} for t in losers[:15]],
                     "total_wasted": round(sum(t["sp"] for t in losers), 2)}, 0.75); lessons += 1
    import keyword_intel as KI
    f = KI.sqp_funnel(db)
    if f["available"]:
        for diag, rid, act in (("SCALE_OPPORTUNITY", "OWN-SQP-SCALE", "In queries par ads/bid badhao (margin parkh kar)"),
                               ("TILE_PROBLEM", "OWN-SQP-TILE", "Main image/title/price sudharo — dikhte ho par click nahi milta"),
                               ("OFFER_PROBLEM", "OWN-SQP-OFFER", "Price/A+/reviews/delivery sudharo — click ke baad bikri nahi")):
            qs = [q for q in f["queries"] if q["diagnosis"] == diag]
            if qs:
                _upsert_own(db, rid, "Amazon", "keyword_research", "A03,A04,A06",
                            f"SQP ke hisaab se {diag}: " + ", ".join(q["query"] for q in qs[:8]), act,
                            {"queries": [{"query": q["query"], "shares": q["shares"]} for q in qs[:15]]}, 0.7); lessons += 1
    db.commit()
    return {"lessons_updated": lessons, "terms_seen": len(terms),
            "note": "Data nahi to sabak nahi — koi nakli seekh nahi banti" if not terms and not f["available"] else ""}

def record_listing_audit(db, sku: str, audit: dict):
    """Listing audit ke baar-baar aane wale issues bhi sabak hain (kaunsa niyam sabse zyada toot-ta hai)."""
    ensure_brain(db)
    for i in audit.get("issues", []):
        try:
            db.execute("INSERT INTO learning_events(rule_id,event,outcome_id,detail,at) VALUES (?,?,?,?,?)",
                       (i["rule_id"], "AUDIT_" + i["severity"], None, f"{sku}: {i['message'][:150]}", now_utc()))
        except Exception:
            pass
    db.commit()

def advise(db, agent: str = None, topic: str = None, platform: str = None, include_probation: bool = False) -> list:
    """Agent ke liye abhi bharose-layak niyam, sabse zyada bharose wale pehle."""
    ensure_brain(db)
    q = "SELECT * FROM playbook_rules WHERE status IN (" + ("'ACTIVE','PROBATION'" if include_probation else "'ACTIVE'") + ")"
    args = []
    if agent: q += " AND (',' || agents || ',') LIKE ?"; args.append(f"%,{agent},%")
    if topic: q += " AND topic=?"; args.append(topic)
    if platform: q += " AND platform IN (?, 'ALL')"; args.append(platform)
    q += " ORDER BY confidence DESC"
    out = []
    for r in db.execute(q, args):
        d = dict(r); d["sources"] = json.loads(d["sources"] or "[]")
        d["evidence"] = json.loads(d["evidence"]) if d.get("evidence") else None
        out.append(d)
    return out

def reenable(db, rule_id: str, by: str) -> dict:
    """DISABLED niyam sirf insaan chalu kar sakta hai — lagatar-haar ka record saaf, seekha hua itihaas wahi."""
    ensure_brain(db)
    cur = db.execute("UPDATE playbook_rules SET status='PROBATION', consecutive_losses=0, updated_at=? WHERE rule_id=? AND status='DISABLED'",
                     (now_utc(), rule_id))
    db.execute("INSERT OR IGNORE INTO learning_events(rule_id,event,outcome_id,detail,at) VALUES (?,?,?,?,?)",
               (rule_id, "REENABLED", None, f"by {by}", now_utc())); db.commit()
    return {"ok": cur.rowcount == 1, "rule_id": rule_id}

def brain_report(db) -> dict:
    ensure_brain(db)
    rules = [dict(r) for r in db.execute("SELECT rule_id, origin, status, confidence, prior, wins, losses, agents FROM playbook_rules")]
    per_agent = {}
    for r in rules:
        for a in (r["agents"] or "").split(","):
            if not a: continue
            pa = per_agent.setdefault(a, {"rules": 0, "active": 0, "wins": 0, "losses": 0, "own_data_lessons": 0})
            pa["rules"] += 1; pa["active"] += r["status"] == "ACTIVE"
            pa["wins"] += r["wins"] or 0; pa["losses"] += r["losses"] or 0
            pa["own_data_lessons"] += r["origin"] == "OWN_DATA"
    from self_learning import strength_score
    for a, pa in per_agent.items():
        pa["strength"] = strength_score(pa["wins"], pa["losses"], pa["rules"], 0)["strength_score"]
    moved = sorted([r for r in rules if r["wins"] or r["losses"]], key=lambda r: abs(r["confidence"] - r["prior"]), reverse=True)[:10]
    stale = MK.stale_rules()
    top_broken = [dict(r) for r in db.execute("""SELECT rule_id, COUNT(*) n FROM learning_events WHERE event LIKE 'AUDIT_BLOCK'
                                                  GROUP BY rule_id ORDER BY n DESC LIMIT 5""")]
    return {"total_rules": len(rules),
            "by_status": {s: sum(1 for r in rules if r["status"] == s) for s in ("ACTIVE", "PROBATION", "DISABLED")},
            "own_data_lessons": sum(1 for r in rules if r["origin"] == "OWN_DATA"),
            "per_agent": per_agent, "rules_moved_by_results": moved,
            "most_broken_in_audits": top_broken,
            "stale_research_rules": stale,
            "note": "Bharosa sirf VERIFIED nateejo se badalta hai; research niyam 90 din me dobara parkho"}

def daily_learning_cycle(store) -> dict:
    db = store.db
    s = seed_playbook(db)
    MK.seed_knowledge(store)
    o = learn_from_outcomes(db)
    d = learn_from_data(store)
    return {"playbook": s, "outcomes": o, "own_data": d}
