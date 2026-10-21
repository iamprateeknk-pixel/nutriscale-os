# DryFruit Ecommerce Growth OS — Master Blueprint v2.0 (Autonomous Edition)
**V1 se upgrade:** Ab system sirf report nahi dega — **khud sab karega, tumse sirf approval lega.**
**Date:** 21 Oct 2026 | V1: MASTER_BLUEPRINT.md (12 agents, engines ready)

---

## 1. Approval-Only Autonomous Mode (sabse bada change)

Tumhara kaam sirf ek hai: **Approve / Reject dabana.** Baaki sab system.

Har agent pehle ek **Action Proposal** banata hai: kya badlega, kyun, expected impact, kitna paisa lagega, galat hua to rollback kaise hoga. Phir tier ke hisaab se:

| Tier | Approval | Kya-kya |
|------|----------|---------|
| **Tier 0 — AUTO** | Koi approval nahi, system khud karta hai | Waste search-term ko negative lagana, bid ±10% (guardrail ke andar), stock/price alert, competitor alert, daily report, stock khatm ho to ads auto-pause |
| **Tier 1 — ONE-TAP** | Tumhe card aayega: **Approve / Reject / Change** | Listing title/bullets/A+ upgrade, bid ±20% se zyada, budget badhana, price change, coupon/deal launch, nayi campaign, FBA shipment plan |
| **Tier 2 — DOUBLE CONFIRM** | Do baar confirm | Budget +50% se zyada, price 10% se zyada kam, naya SKU launch, badi inventory purchase |

**Approve dabate hi system:** API se execute karta hai (Amazon SP-API se listing patch, Ads API se campaign change, Flipkart Seller API, Unicommerce API) → execution verify karta hai → 7 aur 14 din baad result measure karke seekhta hai ki kaunsa action kaam kiya. **Har action ka before/after audit log** — koi agent chhupke kuch nahi kar sakta.

**Guardrails (paisa jalne se bachav):** Daily spend cap • Margin floor se niche price kabhi nahi • Stock na ho to ads band • Rating 4.0 se niche gire to us SKU ka ad spend freeze • Ek din me total budget change ki limit.

---

## 2. ROAS 8–10 asal me kaise aayega — Organic Flywheel (tumhari baat 100% sahi hai)

Ads Console wala ROAS sirf *paid* sales ginta hai. Asli number hai **Blended ROAS = Total Sales ÷ Ad Spend** (aur uska ulta: TACOS).

| Mahina | Ad Spend | Paid Sales (ROAS 3–4) | Organic Sales | **Total Sales** | **Blended ROAS** | TACOS |
|--------|----------|----------------------|---------------|-----------------|------------------|-------|
| Month 1 | ₹25,000 | ₹75,000 | ₹25,000 | ₹1,00,000 | 4.0 | 25% |
| Month 3 | ₹25,000 | ₹1,00,000 | ₹1,00,000 | ₹2,00,000 | **8.0** | 12.5% |
| Month 6 | ₹30,000 | ₹1,20,000 | ₹2,10,000 | ₹3,30,000 | **11.0** | 9% |

**Flywheel kaise ghoomta hai:** Ads → sales velocity → hero keywords par **rank upar** → organic (free) sales badhti hai → ad par nirbharta kam → utne hi spend par total sales dugni → Blended ROAS 8–10.

Isiliye A06 Ads Agent ke 2 mode honge:
- **Rank-Push Mode** (shuruaat): 3–5 hero keywords par jaan-bujh kar break-even ads — maksad profit nahi, page-1 rank.
- **Harvest Mode** (rank milne ke baad): unhi keywords ka ad spend ghatao, organic free sales uthao, spend winners par ghumao.
A03 roz hero keywords ki **organic rank track** karega — rank hi is system ki asli sampatti hai.

---

## 3. FBA + Flipkart Warehouse (A09 ka upgrade)

Tumhari baat sahi: material **Amazon FBA + Flipkart Warehouse (Flipkart Assured)** me rakhenge to:
- **Prime / Assured badge** → CTR aur conversion dono upar (badge wali listing ko customer zyada trust karta hai)
- **Fast delivery** → Buy Box aur rank dono ko fayda
- **Transport cost kam aur fix** — khud courier bhejne (₹80–120/order + RTO ka nuksan) ki jagah predictable FBA fee, returns Amazon/Flipkart sambhalega

