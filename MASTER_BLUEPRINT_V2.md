# DryFruit Ecommerce Growth OS — Master Blueprint v2.0 (Autonomous Edition)
**Upgrade over V1:** the system no longer just reports — **it does the work itself and only asks you for approval.**
**Date:** 21 Oct 2026 | V1: MASTER_BLUEPRINT.md (12 agents, engines ready)

---

## 1. Approval-only autonomous mode (the biggest change)

You have one job: **press Approve / Reject.** The system does everything else.

Every agent first creates an **Action Proposal**: what changes, why, the expected impact, what it costs, and how to roll back if it goes wrong. Then, by tier:

| Tier | Approval | What |
|------|----------|------|
| **Tier 0 — AUTO** | No approval; the system does it itself | Negating wasted search terms, bids ±10% (within guardrails), stock/price alerts, competitor alerts, daily report, auto-pausing ads when stock runs out |
| **Tier 1 — ONE-TAP** | You get a card: **Approve / Reject / Change** | Listing title/bullets/A+ upgrades, bids beyond ±20%, budget increases, price changes, coupon/deal launches, new campaigns, FBA shipment plans |
| **Tier 2 — DOUBLE CONFIRM** | Confirmed twice | Budget +50% or more, price cuts of more than 10%, a new SKU launch, a large inventory purchase |

**As soon as you approve, the system:** executes via API (listing patch via Amazon SP-API, campaign change via the Ads API, Flipkart Seller API, Unicommerce API) → verifies the execution → measures the result after 7 and 14 days and learns which actions worked. **Every action has a before/after audit log** — no agent can do anything in secret.

**Guardrails (protection against burning money):** daily spend cap • price never below the margin floor • ads off when there is no stock • ad spend for a SKU frozen if its rating drops below 4.0 • a limit on total budget change per day.

---

## 2. How a ROAS of 8–10 really happens — the organic flywheel

The Ads Console ROAS only counts *paid* sales. The real number is **Blended ROAS = Total Sales ÷ Ad Spend** (and its inverse: TACOS).

| Month | Ad spend | Paid sales (ROAS 3–4) | Organic sales | **Total sales** | **Blended ROAS** | TACOS |
|-------|----------|----------------------|---------------|-----------------|------------------|-------|
| Month 1 | ₹25,000 | ₹75,000 | ₹25,000 | ₹1,00,000 | 4.0 | 25% |
| Month 3 | ₹25,000 | ₹1,00,000 | ₹1,00,000 | ₹2,00,000 | **8.0** | 12.5% |
| Month 6 | ₹30,000 | ₹1,20,000 | ₹2,10,000 | ₹3,30,000 | **11.0** | 9% |

**How the flywheel turns:** ads → sales velocity → **higher rank** on hero keywords → organic (free) sales grow → less dependence on ads → total sales double on the same spend → blended ROAS 8–10.

That is why the A06 Ads Agent has 2 modes:
- **Rank-Push mode** (at the start): deliberately break-even ads on 3–5 hero keywords — the aim is page-1 rank, not profit.
- **Harvest mode** (once rank is won): reduce ad spend on those keywords, collect the free organic sales, move spend to the winners.
A03 tracks the **organic rank** of hero keywords daily — rank is this system's real asset.

---

## 3. FBA + Flipkart Warehouse (the A09 upgrade)

Keeping stock in **Amazon FBA + Flipkart Warehouse (Flipkart Assured)** gives:
- **Prime / Assured badge** → higher CTR and conversion (customers trust badged listings more)
- **Fast delivery** → helps both Buy Box and rank
- **Lower, fixed transport cost** — instead of shipping yourself (₹80–120/order + RTO losses), a predictable FBA fee; Amazon/Flipkart handle returns

**What the FBA Planner does:**
- **Days of cover** per SKU: no more than 30–45 days of stock (storage fees + dry-fruit shelf life); under 15 days → a replenishment proposal (Tier-1 approval)
- **Which SKU goes to FBA and which does not:** fast-selling hero SKUs = FBA; slow SKUs = your own warehouse (otherwise storage fees eat the margin)
- **Festival rule:** FBA stock full 45 days before a peak like Diwali — inbound is congested at the peak
- **FEFO/expiry:** the batch that expires first sells first — the biggest hidden loss in dry fruits
- **Cost comparison:** FBA fee vs self-ship per SKU together with the A07 Profit Agent — where FBA is more expensive, it is not used

---

## 4. NEW — A13 Unicommerce Ops Agent

**All the Unicommerce work is now done by this system too.** No separate person, no separate hassle.

| Job | What A13 does |
|-----|---------------|
| **Order sync** | All Amazon + Flipkart (+ website, if any) orders in one place; no order missed |
| **One stock truth** | Unicommerce master inventory ↔ Amazon ↔ Flipkart — a daily **3-way reconciliation**; an immediate alert on a mismatch (a stock mismatch = overselling = cancellations = poor account health) |
| **Channel allocation** | Reserve/allocate stock by channel — if Amazon sells faster, stock goes there first |
| **Warehouse allocation** | Own warehouse, FBA, Flipkart warehouse — which facility an order ships from, managed by A13 with Unicommerce facility mapping |
| **SKU mapping** | Map the different channel SKU codes of one product to one master SKU — the most common source of mistakes |
| **Returns / RTO** | Return received, QC done, stock back in the system — where the losses are, which SKU/courier has the most RTO |
| **PO / GRN** | Purchase orders to suppliers and stock-in records, linked to A09's forecast |
| **Health report** | Daily: pending orders, dispatch delays, stock mismatches, RTO% — in one report |

**Integration:** via the Unicommerce (Uniware) API. Phase 2 needs your Unicommerce login/API access — the system prepares everything, you only approve the connection.

---

## 5. Updated system — 13 agents

V1's 12 agents (A01 Market Research → A12 Orchestrator) stay, with 3 changes:
- **A12 Orchestrator is now also the Approval Governor** — all proposals, approvals, the audit log and guardrails sit with it
- **A06 Ads Agent** gets the Rank-Push + Harvest modes
- **A09 Inventory Agent** is now also the FBA + Flipkart Warehouse Planner
- **+ A13 Unicommerce Ops Agent (new)**

## 6. Updated roadmap
- **Phase 0 (7 days):** audit — ASINs, ad reports, cost sheet, the current Unicommerce setup
- **Phase 1:** engines (ready) + approval system + war-room report
- **Phase 2:** live connection — Amazon SP-API/Ads API, Flipkart, **Unicommerce API**, FBA planner live
- **Phase 3:** fully autonomous — the Rank-Push → Harvest flywheel running, festival war plan, scale

## 7. What I need from you (the old list + 2 new items)
1–5. The V1 list (brand, ASIN links, 90 days of sales/ad data, cost sheet, agency details)
6. Do you use **Unicommerce** today? If you have an account, its setup (how many warehouses/facilities, which channels are connected)
7. **Is there stock in FBA already, or does it still need to be sent?** And the Flipkart warehouse status
