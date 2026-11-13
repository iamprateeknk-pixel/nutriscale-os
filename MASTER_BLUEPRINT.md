# DryFruit Ecommerce Growth OS — Master Blueprint v1.0
**Goal:** become the #1 selling dry-fruits brand on Amazon IN + Flipkart — profit-first, data-first.
**Working name:** Growth OS (renamed once the brand name is given)
**Date:** 21 Oct 2026

---

## 1. The truth first (what an agency will not tell you)

1. **Nobody can guarantee a ROAS of 8–10.** ROAS 8–10 means ACOS 10–12.5%.
   That is only possible when: (a) contribution margin is 35%+, (b) listing conversion is 15%+,
   (c) branded + high-intent keywords carry a large share. On generic keywords ("buy almonds online")
   a ROAS of 2.5–4 is realistic at the start. The system's job: first stop the waste (ROAS 4–5),
   then scale the winners towards a blended ROAS of 6–8. Anyone selling a guaranteed 8–10 is lying.
2. **Ads cannot save a listing.** If the main image, price-per-kg, reviews and conversion are weak,
   ads only burn money. That is why the system fixes Listing + Price first, then scales Ads.
3. **No growth in 4 months usually has these 5 reasons:** low main-image CTR, price/kg above the top-3 competitors,
   fewer than 50 reviews and a rating below 4.2, keywords never indexed, 70%+ of ad spend on search terms with no sales.
   The system's Phase-0 audit catches these 5 first.

---

## 2. System architecture — 12 agents

