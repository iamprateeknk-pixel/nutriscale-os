# Growth OS — Gap Audit + Blueprint v4.0 (the right architecture)
**Date:** 21 Oct 2026 | Audited: the V1–V3 blueprints + 11 code engines (all tests pass, but...)

---

## PART 1 — GAPS (an honest audit of our own system)

The engines are right, but they are only the system's **brain math**. The car has an engine; the wheels, road and driver's seat are not there yet:

| # | Gap | Severity | Meaning |
|---|-----|----------|---------|
| G1 | **No data connectors** — no code at all that brings data from Amazon SP-API/Ads API, Flipkart, Unicommerce | 🔴 Critical | Without data every engine is an empty box. This is the first job of Phase 1 |
| G2 | **No database** — the Learning Store lives in RAM | 🔴 Critical | A restart = the agent forgets everything. Learning needs permanent memory (Postgres/SQLite) |
| G3 | **No scheduler/runtime** — "the crawl runs at 6 am daily" is written down, but nothing runs it | 🔴 Critical | Cron/queue, retries, alerts on failure — the foundation of automation |
| G4 | **No approval screen** — where would approval cards even appear? | 🔴 Critical | Approval on WhatsApp + a web War-Room dashboard are still to be built |
| G5 | **Algorithm intelligence was missing** | 🔴 Critical | Added in V4 — see Part 3 |
| G6 | **Agent bloat — 14 agents is too many** | 🟠 High | Fixed in V4 — see Part 2. A needless agent = more AI cost + more chances of error |
| G7 | **Flipkart half-done** — most engines were built for Amazon; Flipkart fees/ranking differ | 🟠 High | V4 adds a separate Flipkart rank model; a Flipkart fee calculator in Phase 1 |
| G8 | **Seller account health missing** — ODR, cancellation rate, late dispatch, policy violations | 🟠 High | A suspended account = everything over. A new **F10 Health Flow** — daily health check, red alert near the limits |
| G9 | **No AI cost governor** | 🟡 Medium | A lesson from AI Quant OS: a monthly AI budget cap per agent, otherwise the learning system itself gets expensive |
| G10 | **No credentials/security design** | 🟡 Medium | API keys in a secure vault, never in code/chat — designed before Phase 2 |
| G11 | Creative is only a brief, with no image/video generation pipeline; no GST/accounting export; no multi-user roles | 🟡 Medium | Later phases |

**In short:** we are at the "Blueprint + Brain Core" stage, not "a running system". That is the work of Phases 0–2, and it needs your data/access (which is why G1 is at the top).

---

## PART 2 — AGENT RATIONALISATION: 14 agents → 9 agents + 10 flows

**Rule: an agent only where *judgment* is needed (ambiguous situations, language, creativity, strategy).
Where there is a formula/calendar/fixed rule, an agent is foolish — a FLOW (plain code) runs there.
A flow is cheaper, faster and 100% reliable than an agent — an agent can wander, a formula cannot.**

### ✅ These stay AGENTS (9) — they need a brain
| Agent | Why it must be an agent |
|-------|-------------------------|
| A01 Market Research | Understanding trends, extracting meaning from news — judgment |
| A02 Competitor Intelligence | Understanding the *intent behind* a competitor's move |
| A03 Keyword Domination | Which keyword really signals buying — language + relevance judgment |
| A04 Listing Optimization | Writing copy that both sells and ranks — creativity |
| A05 Creative | Image/video design judgment |
| A06 Ads Manager | Strategy: when to Rank-Push, when to Harvest, when to stop — money + judgment |
| A07 Pricing Strategist | Not just math — a pricing *strategy* based on competitors and season (its calculator is Flow F4) |
| A08 Review / Customer Voice | Understanding the real problem from the language of complaints |
| A09 Governance Agent (merge of the old A12 + A14) | Orchestration + approval + learning + algorithm impact — the owner of the system |

