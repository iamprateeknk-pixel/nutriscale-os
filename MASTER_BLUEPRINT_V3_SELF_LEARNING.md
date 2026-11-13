# DryFruit Ecommerce Growth OS — Blueprint v3.0: Self-Learning Layer
**Upgrade over V2:** every agent now **learns daily and gets stronger daily** — from its own results and from the best sources on the web.
**Date:** 21 Oct 2026 | Previous: V1 (12 agents + engines), V2 (Autonomous + FBA + Unicommerce + A13)

---

## 0. An honest word first — about "AGI"

Scientifically, **AGI** (human-like general intelligence) does not exist anywhere today — not at OpenAI, not at Google. Anyone selling it is doing marketing.

**But you do not need AGI — you need self-improving agents, and those can be built 100%:**
An agent works → measures the result → learns from mistakes → improves its own rules → brings in new knowledge from the web → tests and adopts it → **smarter every day than the day before.** That is the design of V3. Name: **Self-Learning Layer (under the A14 Learning Governor).**

---

## 1. Every agent learns in 4 ways

### Learning #1 — from its own results (experience learning) — *the most valuable*
Every action the system takes (raised a bid, changed a title, cut a price) has its result measured **after 7 and 14 days**:
- Good result → that rule's **confidence goes up**; next time it decides more strongly
- Bad result → confidence goes down; the rule gets weaker
- A rule that fails 3 times in a row → **auto-disabled**, and the agent tries a new rule in its place
- *Example:* if "bid +20%" worked on cashews but failed 3 times on almonds, the agent learns that **this rule differs by category.** That is real learning — no blog can teach it, because it comes from *your* data.

### Learning #2 — from the web (knowledge learning)
A **Learning Crawl** runs every morning — these sources, in order of trust:

| Trust | Source | What it learns |
|-------|--------|----------------|
| ★★★★★ Official | Amazon Seller University, Amazon Ads Academy, Flipkart Seller Learning Center, Unicommerce Help/Docs | New policies, fee changes, new features — **fee/policy changes first, otherwise the profit math goes wrong** |
| ★★★★ Practitioner | Helium 10 blog/podcast, Jungle Scout, SellerApp, top Indian seller YouTube channels | New tactics, case studies, keyword/ads strategies |
| ★★★ Community | Seller forums, Reddit r/AmazonSeller, Facebook seller groups | Ground truth, other people's mistakes (so you do not have to make them) |
| ★★ News | Ecommerce news (ET Retail, Inc42, YourStory) | Category trends, competitor brand moves, funding/new launches |

Everything new goes into the **Knowledge Store**: what was learned, the source, its trust (reliability score), and which agent it is useful for.

### Learning #3 — from experiments (A/B testing)
An agent does not learn in the dark — it learns **by testing**:
- New listing title vs the old one — 50/50 traffic; the winner stays, the loser is rolled back
- New main image, new price point, new bid strategy — all in a small test first
- Only a change that wins the test is applied to the whole listing — so "advancing" means advancing *with evidence*

### Learning #4 — from competitors (what they do is data)
A competitor changed a price, added a new image, ran a deal — A02 records it all and A14 extracts patterns: *"the top-5 competitors run coupons 30 days before Diwali"* — after one season, **the system is prepared in advance next year.** This is compounding learning — the older the system, the more dangerous it gets.

---

## 2. Safety — learning does not mean blind change

A system that changes itself without checks can also break itself. So there are 3 locks:

1. **Sandbox first:** a new learning/rule is first **backtested** on old data — if it did not work on old data, it never goes live
2. **The approval rule stays the same:** a big change that comes from learning (a strategy change) goes through Tier-1 approval; small knowledge/rules can be adopted at Tier 0
3. **Rollback + versions:** every version of every agent is saved (v1.0 → v1.1 → ...). If a new version is worse than the old one, **one click restores the old version.** Every Sunday an "Agent Upgrade Report": how much each agent improved, what it learned, what was disabled.

## 3. The daily learning cycle (runs by itself)

| Time | What happens |
|------|--------------|
| 6 am | Learning Crawl — new knowledge from all sources, policy/fee change alerts at the top |
| 7 am | Yesterday's action results measured — confidence up/down, failing rules flagged |
| During the day | Experiments keep running, data keeps accumulating |
| 11 pm | Daily Learning Summary for you: what the agents learned today, what they will do differently tomorrow |

**Agent Strength Score (0–100):** each agent's report card — the success rate of its decisions. The weaker an agent, the more attention (more tests, more learning) the system gives it. **The daily score should always end up above Sunday's — that is the proof of "stronger day by day", not words.**

## 4. Technical parts (ready in code)
- `src/self_learning.py` — Knowledge Store, source reliability, Outcome Learner (rule confidence engine), auto-disable of failing rules
- `src/experiment_engine.py` — the A/B test win/loss decision (with numbers, not guesses)
- `src/learning_sources.py` — the registry of all learning sources, which agent reads which, the crawl schedule
- The A14 **Learning Governor** agent — owns the whole learning process; no agent can change its live rules without it

## 5. The truth to remember
Learning speed = data speed. In the first 30 days there is little data and learning is slow. After 90 days, with result data from 1000+ actions, the system really gets fast — just like a new employee: learns in the first month, runs things by the sixth. **The system needs time, but that time is not wasted — every day's data is a strength no competitor can buy.**