| # | Agent | Job | Output |
|---|-------|-----|--------|
| A01 | **Market Research Agent** | Category demand, search trends, seasonality (Diwali/Rakhi/weddings/gifting), price bands 250g/500g/1kg | Weekly demand report: which SKU to push when |
| A02 | **Competitor Intelligence Agent** | Top 20 competitor ASINs (Amazon) + Flipkart listings: price, rating, reviews, BSR, title keywords, offers, image style | Daily competitor alert: who cut prices, whose listing changed |
| A03 | **Keyword Domination Agent** | An Indian alternative to Helium10 Cerebro/Magnet: competitor reverse-ASIN, your own Search Term Reports, Amazon search suggestions → keyword universe | A keyword bank per SKU with volume × relevance × competition scores |
| A04 | **Listing Optimization Agent** | Title, bullets, description, A+ content, backend search terms — a 0–100 Listing Score per SKU | Ready-to-upload listing copy (English + Hinglish search terms in the backend) |
| A05 | **Creative Agent** | Main-image CTR design brief, infographics (health benefits, origin, grading), comparison chart, video script | Image/video brief for the designer, A/B test plan |
| A06 | **Ads Manager Agent** | Amazon SP/SB/SD + Flipkart PLA: campaign structure, bid optimisation, negative keywords, dayparting, budget rules | Daily actions: kill / scale / bid-up / bid-down — every action with a reason |
| A07 | **Pricing & Profit Agent** | The real profit of every SKU: product cost + packing + marketplace fee + shipping + returns + ad spend | Break-even ROAS, the max CPC you can afford, price/deal suggestions |
| A08 | **Review & Trust Agent** | Review mining (your own + competitors' 1–3 star reviews = product/listing improvements), Q&A, Vine plan | Weekly: what customers complain about and what they like |
| A09 | **Inventory & Forecast Agent** | Demand forecast, stock-out alerts, dry-fruit expiry/FEFO, FBA shipment plan | Alert before a stock-out (a stock-out = ranking death) |
| A10 | **Offer & Festival Agent** | Deal calendar: Lightning Deals, coupons, combos (gift hampers), subscribe & save, virtual bundles | Festival war plan ready 45 days ahead |
| A11 | **Retention Agent** | Repeat purchase: dry fruits are a monthly consumable — WhatsApp/insert cards/D2C cross-sell, refill reminders | Repeat-rate report (that is the real profit) |
| A12 | **Orchestrator / Growth Governor** | Connects all agents, daily war-room report, budget allocation; no agent can increase spend without the profit guardrail | Every morning a 1-page report: sales, profit, ROAS, top 5 actions |

### How is this better than Helium 10?
- **India-first:** Helium10 is Amazon-US-centric and does not look at Flipkart at all. This system has both in one dashboard.
- **Dry-fruit specific:** per-kg price comparison, grades (W240/W320 cashew, Mamra/Jumbo almonds), weight variants, festival gifting — Helium10 does not understand these.
- **Profit-first:** Helium10 shows sales volume; this system works out margin first — a "bestseller" without margin is a loss.
- **Actions, not just data:** Helium10 gives data and you have to think. These agents give decisions: "kill this keyword, raise this bid +20%, cut this SKU's price by ₹20 because competitor X dropped theirs."

---

## 3. Ads system (the core design of A06)

**Campaign structure (per hero SKU):**
1. Exact — the top 10 proven keywords (the largest budget share)
2. Phrase — keyword expansion
3. Broad/Auto — discovery (small budget, only to find new search terms)
4. Product Targeting — attack competitor ASINs (your ad on their page)
5. Brand Defence — your own brand keywords (cheap, high ROAS)
6. Remarketing (SD) — viewed the page, did not buy

**Decision rules (implemented in code — `src/ads_engine.py`):**
- Search term: spend > 1.5 × target CPA and 0 sales → **negative / kill**
- Keyword: ROAS > target × 1.5 and low impression share → **bid +20% scale**
- CTR < 0.3% → a listing/main-image problem; do not raise the bid, ticket to A05
- CVR < 8% → a price/review problem; ticket to A07/A04 (ad money stops here)
- Every keyword's max CPC = selling price × target conversion × target ACOS — never bid above it

**Budget rule:** 60% proven winners, 25% growth tests, 15% discovery. Ramp up 45 days before a festival.

---

## 4. Listing system (the core design of A04)

**Listing Score 0–100 (implemented in code — `src/listing_scorer.py`):**
Title (keyword + grade + weight + use case) 20 | Main image + 6+ images + video 20 |
Bullets (benefit-first, plain language) 15 | A+ content 10 |
Reviews/rating 15 | Price competitiveness (per kg vs the top 3) 10 | Backend terms + indexing 10

Ads will not scale on a listing scoring below 70 — fix first, then spend. This one rule alone beats the agency model.

---

## 5. Data the system needs

| Source | How to get it | What for |
|--------|---------------|----------|
| Amazon Seller Central reports | SP-API connection or CSV export | Sales, search terms, ads |
| Amazon Ads Console reports | Ads API / CSV | All of A06's decisions |
| Flipkart Seller Hub reports | CSV export (the API is limited) | Flipkart sales/ads |
| Competitor listings | Daily snapshots of public pages | A02 |
| Your cost sheet | Excel: product cost, packing, courier | A07 profit — **without it ROAS is a lie** |

---

## 6. Roadmap

- **Phase 0 — Audit (first 7 days):** a full audit of your ASINs, ad account reports and cost sheet.
  Output: where money is burning and which listing to fix first. *Without it the system is blind.*
- **Phase 1 — MVP (weeks 2–4):** Listing Scorer + Profit Calculator + Ads Decision Engine + Competitor Tracker + daily war-room report. (The code foundation is ready with this blueprint.)
- **Phase 2 — Automation (month 2):** live SP-API/Ads API connection, automatic negative-keyword lists, price alerts, festival war plan.
- **Phase 3 — Scale (month 3+):** auto-bidding (with guardrails), creative A/B tests, a new-SKU launch playbook, D2C retention.

## 7. KPIs we watch every day
Sales (Amazon/Flipkart separately) • Contribution profit (not just revenue) • Blended ROAS + SKU-wise ROAS •
Conversion rate • CTR • Review rating/count • Price gap to the top-3 competitors • Stock days

---

## 8. What I need from you (for Phase 0)
1. Brand name + Amazon store link / top 5–10 ASIN links
2. Flipkart seller name / links to the top listings
3. Last 90 days: monthly sales + ad spend (the Ads Console Search Term Report CSV would be ideal)
4. Hero products: which dry fruits, which weights (250g/500g/1kg), and their cost price (per SKU)
5. What the agency does today and how much it charges per month
