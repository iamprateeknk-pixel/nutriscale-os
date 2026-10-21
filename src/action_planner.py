"""Action Planner — DB ke asal data se 'aaj kya karna hai' ki taiyaar list.
Audit bolti hai kya gadbad hai; Planner bolta hai kis button ko, kis kram me dabana hai.
Har item ke saath andazan bachat/asar — taaki faisla aasan ho.
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
                                   "reason": "Is pure arse me ek bhi sale nahi — paisa jal raha hai"})
            plan["savings_est"] += c["spend"]
        elif roas >= 2.5 and c["spend"] >= 200:
            plan["scale"].append({"campaign": c["name"], "spend": round(c["spend"]), "roas": round(roas, 1),
                                  "suggest": "Budget +30% — yehi paisa kama raha hai, pehle ise khilao"})
        elif 0 < roas < 1.0 and c["spend"] >= 300:
            plan["watch"].append({"campaign": c["name"], "spend": round(c["spend"]), "roas": round(roas, 1),
                                  "suggest": "ROAS 1 se kam — bid -20% karo aur 7 din dekho, na sudhre to pause"})
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
         f"Kul ad kharch (report ka): **₹{plan['total_spend']:,}** · Sirf pause se andazan bachat: **₹{plan['savings_est']:,}/cycle**", "",
         "## 1) PAUSE karo (zero sale, paisa jal raha hai)"]
    L += [f"- [ ] **{p['campaign']}** — ₹{p['spend']:,} kharch, 0 sale. {p['reason']}" for p in plan["pause"]] or ["- (koi nahi)"]
    L += ["", "## 2) BADHAO (ye paisa kama rahe hain)"]
    L += [f"- [ ] **{s['campaign']}** — ROAS {s['roas']} · {s['suggest']}" for s in plan["scale"]] or ["- (koi nahi — pehle conversion sudharo)"]
    L += ["", "## 3) BID GHATAO aur dekho"]
    L += [f"- [ ] **{w['campaign']}** — ROAS {w['roas']} · {w['suggest']}" for w in plan["watch"]] or ["- (koi nahi)"]
    L += ["", f"## 4) NEGATIVE keywords lagao (kul barbaadi ₹{plan['negative_waste']:,})", "_In terms ne paisa khaya, order ek bhi nahi — Exact Negative lagao:_"]
    for g in plan["negatives"]:
        L.append(f"- **{g['campaign']}**: " + ", ".join(f"{t['term']} (₹{t['wasted']:,})" for t in g["terms"]))
    if not plan["negatives"]: L.append("- (koi nahi)")
    return "\n".join(L)
