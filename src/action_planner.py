"""Action Planner — a ready 'what to do today' list from real DB data.
The audit says what is wrong; the planner says which button to press, in which order.
Each item comes with estimated savings/impact — to make the decision easy.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db_store import Store

def build_plan(store: Store, min_waste_spend: float = 50.0, neg_min_spend: float = 80.0) -> dict:
    db = store.db
    plan = {"pause": [], "scale": [], "watch": [], "negatives": [], "savings_est": 0.0}
    camps = [dict(r) for r in db.execute("SELECT * FROM campaigns ORDER BY spend DESC")]
    total_spend = sum(c["spend"] for c in camps)
    for c in camps:
        roas = c["sales"] / c["spend"] if c["spend"] else 0
        if c["sales"] == 0 and c["spend"] >= min_waste_spend:
            plan["pause"].append({"campaign": c["name"], "spend": round(c["spend"]),
                                   "reason": "Not a single sale in the whole period — money is burning"})
            plan["savings_est"] += c["spend"]
        elif roas >= 2.5 and c["spend"] >= 200:
            plan["scale"].append({"campaign": c["name"], "spend": round(c["spend"]), "roas": round(roas, 1),
                                  "suggest": "Budget +30% — this is what earns money, feed it first"})
        elif 0 < roas < 1.0 and c["spend"] >= 300:
            plan["watch"].append({"campaign": c["name"], "spend": round(c["spend"]), "roas": round(roas, 1),
                                  "suggest": "ROAS below 1 — cut bid -20% and watch for 7 days; pause if it does not improve"})
    neg = {}
    for r in db.execute("""SELECT campaign, term, SUM(spend) sp FROM search_terms
                           GROUP BY campaign, term HAVING SUM(purchases)=0 AND SUM(spend)>=?""", (neg_min_spend,)):
        neg.setdefault(r["campaign"], []).append({"term": r["term"], "wasted": round(r["sp"])})
    plan["negatives"] = [{"campaign": k, "terms": sorted(v, key=lambda x: -x["wasted"])} for k, v in neg.items()]
    plan["negative_waste"] = round(sum(t["wasted"] for v in neg.values() for t in v))
    plan["total_spend"] = round(total_spend)
    plan["savings_est"] = round(plan["savings_est"])
    return plan

def render_markdown(plan: dict, title_date: str = "") -> str:
    L = [f"# Action Plan {title_date}", "",
         f"Total ad spend (report): **₹{plan['total_spend']:,}** · Estimated savings from pauses alone: **₹{plan['savings_est']:,}/cycle**", "",
         "## 1) PAUSE (zero sales, money is burning)"]
    L += [f"- [ ] **{p['campaign']}** — ₹{p['spend']:,} spent, 0 sales. {p['reason']}" for p in plan["pause"]] or ["- (none)"]
    L += ["", "## 2) SCALE (these earn money)"]
    L += [f"- [ ] **{s['campaign']}** — ROAS {s['roas']} · {s['suggest']}" for s in plan["scale"]] or ["- (none — improve conversion first)"]
    L += ["", "## 3) LOWER BIDS and watch"]
    L += [f"- [ ] **{w['campaign']}** — ROAS {w['roas']} · {w['suggest']}" for w in plan["watch"]] or ["- (none)"]
    L += ["", f"## 4) Add NEGATIVE keywords (total waste ₹{plan['negative_waste']:,})", "_These terms spent money with zero orders — add them as Exact Negative:_"]
    for g in plan["negatives"]:
        L.append(f"- **{g['campaign']}**: " + ", ".join(f"{t['term']} (₹{t['wasted']:,})" for t in g["terms"]))
    if not plan["negatives"]: L.append("- (none)")
    return "\n".join(L)
