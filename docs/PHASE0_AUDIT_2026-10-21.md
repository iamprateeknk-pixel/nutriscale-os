# Phase-0 Audit — Dry Fruit Farm (Amazon) · 21 Oct 2026
_From real data: Ads Campaign Report + Search Term Report + All Orders Report. Raw data (customer information) is NOT in the repo — only aggregates._

## The truth at a glance
| Item | Number |
|---|---|
| Orders (22 Aug – 21 Oct 2026) | **104 orders, ₹46,069 revenue, AOV ₹443** |
| SKUs sold | only **7** |
| Ad spend (campaign report) | **₹27,963** → ad sales ₹41,346 → **ROAS 1.48** |
| Search-term level | spend ₹17,158 → sales ₹29,031 → **ROAS 1.69, ACOS 59%** |
| **TACOS (spend ÷ total sales)** | **≈ 61%** — ₹61 of every ₹100 of sales goes to ads alone |
| Click→order conversion | **3.6%** (a healthy level is 10–15%) |
| Campaigns | **14 of 23 with zero sales**, **₹3,850 (14%)** wasted on them |

_Note: the three reports cover different time windows (orders 22 Aug–21 Oct; search terms around September; campaign rows a mix of Jul–Oct) — so the numbers show direction, not a rupee-for-rupee match._

## Where the sales come from — only 2 products!
| Product | Units | Revenue | Share |
|---|---|---|---|
| Brazil Nuts Grade A++ 200g | 32 | ₹25,448 | **55%** |
| Dried Cranberries 200g | 68 | ₹14,892 | **32%** |
| Pecan Nuts 200g | 5 | ₹2,995 | 7% |
| Macadamia 200g | 2 | ₹1,518 | 3% |
| Blueberries / Sunflower / Cashew W320 | 4 | ₹1,216 | 3% |

**The top 2 = 87% of total sales.** And the most surprising part: **cashews and almonds — the face of dry fruits — barely sold** (Cashew W320 only 1 unit), even though ads are running on them.

## Where the money burns
1. **14 zero-sale campaigns = ₹3,850 straight down the drain:** Dried Blueberries SP ₹936, Dried Cranberries SP ₹567, cashew (old) ₹528, Walnut Giri SP ₹460, California Almonds SP ₹374, Afghani Raisin SP ₹231…
2. **The biggest campaign is the weakest:** "CRANBERRY" ₹8,517 spent → ROAS only 1.3, while the "brazil" campaign ₹7,537 → **ROAS 2.9** — the budget split is upside down.
3. **Bleeder search terms (₹100+ spent, 0 orders):** sunflower seeds 250 gm ₹277, kaju 1 kg ₹188, blueberry dried ₹178, pecan nuts 500g ₹138, brazil nuts 200g ₹114 — ₹896 in total.
4. **The real disease is conversion, not traffic:** 1,846 clicks came, only 67 orders. No keyword reaches a 10% CVR (HERO level) — the best, "dried cranberry", is at 6.1%. People are arriving; **the listing/price/trust is stopping them**.

## Winners (protect and grow these)
- Campaign **brazil** (ROAS 2.9), terms: brazil nuts (ROAS 2.5), brazil nuts 250g (2.4), cranberry (4.6, small spend — worth scaling)
- Every selling term is around Cranberry/Brazil — these two are the "cash engines".

## What the system did itself (today)
- The Ads Agent created **15 bid-down proposals** on real data (awaiting your approval)
- This audit also found and fixed two real software bugs (the orders import column, campaign aggregation) — the system is now tested on your own data.

## The cure for the next 30 days (in order)
1. **Today:** PAUSE the 14 zero-sale campaigns (an estimated ₹3,850 saved per cycle) — the approval file is in the backend.
2. **This week:** move budget from the "CRANBERRY" broad campaign towards **brazil + cranberry-exact**; give the "cranberry" term its own exact campaign.
3. **Listing cure (the biggest):** the small ₹219 cranberry pack is killing AOV — 400g/800g bundle variants; review/price work on Brazil Nuts. Check the cashew/almond listings — **this needs the listing links**.
4. **Margin math:** without a cost sheet the ROAS target is blind — as soon as the **Brazil Nuts and Cranberry cost sheet** (per-kg purchase + packing) arrives, every SKU's break-even ROAS gets calculated.

## Inputs still pending
- [ ] Cost sheet for the hero SKUs (Brazil Nuts, Cranberry first)
- [ ] Cashew/almond listing links (to see why they do not sell)
- [ ] Flipkart data (how things stand there)
- [ ] Is stock in FBA, or are you shipping yourself? (delivery speed = conversion)
- [ ] How much does the agency charge per month? (the numbers above raise that question)
