# DryFruit Ecommerce Growth OS — Master Blueprint v1.0
**Goal:** Amazon IN + Flipkart par dry fruits category me #1 selling brand banna — profit-first, data-first.
**Working name:** Growth OS (tum brand name doge to rename ho jayega)
**Date:** 21 Oct 2026

---

## 1. Pehle sach (jo agency nahi bolegi)

1. **8–10 ROAS guarantee koi nahi de sakta.** ROAS 8–10 matlab ACOS 10–12.5%.
   Ye sirf tab possible hai jab: (a) contribution margin 35%+ ho, (b) listing conversion 15%+ ho,
   (c) branded + high-intent keywords ka share zyada ho. Generic keywords ("buy almonds online")
   par shuruaat me ROAS 2.5–4 realistic hai. System ka kaam: pehle waste band karo (ROAS 4–5),
   phir winners scale karke blended ROAS 6–8 ki taraf le jao. Jo 8–10 bolke beche, woh jhooth bol raha hai.
2. **Ads listing ko nahi bacha sakte.** Agar main image, price-per-kg, reviews aur conversion kamzor hai,
   to ads sirf paisa jalayenge. Isiliye system pehle Listing + Price fix karta hai, phir Ads scale karta hai.
3. **4 mahine me growth nahi = aksar ye 5 reasons:** main image CTR kam, price/kg top-3 competitor se zyada,
   reviews <50 aur rating <4.2, keywords index hi nahi hue, ads me 70%+ spend bina-sale wale search terms par.
   System ka Phase-0 audit in 5 ko pehle pakdega.

---

## 2. System Architecture — 12 Agents

| # | Agent | Kaam | Output |
|---|-------|------|--------|
| A01 | **Market Research Agent** | Category demand, search trend, seasonality (Diwali/Rakhi/wedding/gifting), price bands 250g/500g/1kg | Weekly demand report, kaunsi SKU kab push karni hai |
| A02 | **Competitor Intelligence Agent** | Top 20 competitor ASIN (Amazon) + Flipkart listings: price, rating, reviews, BSR, title keywords, offers, image style | Daily competitor alert: kisne price giraya, kiski listing badli |
| A03 | **Keyword Domination Agent** | Helium10 Cerebro/Magnet ka desi alternative: competitor reverse-ASIN, apne Search Term Reports, Amazon search suggestions se keyword universe | Keyword bank har SKU ke liye: volume × relevance × competition score ke saath |
| A04 | **Listing Optimization Agent** | Title, bullets, description, A+ content, backend search terms — har SKU ko 0–100 Listing Score | Ready-to-upload listing copy (EN + Hinglish search terms backend me) |
| A05 | **Creative Agent** | Main image CTR design brief, infographics (health benefits, origin, grading), comparison chart, video script | Image/video brief designer ke liye, A/B test plan |
| A06 | **Ads Manager Agent** | Amazon SP/SB/SD + Flipkart PLA: campaign structure, bid optimization, negative keywords, dayparting, budget rules | Daily actions: kill / scale / bid-up / bid-down — har action ke peeche reason |
| A07 | **Pricing & Profit Agent** | Har SKU ka asal profit: product cost + packing + marketplace fee + shipping + returns + ad spend | Break-even ROAS, max CPC jo tum afford kar sakte ho, price/deal sujhav |
| A08 | **Review & Trust Agent** | Review mining (apne + competitor ke 1–3 star reviews = product/listing improvement), Q&A, Vine plan | Weekly: customers kya shikayat kar rahe hain, kya pasand kar rahe hain |
| A09 | **Inventory & Forecast Agent** | Demand forecast, stockout alert, dry fruits expiry/FEFO, FBA shipment plan | Stockout se pehle alert (stockout = ranking death) |
| A10 | **Offer & Festival Agent** | Deal calendar: Lightning Deals, coupons, combos (gift hampers), subscribe & save, virtual bundles | Festival war-plan 45 din pehle ready |
| A11 | **Retention Agent** | Repeat purchase: dry fruits monthly consumption hai — WhatsApp/insert cards/D2C cross-sell, refill reminders | Repeat rate report (yehi asli profit hai) |
| A12 | **Orchestrator / Growth Governor** | Saare agents ko jodta hai, daily war-room report, budget allocation, koi agent bina profit-guardrail ke spend nahi badha sakta | Roz subah 1-page report: Sales, Profit, ROAS, top 5 actions |