**FBA Planner kya karega:**
- Har SKU ka **Days-of-Cover**: stock 30–45 din se zyada nahi (storage fee + dry fruits ki shelf-life), 15 din se kam ho to replenishment proposal (Tier-1 approval)
- **Kaunsi SKU FBA me jaye, kaunsi nahi:** tez bikne wali hero SKU = FBA; slow SKU = apna godown (warna storage fee kha jayegi)
- **Festival rule:** Diwali jaise peak se 45 din pehle FBA me stock full — peak me inbound band bheed hoti hai
- **FEFO/Expiry:** pehle expire hone wala batch pehle bikey — dry fruits me ye sabse bada chhupa nuksan hai
- **Cost compare:** har SKU par FBA fee vs self-ship ka hisaab A07 Profit Agent ke saath — jahan FBA mehenga pade, wahan nahi bhejenge

---

## 4. NAYA — A13 Unicommerce Ops Agent

Ab **Unicommerce ka saara kaam bhi yahi system karega.** Koi alag banda, koi alag jhanjhat nahi.

| Kaam | A13 kya karega |
|------|---------------|
| **Order Sync** | Amazon + Flipkart (+ website ho to woh bhi) ke saare orders ek jagah, koi order miss nahi |
| **Ek Stock Truth** | Unicommerce master inventory ↔ Amazon ↔ Flipkart — roz **3-way reconciliation**; mismatch mile to turant alert (stock mismatch = overselling = cancellation = account health kharab) |
| **Channel Allocation** | Stock ko channel ke hisaab se reserve/allocate — Amazon par tez bik raha hai to wahan stock pehle |
| **Warehouse Allocation** | Apna godown, FBA, Flipkart warehouse — order kis facility se jaye, Unicommerce facility mapping ke saath A13 manage karega |
| **SKU Mapping** | Ek hi product ke alag-alag channel SKU codes ki mapping ek master SKU se — galti yahi sabse zyada hoti hai |
| **Returns / RTO** | Return aaya, QC hua, stock wapas system me — ghata kahan ho raha hai, kaunsi SKU/courier se RTO zyada |
| **PO / GRN** | Supplier se kharid ka purchase order aur stock-in entry ka record, A09 forecast se juda hua |
| **Health Report** | Roz: pending orders, dispatch delay, stock mismatch, RTO% — ek report me |

**Integration:** Unicommerce (Uniware) API se. Phase-2 me tumse Unicommerce login/API access lagega — system ready karke dega, tum sirf connect approve karoge.

---

## 5. Updated System — 13 Agents

V1 ke 12 agents (A01 Market Research → A12 Orchestrator) waise hi rahenge, bas 3 badlav:
- **A12 Orchestrator ab Approval Governor bhi hai** — saare proposals, approvals, audit log, guardrails isi ke paas
- **A06 Ads Agent** ko Rank-Push + Harvest mode mile
- **A09 Inventory Agent** ab FBA + Flipkart Warehouse Planner bhi hai
- **+ A13 Unicommerce Ops Agent (naya)**

## 6. Updated Roadmap
- **Phase 0 (7 din):** Audit — ASIN, ad reports, cost sheet, Unicommerce ka current setup
- **Phase 1:** Engines (ready hain) + Approval system + War-room report
- **Phase 2:** Live connect — Amazon SP-API/Ads API, Flipkart, **Unicommerce API**, FBA planner live
- **Phase 3:** Full autonomous — Rank-Push → Harvest flywheel chalu, festival war-plan, scale

## 7. Tumse chahiye (purani list + 2 naye)
1–5. V1 wali list (brand, ASIN links, 90 din sales/ad data, cost sheet, agency details)
6. **Unicommerce** use kar rahe ho abhi? Account hai to uska setup (kitne warehouse/facility, kaunse channel jude hain)
7. **FBA me abhi stock hai ya abhi bhejna hai?** Flipkart warehouse ka status bhi