### ⚙️ These became FLOWS (agent removed) — they need a formula, not a brain
| Flow | What it was before | What it does (deterministic code, zero AI cost) |
|------|-------------------|-------------------------------------------------|
| F1 Data Sync Flow | — (new) | Brings data from Amazon/Flipkart/Unicommerce on time; retry + alert on failure |
| F2 Unicommerce Ops Flow | ~~A13 Agent~~ | Order sync, stock reconciliation, allocation — it is a formula and never needed an agent. Only unusual anomalies are escalated to A09 |
| F3 Inventory & FBA Flow | ~~A09 Agent~~ | Days of cover, reorder point, FBA shipment checklist — all formula/calendar |
| F4 Profit Calculation Flow | The math part of A07 | Margin/fee math per SKU — do not turn a calculator into an agent |
| F5 Offer & Festival Flow | ~~A10 Agent~~ | Festival calendar, deal eligibility, coupon templates — dates and rules are fixed (strategy comes from A01/A07) |
| F6 Retention Flow | ~~A11 Agent~~ | "Refill reminder on day 25 after purchase" — trigger-based automation, nothing to think about |
| F7 Guardrail & Alert Flow | Part of A12 | Stock zero → pause ads, rating dropped → alert — if-then rules |
| F8 War-Room Report Flow | — | Compiles the day's data into a report (agent insights plug into it) |
| F9 Algorithm Watch Flow | — (new) | See Part 3 — crawl official announcements + detect changes |
| F10 Seller Health Flow | — (new, G8) | Daily ODR/cancellation/late-dispatch check; near the limit = red alert |

**Benefit:** roughly half the AI cost, double the reliability, and the learning power stays where it is useful.

---

## PART 3 — ALGORITHM INTELLIGENCE (understanding the algorithm with every update)

**The truth first:** the exact Amazon and Flipkart algorithms are **secret** — nobody in the world fully knows them; Helium 10 also estimates. But there are 2 ways to win, and the system uses both:

### Way 1 — Official signals (what the platform itself says)
**Well-known factors affecting Amazon search rank** (our model, coded in `algorithm_intel.py`):
Relevance/indexing (title + backend terms) • Sales velocity (recent sales speed) • Conversion rate • CTR • Price • Prime/FBA • Stock always available • Rating/reviews • Seller health.
**Buy Box factors:** landed price, fulfilment (FBA strongest), seller rating, dispatch time, stock.
**The new era:** Amazon is moving to **COSMO + Rufus (an AI shopping assistant)** — a listing ranks not only by keywords but also by **language an AI understands**: complete attributes, use cases ("morning protein snack", "diabetic-friendly gifting"), questions and answers. This goes into the A04 Listing Agent's rules — the biggest change of the next 2 years.
**Flipkart rank factors:** relevance, price, rating, **Flipkart Assured**, seller rating/tier, dispatch speed, popularity/sales, return rate.

### Way 2 — Reverse-engineering the algorithm from your own data (Rank Probe)
Every day, for every hero keyword, your **rank + CTR + CVR + sales velocity + price** is recorded. The system extracts correlations itself: *"CTR went 0.4→0.6% and rank went 18→9"* — that is **the real algorithm model for your category**, which no outside tool can give you.

### The process for every update
1. **F9 Watch Flow** crawls Amazon Seller Central News, Flipkart Seller Hub announcements and Ads Console changelogs daily — any change (diff) is flagged immediately
2. **A09 Governance Agent** analyses the impact: which SKUs, rules and flows the change touches, and its severity (`assess_algorithm_change` in code)
3. **Playbook updates** are created: "Amazon Playbook v2026.11" — the old version is kept
4. The change is first tested in a **small experiment** (the V3 experiment engine); if it wins, it is applied fully with **Tier-1 approval**
5. In the Sunday report: "This week the algorithm changed like this, we did this, the effect was this"

**So the system never goes stale — when the platform changes, the system adapts the same week.**

---

## PART 4 — Updated roadmap (based on the gaps)
- **Phase 0:** audit (your data) — *blocked on pending inputs*
- **Phase 1 (foundation):** G1 connectors + G2 database + G3 scheduler + flows F1–F10 live — *these first, agents later*
- **Phase 2:** G4 War Room + WhatsApp approval + 9 agents live + algorithm playbooks v1
- **Phase 3:** fully autonomous + a mature Rank Probe + festival/flywheel scale