### Helium 10 se behtar kaise?
- **India-first:** Helium10 Amazon US-centric hai, Flipkart ko toh dekhta hi nahi. Ye system dono ek dashboard me.
- **Dry-fruit specific:** per-kg price comparison, grade (W240/W320 cashew, Mamra/Jumbo badam), weight variants, festival gifting — Helium10 ko ye samajh nahi.
- **Profit-first:** Helium10 sales volume dikhata hai, ye system pehle margin nikalta hai — bina margin ke "bestseller" ghata hai.
- **Action, sirf data nahi:** Helium10 data deta hai, tumhe sochna padta hai. Ye agents decision dete hain: "is keyword ko kill karo, is par bid +20% karo, is SKU ka price ₹20 kam karo kyunki competitor X ne giraya hai."

---

## 3. Ads System (A06 ka core design)

**Campaign structure (har hero SKU ke liye):**
1. Exact — Top 10 proven keywords (sabse zyada budget %)
2. Phrase — keyword expansion
3. Broad/Auto — discovery (kam budget, sirf naye search terms dhoondhne ke liye)
4. Product Targeting — competitor ASIN par attack (unke page par apna ad)
5. Brand Defence — apne brand keywords (sasta, high ROAS)
6. Remarketing (SD) — page dekha, kharida nahi

**Decision rules (code me implemented — `src/ads_engine.py`):**
- Search term: spend > 1.5 × target CPA aur 0 sale → **negative / kill**
- Keyword: ROAS > target × 1.5 aur impression share kam → **bid +20% scale**
- CTR < 0.3% → listing/main image problem, bid nahi badhayenge, A05 ko ticket
- CVR < 8% → price/review problem, A07/A04 ko ticket (ads ka paisa yahan rukega)
- Har keyword ka max CPC = selling price × target conversion × target ACOS — isse upar bid kabhi nahi

**Budget niyam:** 60% proven winners, 25% growth tests, 15% discovery. Festival me 45 din pehle se ramp-up.

---

## 4. Listing System (A04 ka core design)

**Listing Score 0–100 (code me implemented — `src/listing_scorer.py`):**
Title (keyword + grade + weight + use-case) 20 | Main image + 6+ images + video 20 |
Bullets (benefit-first, Hinglish samajhne wali bhasha) 15 | A+ content 10 |
Reviews/rating 15 | Price competitiveness (per-kg vs top-3) 10 | Backend terms + indexing 10

Score <70 wali listing par ads scale nahi honge — pehle fix, phir spend. Ye ek rule hi agency-model ko hara dega.

---

## 5. Data — system ko chahiye

| Source | Kaise milega | Kis ke liye |
|--------|--------------|-------------|
| Amazon Seller Central reports | SP-API connect ya CSV export | Sales, search terms, ads |
| Amazon Ads Console reports | Ads API / CSV | A06 ke sare decisions |
| Flipkart Seller Hub reports | CSV export (API limited hai) | Flipkart sales/ads |
| Competitor listings | Public pages ki daily snapshot | A02 |
| Tumhara cost sheet | Excel: product cost, packing, courier | A07 profit — **bina iske ROAS jhooth hai** |

---

## 6. Roadmap

- **Phase 0 — Audit (Pehle 7 din):** Tumhare ASIN, ad account reports aur cost sheet par full audit.
  Output: kahan paisa jal raha hai, kaunsi listing fix pehle. *Bina iske system andha hai.*
- **Phase 1 — MVP (Week 2–4):** Listing Scorer + Profit Calculator + Ads Decision Engine + Competitor Tracker + Daily War-Room report. (Is blueprint ke saath code foundation ready hai.)
- **Phase 2 — Automation (Month 2):** SP-API/Ads API live connect, auto negative-keyword lists, price alerts, festival war-plan.
- **Phase 3 — Scale (Month 3+):** Auto-bidding (guardrails ke saath), creative A/B tests, naye SKU launch playbook, D2C retention.

## 7. KPI jo roz dekhenge
Sales (Amazon/Flipkart alag) • Contribution Profit (sirf revenue nahi) • Blended ROAS + SKU-wise ROAS •
Conversion Rate • CTR • Review rating/count • Top-3 competitor se price gap • Stock days

---

## 8. Mujhe tumse chahiye (Phase-0 ke liye)
1. Brand name + Amazon store link / top 5–10 ASIN links
2. Flipkart seller name / top listings ke links
3. Last 90 days: monthly sales + ad spend (Ads Console ka Search Term Report CSV mile to sone pe suhaga)
4. Hero products: kaunsi dry fruits, kaunse weights (250g/500g/1kg), aur unki cost price (per SKU)
5. Abhi agency kya-kya kar rahi hai, monthly kitna charge kar rahi hai
