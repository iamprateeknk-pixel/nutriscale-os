# NutriScale OS V12 - Master Developer Backlog

Audit date: 22 Oct 2026. Source repo commit: 73f7777ae494d17e5e84d2747918fad613d5a5ff. All material labeled target-state unless clearly described as current.


# 00  Developer navigation and project contract
**Use this PDF as the authoritative target-state build specification.** Current-state evidence appears in Sections 01-05; implementation contracts span Sections 04-22. A developer should convert every unique requirement ID into a tracked work item, attach PR and test evidence, and prove end-to-end flows before marking them DONE.
| Read first | Then implement | How to prove it |
| --- | --- | --- |
| 01-06: baseline, architecture, safety and truth model | P0 auth/approval/data/reporting + modern marketplace access | Release gates A-C and acceptance rows QA-01 to QA-04 |
| 07-13: ads, keywords, listings, peers, ranking, creative, profit | Data-backed growth workflows with explicit sources and costs | Real SKU use cases UC-01 through UC-10 |
| 14-16: UI/UX and AI governance | 16 screens, 8 deeply specified flows, controlled agents | Mobile/desktop screenshots, role-safe interaction videos |
| 17-22: milestones, QA, risk and deployment | Parallel team assignment; staged integration and pilot | Signed finance reconciliation, read-only integration and action proofs |
| 23: sources | Validate versioned third-party assumptions before shipping | Provider docs, access permissions and recorded licence status |
> **Interpretation rule** "Working", "implemented" or "supported" means the current repository only when the baseline explicitly says so. Everywhere else this document uses target-state requirements. Vendor-managed data may be unavailable; the correct product behavior is to display limitation, not invent data or bypass permissions.
**Critical launch order:** Secure and correct first; integrate read-only next; make UI genuinely live; enable controlled writes after formal acceptance; build competitor research and advanced agent learning with licensed evidence. Development can proceed in parallel by team, but risky capabilities cannot be switched on out of order.

# 01  Executive mandate and truth baseline
**Objective:** Deliver a single private, secure, measurable multi-marketplace growth operating system for Dry Fruit Farm. It must help the team improve discoverability, traffic quality, conversion, ad efficiency and contribution profit on Amazon India and Flipkart, without pretending that a proprietary ranking formula can be reverse-engineered exactly.
> **What the developer is being asked to build** This is a **complete target-state specification**, not a claim that all listed capabilities are already available. Deliver through dependency-ordered workstreams with mandatory acceptance gates; one simultaneous big-bang production release is NOT authorised.
| Axis | Verified repository snapshot (22 Oct 2026) | Target after this blueprint |
| --- | --- | --- |
| Core | Python engines, 9 agent classes, SQLite, CSV ingestion, 11 passing CI suites | Typed modular services, robust persistence, monitored pipelines |
| UI | Static multi-section dashboard; only a few KPIs update from backend | 100% API-backed, provenance-aware, interaction-complete UI |
| Ads | Rules produce suggestions; action not verified on seller account | Dry-run -> approval -> execution -> verification -> learning |
| Keywords | Uses existing search-term reports; no genuine reverse-ASIN feed | Source-verified keyword discovery, gaps, ranks and opportunity |
| Competitors | Simple comparison math, demo product rows | Matched peer sets, dated snapshots, explainable win plan |
| Rank | Heuristic weighted model and correlation helper | Observed rank tracking plus controlled experiments |
| Trust / security | Unauthenticated backend, demo kill switch, incomplete audit chain | RBAC, real kill switch, immutable trail, private deployment |
**Audited commit:** `73f7777ae494d17e5e84d2747918fad613d5a5ff` on `main`. GitHub Actions verified 11 suites; job log contains 43 individual PASS assertions while repository prose says 44. Tests include simulated API transports and do not demonstrate live account integration. Code foundation estimated ~65%, end-to-end workflows ~30%, production readiness ~15%; these are separate qualitative measures.
**Do not build a substitute for a licensed data provider by fabricating Amazon/Flipkart search volume, competitor rank, product sales or demand.** Every number in the UI must indicate its source, observation time and confidence/coverage.

## Business outcomes and decision rules
| Metric | Required meaning / formula | Failure that must be prevented |
| --- | --- | --- |
| Contribution profit | Net sales minus COGS, packaging, variable fees, discounts, ads, returns, fulfilment and allocable variable costs | Scaling a loss-making SKU because ROAS looks attractive |
| TACOS | Matched-period ad spend / same-channel total attributed-order or booked-sales basis, explicitly defined | Mixing 60-day orders with 90-day ad cost |
| Paid ACOS / ROAS | Paid ad spend / attributed sales; attributed sales / ad spend; declared attribution window | Combining incompatible windows without flags |
| CVR | Orders or units / clicks or sessions, by clearly named denominator | Comparing unlike denominators across platforms |
| Rank movement | Observed keyword + marketplace + device/geo + date + organic/sponsored position | Calling a heuristic scoring model actual search rank |
| Market share proxy | Use only lawful/licensed data with method and uncertainty | Inventing precise competitor volumes |

# 02  Scope, source hierarchy and release gates

## Evidence classes; always visible to users
| Evidence class | Allowed examples | Displayed badge |
| --- | --- | --- |
| OBSERVED | Own Seller Central / Ads reports, verified listing attributes, authorised public snapshots | Observed; source and timestamp |
| DERIVED | ACOS, contribution, price/100 g, 7-day rank delta; formula and input available | Calculated; formula access |
| ESTIMATED | Provider search-volume estimates, demand models, competitor sales proxy | Estimate; confidence range |
| HYPOTHESIS | Proposed explanation for rank change, inferred image/CVR improvement | Hypothesis; experiment needed |
| DEMO | Synthetic samples for training/QA isolated from production | DEMO ONLY, never on live War Room |

## Definition of release readiness
1. GATE-A FOUNDATION: all private endpoints enforce login + role check; public backend port closed; no sample revenue/rank claims; owner-level kill switch stored server-side.
2. GATE-B TRUTH: same file twice produces identical numbers; order lines/returns/campaign IDs preserved; matched-period KPI controls; cost-unknown blocks profitable-scale recommendations.
3. GATE-C CONNECTIVITY: read-only live certification for Amazon and Flipkart where approved; alternative CSV import has coverage dashboard and explicit manual workflow.
4. GATE-D ACTIONS: approved changes are dry-run compared with vendor state, pushed through real adapter, acknowledged, verified, retried safely or rolled back.
5. GATE-E RESEARCH: competitor/keyword feeds documented with permissions, sampling limits, match confidence, provenance and no forbidden access methods.
6. GATE-F PILOT: owner signs off after two weekly reporting cycles and controlled pilot; financial results reconciled against seller settlement and spend.
> **Outside this release** No guarantee of page-1 ranking, top category seller, 8-10 blended ROAS, fully autonomous self-updating algorithm or guaranteed sales. These are hypotheses/aspirations to test, not acceptance conditions.

# 03  Target architecture and separation of responsibilities

## Recommended implementation topology
| Layer | Suggested components | Non-negotiable boundary |
| --- | --- | --- |
| Frontend | Next.js/React + TypeScript + TanStack Query/table + chart library; accessible component system | Only authenticated backend APIs; no API secrets in browser |
| API | FastAPI (Python) or typed backend retaining existing Python engines; OpenAPI schema | RBAC, tenant/account scoping, validation, versioning |
| Workers | Persistent queue + scheduler (Redis queue/Celery or equivalent); DLQ | No job executed on HTTP request thread |
| Data | PostgreSQL; immutable raw reports in object storage; cache optional | Canonical dimension model; migrations + constraints |
| Integrations | Amazon SP/Ads, Flipkart seller, authorised ads exports, optional Unicommerce / Logic ERP | Capability contracts and read-only certification per adapter |
| Analytics | Metric service, unit-economics evaluator, experiment/statistics service | No silent fee defaults or incompatible denominators |
| Actions | Policy engine, approval state machine, executor, verifier, rollback journal | Never label action EXECUTED before vendor confirmation |
| Observability | Structured logs, health metrics, traces, provider status, alerting, backups | Auditable who/when/why for every data/action change |

## Mandatory processing contract
`Provider/CSV -> raw immutable import -> schema validation -> canonical mapping -> dedupe -> reconciled metrics -> recommendation proposal -> risk/policy validation -> approval -> vendor write -> acknowledgement -> verification -> measured result -> outcome record.`
Every link carries `trace_id`, `platform`, `seller_account_id`, `source_id`, UTC event time, IST display time, data freshness, implementation version, actor/service identity and errors. Use idempotency keys for both data ingestion and write actions.

# 04  P0 | Technical remediation and production safety

### SEC-01  |  P0  |  Access control and private hosting
- Requirement: No unknown user should view metrics or change settings.
- Implement: Add login with MFA for privileged users, RBAC (Owner, Growth Lead, Analyst, Agency Viewer, Operations, Developer/Support), session expiry, per-seller scopes, CSRF or safe bearer flow, TLS. Keep service port private and deny access by default.
- Acceptance: 401/403 verified for unauthorised reads/writes; agency viewer cannot apply actions; external port scan exposes only approved reverse proxy.
- Dependencies: Current `backend/app.py` exposes unauthenticated endpoints and binds 0.0.0.0.

### SEC-02  |  P0  |  Reliable kill switch
- Requirement: Owner needs verifiable emergency stop for future automated writes and ads.
- Implement: Persist kill state in DB; prevent queued/new writes; optionally pause live campaigns only when separately authorised; use remote acknowledgement per campaign; show pending/failed states and hotline fallback.
- Acceptance: Restart does not reset kill state; no action executes after kill; UI never says ad is paused without remote confirmation.

### SEC-03  |  P0  |  Approval state machine
- Requirement: Separate recommendation, approval, execution and measurement.
- Implement: States: DRAFT > PROPOSED > APPROVAL_PENDING > APPROVED > QUEUED > EXECUTING > APPLIED_VERIFIED / FAILED / CANCELLED / ROLLED_BACK. Tier-2 requires two separate owner confirmations; attach action diff, limits, expiration and idempotency.
- Acceptance: Every action has full change log; double confirmation enforced; duplicate POST cannot double-apply; failed writes remain visibly failed.

### DAT-01  |  P0  |  Canonical orders and reporting schema
- Requirement: Avoid false revenue, profit and search term conclusions.
- Implement: Separate orders/order_items/settlements/refunds; campaign identity keyed by provider account and campaign ID; import batch hashes; product mapping dimensions and report date/attribution windows.
- Acceptance: Two-item order remains two rows; reimporting exact CSV is idempotent; same campaign name on Amazon and Flipkart remains separate.

### DAT-02  |  P0  |  Metric reconciliation and incomplete-data gating
- Requirement: No misleading TACOS, organic share or projected savings.
- Implement: Expose coverage %, metric definitions and same-period conditions; stop organic = order sales - ad sales unless attribution/periods reconcile; version definitions.
- Acceptance: If date ranges mismatch, UI shows NOT COMPARABLE and disables derived organic share rather than showing a confident number.

### JOB-01  |  P0  |  Real time-triggered scheduler and durable jobs
- Requirement: Jobs must actually run at configured IST times even after restart.
- Implement: Separate periodic trigger + durable worker; retries/backoff, checkpoints, concurrency lock, job audit and alerts; health/feed jobs cannot just return a plan string.
- Acceptance: Simulate restart, 429, missing credentials, duplicate invocation, DST-independent IST clock and delayed jobs; no duplicate writes.

### UI-01  |  P0  |  Remove all demo claims from production
- Requirement: No static competitor data, rates, approval badges or rank claims visible in live mode.
- Implement: Rebuild frontend with typed endpoints; no hard-coded live SKU arrays; labels for DEMO vs LIVE; same-origin browser configuration; all buttons bound to backend actions.
- Acceptance: Empty DB screenshots show zero invented numeric examples; browser network calls are authorised; every action persists/reloads correctly.

### SEC-04  |  P0  |  Credential isolation and secrets handling
- Requirement: Do not put marketplace credentials in code, logs or chat.
- Implement: Encrypted secret storage, rotation, least privilege, server-only OAuth, audit, no raw PII on dashboards, backups encrypted; secrets detection in CI.
- Acceptance: Secrets scan passes; access denied to roles without integration permission; safe rotation without deployment downtime.

# 05  Data integration matrix: Amazon, Flipkart and related systems
| Feed / capability | Amazon India | Flipkart | Release rule |
| --- | --- | --- | --- |
| Orders, items, returns | SP-API Orders current supported version + reports | Seller APIs + CSV exports | Read-only first; line-level reconciliation |
| Listings / catalog | Listings/Catalog SP APIs, content reports | Seller listing APIs | Permission-scoped edits |
| Ad campaigns / targets | Amazon Ads API and reports | Seller ad reports; verify seller-specific programmatic ad access | CSV fallback; no imagined Ads API capability |
| Search terms | Amazon sponsored search terms; clicked terms caveat | Ads console reports if accessible | Do not confuse with total shopper query volume |
| Inventory / fulfilment | FBA/FBM reports | Seller/fulfilment stock + returns | Facility + lot/expiry mapping |
| Competitor ASIN/FSN | Approved/licensed providers or policy-compliant monitored observations | Approved marketplace/product intelligence sources | Never imply seller API exposes competitor keyword ranks |
| Finance | Settlement, transaction, ad invoice, fee schedules | Settlements, commissions, logistics, tax exports | Cost + ad + refund alignment |
| Store/WMS | Optional Logic ERP/Unicommerce import | Same canonical SKU map | Disable if not actually used |

### INT-01  |  P0  |  Amazon SP-API modernisation
- Requirement: Current connector expects obsolete AWS key/SigV4 requirement and older Orders v0.
- Implement: Use Login with Amazon (LWA), roles, consent, secure refresh; implement current Orders v2026-01-01 migration with item/proceeds fields where permitted; cursors, retries, rate limits and token refresh.
- Acceptance: Live authorised read-only sample: 100% paginated orders/items matched to Seller Central report. No AWS signing required for SP-API requests.
- Dependencies: Official Amazon Orders API docs and 2023 SigV4 announcement [S1,S2].

### INT-02  |  P0  |  Amazon Ads reports end to end
- Requirement: Code requests a Sponsored Products report but does not fully poll/download/import it.
- Implement: Implement profile discovery, campaign/ad group/target/placement reports, async report create-poll-download-decompress-validate-store, attribution metadata, spend reconciliation; ads write capabilities separated.
- Acceptance: One successful report and one rate-limited retry demonstrated on authorised account.
- Dependencies: Official Amazon Ads Search Term Reports [S3].

### INT-03  |  P1  |  Flipkart account sync + ads feasibility
- Requirement: Existing Flipkart connector is thin and live sync command is incomplete.
- Implement: Connect approved seller endpoints for listings/orders/returns/inventory; for ads first document actual accessible APIs/export format and permission. Implement CSV/SFTP/manual feed where programmatic ads access unavailable.
- Acceptance: Real seller report/API parity; ads automations explicitly disabled unless approved writable interface certified.
- Dependencies: Official Flipkart Seller API docs [S4,S5].

### INT-04  |  P1  |  Reliable CSV and manual fallback
- Requirement: Operations must continue without API permission.
- Implement: Wizard: identify platform, report type, date/attribution, header mapping, dry-run preview, duplicates, error rows, source hash, import receipt, historical backfill, rollback import.
- Acceptance: Reimport produces no duplicate; invalid dates/units are quarantined; importer exports an exceptions sheet.

### INT-05  |  P1  |  External competitive intelligence provider contract
- Requirement: Seller APIs alone do not provide all reverse-ASIN/volume/history signals.
- Implement: Create data-source adapter interface with supported marketplace, permitted fields, licensing, rate limits, TTL, geographic/device coverage, uncertainty bands and price per query; import licensed vendor exports.
- Acceptance: For an unavailable metric show UNAVAILABLE with explanation; do not simulate ranking/search volume.

# 06  Product and financial truth model

## Core records / required keys
| Entity | Important fields (minimum) | Relationships and validation |
| --- | --- | --- |
| ProductMaster | master_sku, brand, product, grade, origin, pack_g, lot, EAN/GTIN, verified_claims | One physical SKU may map to multiple listing IDs |
| MarketplaceListing | platform, account, ASIN/FSN, seller_sku, URL, title, content, status, media | Listing version history + listing health observations |
| OrderHeader/Items | platform, seller, order_id, item_id, sku, qty, gross, refund, status, timestamps | Multiline; cancellations / refunds not overwritten |
| AdFact | platform, account, campaign_id, adgroup_id, target_id, sku/ASIN, date, impression, click, spend, sales, units | Attribution window, report type, placement, currency |
| KeywordMetric | phrase, platform, source, time, search_volume, rank_org, rank_ads, CPC, coverage | Estimated/observed flag, rank geo/device evidence |
| PeerProduct/Snapshot | peer ID, product URL, capture_id, grade, grams, total_price, coupon, rating, reviews, badge, delivery | Snapshot time, match confidence, source permission |
| CostVersion | sku, effective_from, net landed COGS, packaging, fee plan, GST basis, agency allocation | Block scale when costs unknown or stale |
| Action/Experiment | proposal_id, user, risk, expected impact, approval, execution ID, verified outcome | Immutable action timeline; rollback version |

## Non-negotiable data validation rules
- Marketplace price/pack comparison requires normalized `₹ / 100 g` or `₹ / kg`; never mix 200 g W320 cashew with 500 g W240 without grade flag.
- `Unknown` must not be interpreted as zero for product cost, ad spend, coupon, competitor price, returns or seller health.
- Each time series data point stores captured_at and ingested_at; show stale indicators; never connect performance changes to unsupported cause.
- Multi-pack/hampers have BOM, packaging and bundle COGS; separate per-item inventory reservations; actual GST/tax treatment verified with accountant.
- Keep list price, applied coupon, shipping, fulfilled price and effective delivered price distinct; match the buyer-visible location where known.

# 07  Ads Growth Studio | rule-based + intelligent + safe
This is the primary growth lever after listing conversion and accurate contribution margins. Amazon Sponsored Products first; Flipkart-specific reports and approved action capabilities second. No change is directly applied from LLM free text.

### ADS-01  |  P0  |  Campaign health + action queues
- Requirement: Growth lead needs to see what wastes spend and what can profitably scale.
- Implement: Campaign/target/search term tables with SPEND, impressions, clicks, CPC, CVR, ROAS, ACOS, TACOS, organic rank, profit after ads, budget consumed, report freshness; filters by SKU, agency, marketplace, period, status, owner.
- Acceptance: Selecting one SKU reproduces finance-grade metrics; action cards explain evidence and no-cost unknown values.

### ADS-02  |  P0  |  Profit-led bid recommender
- Requirement: Do not use fixed global ROAS 4 or arbitrary daily cap for every SKU.
- Implement: Target ACOS from SKU contribution-before-ad and owner profit floor; max CPC = conversion probability x net revenue x allowed ACOS (consistent units); confidence intervals, click/order thresholds, attribution delays, caps.
- Acceptance: Model never scales on unknown SKU costs; proposed bid always shows before/after, max daily change, worst-case spend and reason.

### ADS-03  |  P1  |  Campaign restructuring and harvesting
- Requirement: Harvest converting search terms while protecting high-value discovery campaigns.
- Implement: Detect converting broad/auto terms to exact; negatives only after query intent, conversion data and cross-campaign impact checks; budget distribution by marginal contribution; placement/ASIN targeting when supported.
- Acceptance: Bulk preview lists affected campaigns; no accidental exclusion of winning terms; changes deduplicated.

### ADS-04  |  P1  |  Pacing, anomalies and live budget control
- Requirement: Unexpected spend spike or inventory shortage must not burn cash.
- Implement: Hour/day spend pace, ROAS drop, CPC spike, out-of-budget, zero inventory and policy issues; kill/pause triggered only through verifiable write connector and approved policy.
- Acceptance: Injected overspend event makes alert; remote pause state checked; no false "ads stopped" confirmation.

### ADS-05  |  P1  |  Ad portfolio optimizer
- Requirement: Spend budget should move to contribution-positive incremental opportunities.
- Implement: Budget scenarios by SKU/season, max acceptable TACOS, organic vs paid rank, coupon cost, stock cover, margin; holdout/experiment option and notes.
- Acceptance: Owner can compare current vs proposal vs conservative case in rupees; budget caps enforced across agents.

### ADS-06  |  P2  |  Automation policies and AI advisor
- Requirement: Intelligence may propose but rules must control money.
- Implement: Tier-0 only safe notifications/read-only; low-risk writes opt-in after pilot; Tier-1 approval for bid/budget/negative; Tier-2 for large deltas, price or listing publish.
- Acceptance: Every executed campaign change has real vendor response, re-fetch verification and measured before/after.

# 08  Keyword Lab | Cerebro/Magnet-inspired capabilities

## Research tabs and outputs
| Tab | What user can do | Data feasibility |
| --- | --- | --- |
| Seed discovery | Input "california badam 200g"; related terms, long tails, misspellings, clusters, intent, relevancy | Owned search-term reports + provider/catalog sources |
| Reverse product | Input own/peer ASIN/FSN; compare keywords with observed/estimated ranking and evidence | Licensed keyword/rank provider or authorised platform feature |
| Keyword overlap | 2-10 matched peers; own missing keywords, peer coverage, ranking distribution | Requires verified rank universe; otherwise text-only listing gap |
| Keyword tracker | Hero terms; daily rank trajectory, paid/org tags, search locale, device, freshness | Permitted ranking observations; no forbidden scraping |
| Opportunity score | Normalized demand, relevancy, difficulty, conversion and margin, with uncertainty | Versioned model; never claim platform algorithm |
| Keyword placement | Show target keywords by title, bullet, backend, A+, campaign & content version | Own listing metadata; possible public peer text only |

### KWD-01  |  P1  |  Real query taxonomy and keyword provenance
- Requirement: Current code guesses search volume from `clicks * 20`; this is not actual volume.
- Implement: Replace heuristic with observed own search terms and labelled external provider estimates. Use dedupe, Hindi transliterations, singular/plural, size-grade intent, brand terms and competitor terms.
- Acceptance: Volume displays estimated source and date; without provider shows "unknown"; no fabricated search volume.

### KWD-02  |  P1  |  Reverse-ASIN / reverse-FSN research
- Requirement: Understand which keywords matched competitors appear for while own SKU lags.
- Implement: Use a legal data adapter; fetch supported peer keyword ranks, coverage and trend; pair with peer comparability. If unavailable, downgrade to listing-text and own search-term gap only.
- Acceptance: Results include method/provenance, confidence, geo/device, organic/sponsored; unavailable states explicit.

### KWD-03  |  P1  |  Keyword Opportunity Matrix
- Requirement: Select high-fit, profitable keywords for Cashew W320, Almond California, Brazil Nuts, Cranberry.
- Implement: Score with demand signals, grade/pack match, relevance, conversion evidence, keyword difficulty estimate, target CPC and contribution margin; include exclusions (wrong grade, wholesale intent).
- Acceptance: Every recommended term ties to SKU, intent, expected risk and owner action. UI provides detail drawer and cohort history.

### KWD-04  |  P1  |  Rank movement alert and keyword grouping
- Requirement: Identify positive/negative shifts reliably.
- Implement: Keywords grouped product/grade/season, organic vs ad rank, captured SERP conditions, tracked peers, volatility, rank coverage and alert thresholds.
- Acceptance: Alert contains at least 3 comparable data points and uncertainty; supports mute/snooze and remediation ticket.

# 09  Listing Intelligence | quality, content, conversion

### LST-01  |  P0  |  Fact-safe listing score v2
- Requirement: Current listing score is mostly a checklist; upgrade to buyer and policy value.
- Implement: Versioned 100-point weighted score for keyword fit, title readability, attributes, images, bullets, A+ eligibility, actual reviews, price/grade context, fulfillment and compliance; weights editable by admin but not confused with Amazon ranking formula.
- Acceptance: Score breakdown and raw evidence shown; score not claimed to be Amazon ranking score.

### LST-02  |  P1  |  Listing content audit and competitor gap
- Requirement: For a given SKU compare equivalent peers content and trust.
- Implement: Highlight missing sizes, grade/origin/processing, use cases, photo types, review objections, inconsistent claims, indexed keyword coverage, misplaced pack weights. Generate proposed title/bullets/attribute edits with before/after preview.
- Acceptance: Never auto-claim nitrogen flush, organic, diabetic-friendly, no sugar or lab test without recorded proof.

### LST-03  |  P1  |  Image/video/A+ creative lab
- Requirement: Improve CTR and CVR with controlled creative.
- Implement: Brand asset library, shot storyboard, white-background primary image policy checks, pack legibility at mobile size, size proof, nutrition verified by source, contextual imagery, video scripts; optional image-generation workflow with human QC.
- Acceptance: QA records resolution, legibility, no false pack representation; experiments log original/revision. AI artifacts not auto-published.

### LST-04  |  P1  |  Listing editor and publish approval
- Requirement: Keep source-of-truth content plus versions.
- Implement: Editor for title/bullets/attributes/backend terms/A+ drafts with claim evidence citation, role-based approval, publish status and pullback.
- Acceptance: No publish without review; rejected edits remain documented; exact diff can be restored.

### LST-05  |  P2  |  Voice of Customer to conversion fixes
- Requirement: Use product feedback to prioritise improvements.
- Implement: Cluster verified reviews/returns into size, freshness, taste, packaging, price, shipping, confusion; attach representative evidence and corrective work tickets.
- Acceptance: No synthetic reviews; claims based on sufficient real responses, not one-off comments.

# 10  Competitor Observatory | flagship specification
This module answers the user's central question: **What are comparable competitors actually doing? What are we doing differently? Which specific evidence-backed change should we test to improve visibility, conversion and profitable ranking?** It must NOT manufacture competitors' ad spend, sales, conversions or search rank from public listing text.

## A. Competitor discovery and matching
1. Start with one Dry Fruit Farm ASIN/FSN/SKU and category (e.g., Cashew W320 200g). Ingest own verified master facts.
2. Find candidate peer products from approved marketplace/product data feed, licensed research provider or manually entered verified URLs. Store the source and last captured date.
3. Score equivalence: nut type, grade (W320 != W240), weight, processing (raw/roasted/salted), origin, brand tier, packaging type, fulfillment and buyer use case.
4. Divide into STRICT PEERS (same grade/pack), NEAR PEERS (different pack but normalized comparison possible), ALTERNATIVES (different positioning) and NOT COMPARABLE.
5. Explicitly show peer rejection reasons, manual override with explanation and reviewer audit. Prevent matching by name similarity alone.

## B. Required competitor signals
| Signal bucket | Fields to capture | Answer produced |
| --- | --- | --- |
| Offer and price | MRP, visible selling price, coupon, 100g/kg normalized rate, delivered price if available | Who undercuts our comparable product, by how much and since when? |
| Value/pack | Grade, weight, origin/claims, bundle, packaging photos, premium markers | Is lower price actually lower grade or poorer pack value? |
| Conversion / trust proxies | Public rating, review count, review trend, badges, verified delivery promise | Which buyer trust gap needs attention? |
| Content / SEO | Title terms, bullets, images, rich content, attributes, relevant use cases | Which details have peers shown that our listing omits? |
| Availability | Visible in-stock status and shipping promise at sampled geography | Do competitors win due to stock/fulfilment? |
| Visibility (if licensed) | Organic/sponsored rank by query, keyword overlap, historic position | Where are we behind on a specific keyword? |
| Offers / merchandising | Coupons, deal tags, content updates, product variation changes | What changed in last 7/30 days? |
| Review themes | Supported review excerpts/sentiment summaries, complaint themes with sample counts | Which quality issue or proof could affect our CVR? |

## C. Snapshot cadence and change detection
Own listings and seller data: prefer daily sync; competitor offers/content: only as allowed by source license and rate limits, normally at 24h/7d cadence; ranking: only under authorised provider terms. Store `before_snapshot`, `after_snapshot`, `change_type`, `delta`, `source_url`, `captured_at`, `coverage`, `confidence`. A missing value is unknown, not stockout or zero price.

## D. Recommendation engine: difference -> cause hypothesis -> business action
| Observed peer finding | What our engine checks next | Recommended controlled action |
| --- | --- | --- |
| Comparable peer 8% cheaper | Own verified net margin, shipping/pack cost, value tier, peer confidence | Test smaller coupon/pack-value proof before price cut; reject if margin floor broken |
| Peer rating +0.3, 10x reviews | Own rating/returns/root complaints; product/grade parity | Improve pack and product proof; compliant review collection; no manipulation |
| Peer title covers "California almonds 200g" | Own listing actual grade, search-term relevance, title space | Add verified term to draft, evaluate readability, test and monitor relevant search traffic |
| Peer more images/grade scale photo | Own main image click-through and gallery, packaging accuracy | Prepare size-comparison secondary image; primary image only per marketplace policy |
| Peer keyword rank improves after discount | Price change history, inventory, sales, seasonality, competing ads | Label as correlation, create experiment; do not claim discount caused rank rise |
| Peer faster shipping and in stock | Own fulfillment SLA, stock cover, location, cancellation rate | Fix stock/replenishment or service promise; avoid unprofitable ad scaling |

## E. Worked comparison (illustrative data only - NOT actual competitor observation)
| Example measure | Dry Fruit Farm Cashew W320 200g | Strict peer A (hypothetical) | Proposed investigation |
| --- | --- | --- | --- |
| Offer price | INR 279 | INR 259 | Difference 7.7%; check COGS+fees before coupon |
| Normalized price | INR 139.5 per 100g | INR 129.5 per 100g | Confirm same grade, salted/raw and origin |
| Rating/reviews | 4.1 / 26 | 4.4 / 180 | Review theme, pack-size proof, shipping experience |
| Title coverage | Cashew W320 200g | W320, whole, grade, snacking | Check verified attribute and keyword relevance |
| Gallery evidence | 4 images | 7 images + size proof | Design and A/B-test size-comparison image |
| Rank for query | Unknown | Unknown | Connect approved tracking provider; do not guess |
**Example decision:** A price cut is NOT automatic. First compute contribution profit at INR 279 versus INR 269 and INR 259 including fees, coupons, ads and returns. If margin floor is violated, propose improved proof of grade/quality or a targeted ad/creative test instead. Track matched keyword rank, CTR, CVR, units and *net contribution* after 14/28 days.

### CMP-01  |  P1  |  Peer discovery and exact matching
- Requirement: Match Cashew/Almond/Brazil/Cranberry by grade, pack and processing.
- Implement: Canonical peer comparator, normalized price engine, confidence, exclusions and human overrides.
- Acceptance: In test corpus, W240 is not tagged exact W320; 200g/500g converted correctly with displayed assumptions.

### CMP-02  |  P1  |  Competitor change feed with proof
- Requirement: Explain which offer, image, keyword, review or stock attribute changed.
- Implement: Dated snapshot archive, diff detector, visual/media evidence links, change type and source legal basis.
- Acceptance: Every event links to both snapshots; no event emitted on missing/failed capture.

### CMP-03  |  P1  |  Competitive Opportunity Board
- Requirement: Rank recommended actions by realistic potential and confidence.
- Implement: Opportunity score from own revenue/traffic, comparable peer gap, likely CVR risk, estimated effort/cost, margin, inventory readiness; each card creates experiment/approval ticket.
- Acceptance: Cards show why, supporting observation, risk, cost, owner and re-evaluation date; not just "beat competitor".

### CMP-04  |  P2  |  Win/Lose post-change monitor
- Requirement: Did our changes improve rank or conversion while preserving profit?
- Implement: Tie action IDs to before/after snapshots, rank and ad metrics; control seasonality/stock/ads where possible; log observed vs suspected effects.
- Acceptance: No causation claim from simple Pearson correlation; controlled experiment readout includes sample size and uncertainty.

# 10A  Competitor-to-rank strategy playbooks: exact decision mechanics
The competitor engine must transform **dated observations** into **testable strategic recommendations**, not generic advice such as "improve listing" or "lower price". Produce one decision packet per own product / competitor / relevant keyword, with a clear trail from evidence to cost to experiment to actual results.

## Competitor decision packet - mandatory fields
| Field | Specification and why it matters |
| --- | --- |
| Comparison scope | Our product/ASIN/FSN, peer listing URLs, exact-match class, variant/grade, marketplace and buyer region. Store manual match override and reason. |
| Source evidence | Captured price/content/reviews/media/stock where available, source ID, snapshot time, freshness TTL, licensing, confidence and unavailable fields. |
| Gap decomposition | Normalized INR per 100g, grade difference, total delivered price, trust difference, content/attribute gaps, fulfillment and visible promotions; separate observed from inferred. |
| Keyword overlap | Owned high-intent search-term gaps and validated external reverse-ASIN/rank data only if available. Mark the provider, region and accuracy limits. |
| Opportunity hypothesis | Specific mechanism: title relevance, photo size clarity, price/value objection, out-of-stock, delivery promise or ad targeting. Include alternatives, not one asserted cause. |
| Financial guardrail | Current contribution, target floor, cost sensitivity, incremental unit sales needed, max CPC and maximum experiment spend. Reject when cost unknown. |
| Experiment design | One primary metric, one intervention, date range, matched baseline/control where possible, contamination events, low-sample fallback and stop/rollback rules. |
| Outcome & learning | Observed change in conversion, contribution, search rank, sales mix and returns. Explain what remains inconclusive; feed validated learning only. |

## Five playbooks the development team must implement

### CP-01 | Price advantage but poor conversion
A strict peer is cheaper or offers a coupon. Inspect grade, actual delivered total, reviews, stock and own contribution. Present 3 options: hold price and prove quality; targeted coupon; pack-size or bundle variant. Compare expected and downside contribution at equal demand.
**Acceptance:** Coupon approval requires cost version and non-negative profit after ads; rank impact stays a hypothesis pending test.

### CP-02 | Content/indexing competitor gap
Peer copy covers grade/pack/primary intent absent from our title, while our conversion terms show demand. Draft factual title+attribute changes and measure click/conversion effects. Never stuff irrelevant competitors' brand names in own listing.
**Acceptance:** Evidence includes terms and product attributes; policy approval before publish; count keyword coverage but never promise indexing.

### CP-03 | Peer has better reviews and value proof
Peer has stronger public trust signals. Analyse own buyer complaints on freshness, small size, breakage, perceived value and delivery, clustered by verified sample. Suggest operational fix and authentic media proof, not review manipulation.
**Acceptance:** Review samples and actual product facts attached; actions include quality-check ticket and image content ticket.

### CP-04 | Peer gains visibility with weak economics
Observed peer ranking improves while its price falls. Do not chase price blindly. Run margin sensitivity, source-check rank conditions, inspect seasonality and ad changes before an experiment.
**Acceptance:** Rank change is only labelled observed; no precise peer ad spend or causation is invented.

### CP-05 | Competitor stockout or slow promise
Visible peer stockout at sampled location may create opportunity, but verify own inventory, age/expiry, delivery promise and incremental ad unit economics before scaling.
**Acceptance:** Low-stock/freshness guardrails block scale; capture region and observation time on stock indication.

## Output example: how a recommendation should be written
> **Action packet example (illustrative; no actual peer claimed)** **Dry Fruit Farm Cashew W320 200g** compared to a confirmed W320/200g peer: observed offer INR 279 vs INR 259; estimated peer customer review advantage; our own margin verified at current price only. **Hypothesis:** clearer grade/size image could improve CTR without price reduction. **Propose:** create secondary image + title fact check, pilot for 14 days; hold price until net-profit sensitivity and baseline are approved. **Do NOT claim:** rival sales, exact search-volume, platform algorithm preference or guaranteed rank uplift.

# 11  Ranking Intelligence | measure, hypothesise, test
> **Ranking reality** Amazon and Flipkart ranking formulas are proprietary. NutriScale can **track observed organic/sponsored rank**, isolate contributing levers and compare controlled interventions; it must not present guessed factor percentages as official platform facts.

### RNK-01  |  P1  |  Rank tracker with scope
- Requirement: Track where listing appears for specific query in comparable conditions.
- Implement: Fields: platform, search term, rank type, product, date/time, locale, device, page, sponsored slot, source/provenance and sample coverage.
- Acceptance: Rank trend screen labels observed vs unavailable; geo/device conditions displayed in tooltip.

### RNK-02  |  P1  |  Rank diagnostic engine
- Requirement: Prioritise fix when ranking falls.
- Implement: Before blaming title, inspect stockouts, price, ratings, fulfillment, campaign changes, seasonality, indexing eligibility, search demand, CTR and CVR. Return ranked hypotheses with evidence.
- Acceptance: At least 3 observed points required for rank alerts; no recommendation based solely on algorithm-weight guess.

### RNK-03  |  P1  |  Keyword-to-rank-to-profit funnel
- Requirement: Link profitable queries to actual SKU outcomes.
- Implement: Map query -> visibility proxy -> owned traffic -> conversions -> attributed/ad spend -> net contribution; show data coverage per segment.
- Acceptance: Test query shows accurate joins; missing ranking provider does not block owned conversion analysis.

### RNK-04  |  P2  |  Experiment-controlled rank improvement
- Requirement: Learn which tactical improvements translate to measurable uplift.
- Implement: Experiment variants, baselines, guardrails, 7/14/28-day cohorts, traffic considerations; exclude confounders and alert on inventory/price changes during experiment.
- Acceptance: Result is `WIN / LOSS / INCONCLUSIVE` with method, uncertainty, sample and material business impact.

# 12  Creative / Conversion Lab and test science

### CVR-01  |  P1  |  Image critique and brand QA
- Requirement: Analyse true buyer clarity, not just image count.
- Implement: Image gallery with zoom/mobile crop; score pack legibility, grade/size explanation, product consistency, compliant white background, lifestyle relevance; use AI critique as suggestion only.
- Acceptance: Every image suggestion includes expected buyer question answered and human QA status.

### CVR-02  |  P1  |  Copy experimentation
- Requirement: Version title/bullets and measure without changing too many factors.
- Implement: Draft candidates, grade/proof validation, side-by-side diff, staged launch, outcome notes; test one primary hypothesis at a time.
- Acceptance: Reject policy/fact-unverified claims; exact original restored by rollback.

### CVR-03  |  P1  |  Experiment registry
- Requirement: Track genuine control and candidate to avoid story-telling.
- Implement: ID, owner, platform, item, start, stop, hypothesis, primary metric, sample size, statistical plan, contamination tags, decision and follow-up.
- Acceptance: Cannot mark statistical win without minimum defined evidence; multiple looks/corrections documented.

### CVR-04  |  P2  |  Festival/gifting growth lab
- Requirement: Baskets and hampers need specific launch support.
- Implement: Bundle BOM, profitability, photos, seasonal keyword clusters, AOV and profitability scenarios, fulfillment availability; compare gift pack SKUs separately.
- Acceptance: Combo cannot launch if component stock insufficient; profit includes actual packaging and assembly.

# 13  Profit, settlements, inventory and agency accountability

### FIN-01  |  P0  |  Finance-grade contribution at SKU + order + channel
- Requirement: Scale decisions depend on validated costs.
- Implement: Versioned COGS, packing, fee, shipping, refund/returns, tax basis, coupon, ad spend, agency allocation. Reconcile invoice/settlement deposits; unknown cost blocks spend increase.
- Acceptance: 5 actual settlement samples reconcile within agreed tolerance; assumptions labelled and signed off by finance.

### FIN-02  |  P1  |  Marketplace reconciliation and return losses
- Requirement: Order gross is not bank payout.
- Implement: Settlement, fee, TCS/TDS/GST where applicable, coupons, penalties, logistics, refund and net realisation tables; provider-wise versions.
- Acceptance: Exception report explains difference between order GMV and payout; partial refunds matched by item.

### INV-01  |  P1  |  Stock-to-ads safety
- Requirement: Do not advertise unavailable or expiring goods.
- Implement: Stock per warehouse/FBA/seller channel; pack+lot expiry, days of cover, inbound shipment; alert on negative/reserved/unavailable units.
- Acceptance: A test stockout blocks new promotion proposals; existing campaigns are flagged for verified pause if authorised.

### INV-02  |  P1  |  Hamper BOM and stock planning
- Requirement: Bundle inventory must reflect component availability.
- Implement: Master SKU component table: Almond 100g + Cashew 100g + Dates 100g + box/label etc; reserve stock on listing/order plans; cost by BOM.
- Acceptance: 2 hampers reserve exact components; stock and batch expiry consistency verified.

### AGY-01  |  P1  |  Agency scorecard and audit
- Requirement: Compare agency action with real business results and fees.
- Implement: Agencies get role-scoped tasks, weekly changes, planned vs applied, cost per platform, tickets, read-only observations, ROI and missed deadlines; change log by actor.
- Acceptance: Weekly report separates agency-reported activities from vendor-confirmed changes.

# 14  Advanced UI/UX | information architecture + design system
Desktop first for analyst workflows and mobile first for approvals/alerts. Product must be information-dense without hiding evidence, profitable impact or execution state. Do not imitate Helium 10 branding; build original Dry Fruit Farm / NutriScale visual language.

## Navigation and hierarchy
| Primary area | Sub-screens / drilldowns | Pinned high-value controls |
| --- | --- | --- |
| War Room | Executive today, anomalies, goals, owner inbox, activity feed | Date, channel, seller account, freshness, currency |
| Research | Keyword Lab, Peer Discover, Competitor Monitor, Opportunity Finder | Seed/ASIN/FSN input, comparison set, export |
| Growth | Ads Studio, Listing Lab, Rank Tracker, Creative Lab, Experiments | Dry-run mode, proposal basket, profit gate |
| Operations | Inventory/FBA, Returns, Settlements, Agency, Gifting | Stock/out-of-date alerts, batch tasks |
| Governance | Approval Queue, Learning, Source Registry, Runbook, Job Status | Kill switch, write mode, policy status |
| Admin | Accounts, role permissions, source connections, fee tables, secrets meta | Owner-only guards, backup status |

## Visual tokens and responsive specification
| Component | Implementation contract |
| --- | --- |
| Palette | Navy #102B3F for hierarchy; Teal #057C81 for primary actions; pale gray #F2F7F9 for grouped surfaces; amber warning; red safety; green verified success. Color never sole meaning. |
| Type | Clear 3-level headings (24/16/13px typical), readable body 13-15px tables, tabular digits, right-aligned INR amounts and percentage deltas; monospaced IDs in detail drawer. |
| Grid | 1440px screen: 240px collapsible navigation, 24px gutters, 12-col canvas; 1024px: condensed sidebar; <=768px: bottom nav for high-value actions, tables as cards/drawers. |
| Charts | Synchronized cursor, labelled axes and units, baseline period overlay, annotations at action dates, no unverified trend line; download CSV and methodology. |
| Tables | Sticky identifier and header, server pagination, 20/50/100 rows, multi-sort, saved views, column chooser, numeric filters and click-to-open right drawer. |
| States | Loading skeleton, no-data, source unavailable, stale, API timeout, insufficient sample, permission denied, action pending, vendor failed, success verified. |
| Accessibility | Keyboard-first, visible focus, >=4.5:1 normal text contrast, accessible tooltips, semantic charts/data table summary, mobile touch targets >=44px. |
| Audit | Every visible value shows source and last synced; every recommended action shows rationale, confidence, cost/risk, permission and status. |

## Interaction recipe - evidence to execution
1. User selects SKU from global search; detail drawer opens with comparable peers, rank timeline, CVR, margin and inventory readiness.
2. Opportunity board shows a ranked plan: what changed, difference vs peers, observed evidence, confidence and expected profit sensitivity.
3. Click "Build test" opens experiment designer with hypothesis, target keyword, image/title/price variant, inventory and profit guardrail.
4. Click "Preview action" creates exact vendor write diff in dry-run mode, plus risk warnings and required approver.
5. After approval system queues vendor write, then fetches remote state; UI status stays pending until verification.
6. War Room annotates action date on time-series chart and measures 7/14/28-day revenue, CVR, rank and net contribution against baseline/control.

# 15  Every production screen: data, interaction and states

### UX-01  Executive War Room
**Content / visuals:** KPI cards for net sales, contribution, spend, TACOS, revenue by channel, order units; alert board; 7/30/90 day time series.
**Primary interactions:** Click cards to drill; export weekly management report; filters persist in URL.
**Required state handling:** No data, stale report, incomplete-cost, API outage, demo disabled.


### UX-02  Product Intelligence Detail
**Content / visuals:** Price, grade, reviews, creative, rank, seller health, margin, inventory and channel variants for single SKU.
**Primary interactions:** Select Amazon/Flipkart, compare peers, open action basket, share verified report.
**Required state handling:** Missing ASIN, mapping conflict, unknown cost, stale content.


### UX-03  Competitor Observatory
**Content / visuals:** Peer selector, product matching confidence, price-per-100g grid, snapshots, keyword overlap and media comparison.
**Primary interactions:** Approve/reject peers, subscribe to changes, see diff evidence and create test.
**Required state handling:** Peer unavailable, data provider limit, not comparable, capture blocked.


### UX-04  Peer Product Side-by-Side
**Content / visuals:** 2-5 matched peers with grade, pack, price, rating, stock, image count, keyword coverage and trend.
**Primary interactions:** Freeze SKU, toggle exact/near peers, normalize weight, explain exclusions.
**Required state handling:** Unknown coupon/shipping, stale snapshot, unmatched grade.


### UX-05  Keyword Research Explorer
**Content / visuals:** Demand source, own search terms, suggestions, clusters, sponsored/organic rank, gap matrix.
**Primary interactions:** Bulk shortlist, assign to listing/campaign, compare keyword intent.
**Required state handling:** No licensed volume data, small sample, duplicate synonyms.


### UX-06  Rank Tracker
**Content / visuals:** Keyword trend chart by geo/device, own ASIN/peer overlay, rank volatility and action annotations.
**Primary interactions:** Open diagnostic drawer, attach hypothesis and schedule experiment.
**Required state handling:** Observed vs estimated source, rank outage, mismatch sample.


### UX-07  Ads Command Center
**Content / visuals:** Campaign-to-target performance tree, target ACOS, profit contribution, anomaly and budget pacing.
**Primary interactions:** Propose exact negative/bid/pauses; batch dry-run and approve.
**Required state handling:** Ads API read-only, budget missing, bid outside max, attribution delay.


### UX-08  Listing Quality Analyzer
**Content / visuals:** Quality composite, score components, keyword coverage, listing facts, policy issues.
**Primary interactions:** Edit evidence-backed title/bullets, preview before/after, publish through approval.
**Required state handling:** Unverified origin/nutrition, image mismatch, duplicate SKU.


### UX-09  Creative and A+ Lab
**Content / visuals:** Image asset gallery, mockups, storyboard, mobile legibility evaluation, proof registry.
**Primary interactions:** Request/approve creative, compare candidates, start A/B experiment.
**Required state handling:** AI output not approved, marketplace image policy unavailable.


### UX-10  Experiment Center
**Content / visuals:** Registry with hypothesis, owner, cohort, start/end, risk, intervention and results.
**Primary interactions:** Start/suspend/stop, attach control and intervention, document learning.
**Required state handling:** Too few samples, concurrent interventions, inconclusive result.


### UX-11  Profit and Settlement Center
**Content / visuals:** Order-level reconciliation, fees, net contribution waterfall, cost versions, profitability by SKU.
**Primary interactions:** Import actual invoice, compare assumptions, approve costs, margin scenarios.
**Required state handling:** Unknown COGS, stale fee table, mismatched payout.


### UX-12  Inventory & Festival Planner
**Content / visuals:** Lot/expiry, available-to-sell, transfer plan, stock cover, gift-BOM and peak calendar.
**Primary interactions:** Replenishment recommendation, kit feasibility, ads stock safety.
**Required state handling:** Unsynced inventory, negative stock, expired batch.


### UX-13  Governance / Approval Inbox
**Content / visuals:** Full diff, evidence, financial risk, countercheck, requester, expiry, approver.
**Primary interactions:** Approve/reject/request change; double confirmation; audit download.
**Required state handling:** Permission denied, superseded, remote rejected, killed writes.


### UX-14  Integrations & Data Quality
**Content / visuals:** Account connections, per-report coverage, last sync, source cost, quota, failure reasons.
**Primary interactions:** Reauthenticate, manual upload, run read-only test, inspect failed rows.
**Required state handling:** API denied, provider quota exceeded, report stale.


### UX-15  Agency Performance Board
**Content / visuals:** Task ownership, plan vs delivered, approved changes, vendor effects, fee allocation.
**Primary interactions:** Request evidence, review weekly agency report, assign actions.
**Required state handling:** Agency claim not verified, missing changes, stale evidence.


### UX-16  System Operations and Audit
**Content / visuals:** Worker queue, action attempts, webhook events, dead letters, backup, release status.
**Primary interactions:** Retry eligible job, request restore test, export incident timeline.
**Required state handling:** Rollback needed, queue exhausted, failed authentication.


# 15A  Deep UI interaction specifications - 8 decision-critical screens
Implement the following as shared frontend contracts. All pages use global seller-account/marketplace/date/SKU filters, a visible data-freshness footer, tooltips explaining metric definitions, and a persistent proposal/action drawer. All keyboard actions require accessible names and visible focus.

### D-UX01 War Room
**Layout and visual hierarchy:** Top ribbon: status of Amazon/Flipkart/warehouse connectors, last full sync, data coverage, approval count and emergency mode. KPI row: net revenue, contribution after ads, TACOS, paid ACOS, units, CVR with 7D/30D compare. Middle: campaign performance + revenue trend with action annotations. Bottom: "What changed / Why it matters / Suggested next action" and task owner columns.
**Action contract:** Primary interaction: clicking any delta opens one source-backed drilldown; each card offers definition, numerator/denominator, date coverage and export.
**Responsive behavior:** Mobile: hero KPI switcher plus 3 urgent tasks; charts stack; actions in sticky bottom sheet.
**Safety, empty and failure states:** No fake trend when report incomplete; source API outage uses last reliable data with exact stale timestamp.

### D-UX02 Competitor Observatory
**Layout and visual hierarchy:** Left: own SKU picker and peer match controls. Center: sortable comparison matrix with offer price, normalized price/100g, grade, image count, ratings, review sample, delivery, available keywords. Right: timeline of peer changes and differentiated tactical action cards.
**Action contract:** One-click compare opens visual side-by-side (own image vs competitor image), then a provenance inspector for every numeric cell; show product similarity/confidence next to each peer.
**Responsive behavior:** Mobile: vertical cards grouped Exact Peers / Near Peers / Excluded; swipe to compare fields with persistent product identifier.
**Safety, empty and failure states:** Unavailable rank/provider data draws hatched placeholder with "not collected" explanation; not zero.

### D-UX03 Keyword Lab
**Layout and visual hierarchy:** Tabbed structure: Seed Discovery, Reverse Product, Own Search Terms, Gap Matrix, Rank History, Keyword Map. Each row: phrase, intent, search demand source, observed clicks/CVR, CPC, difficulty band, exact SKU/pack fit, organic/sponsored rank and recommendation.
**Action contract:** Select multiple terms into "Keyword Basket"; assign title/bullet/backend/ads with policy rules, preview impact, create implementation ticket and schedule rank monitor.
**Responsive behavior:** Mobile: priority chips, expanded row details; no 12-column horizontal overflow for essential actions.
**Safety, empty and failure states:** Unlicensed volume -> unknown; only owned observed impressions/clicks and approved provider estimates shown.

### D-UX04 Ads Studio
**Layout and visual hierarchy:** Four panes: campaign tree, main trend, search-term opportunities and scenario/approval side sheet. User drills Campaign -> Ad Group -> Target/ASIN -> Search Term, with spend/click/attributed sale and risk.
**Action contract:** Bid recommendation always opens preflight financial card with current bid, suggested bid, owner min profit, remaining daily cap, sample evidence, expected uncertainty and reversible diff.
**Responsive behavior:** Mobile: alert/action approval first; complex scenario modelling accessible by open full view.
**Safety, empty and failure states:** Vendor read-only prevents action button; disabled reason says report-only and safe manual steps.

### D-UX05 Listing Quality & Content Editor
**Layout and visual hierarchy:** Dual-column original vs proposed title/bullets/assets; overlay keyword coverage, factual evidence citations, format policy warnings, mobile search-result preview and attribute completeness.
**Action contract:** Reviewer can accept text fragment, reject claim, request product facts, save draft, run policy QA, create controlled experiment or publish after approval.
**Responsive behavior:** Mobile: tabs Original / Proposed / Evidence; sticky "Save draft" and safe review CTA.
**Safety, empty and failure states:** Any unsupported pack/origin/processing/health claim appears blocked; publishing forbidden until resolved.

### D-UX06 Product Profit Workbench
**Layout and visual hierarchy:** Top: fee+COGS source status; product economics waterfall; compare Amazon FBA/Easy Ship/Flipkart, bundle and price scenarios. Show exact fees and assumptions, settlement matching and current SKU cost version.
**Action contract:** Scenario slider changes price, ad CAC, return rate and promotion with immediate net contribution plus max viable CPC; Save scenario to an approved proposal, not price write.
**Responsive behavior:** Mobile: expandable waterfall sections, INR tabular digits and clear negative values with text labels.
**Safety, empty and failure states:** Unknown cost/fee leads to warning and suppressed scale suggestions; never silently zeros missing.

### D-UX07 Decision/Approval Center
**Layout and visual hierarchy:** Risk-sorted inbox with one proposal per item and source evidence, exact vendor change diff, last-check validation, approver chain, expiry/kill status, expected financial bounds and reversal method.
**Action contract:** Approve/reject/request changes; Tier-2 requires distinct confirmations; after click statuses show QUEUED, EXECUTING and VERIFIED/FAILED separately.
**Responsive behavior:** Mobile: full-width evidence cards; bottom fixed approval bar with irreversible action reminder and biometric/MFA step where policy demands.
**Safety, empty and failure states:** Write failure is explicit and alertable, not shown as "success"; role restrictions mandatory.

### D-UX08 Experiment & Learning Center
**Layout and visual hierarchy:** Experiments timeline attached to source SKU, query, baseline, exposure, cost, metric/guardrails, control integrity, notes and actual outcome. Growth hypotheses and learnings shown with confidence and source.
**Action contract:** User can launch/stop, inspect overlap conflicts, attach intervention diff, compare outcome windows, label inconclusive and roll back from stored version.
**Responsive behavior:** Mobile: experiment summary cards with actions and verdict; detailed statistical report via modal/page.
**Safety, empty and failure states:** Too-few samples, multi-change interference or unclear attribution always yield INCONCLUSIVE rather than WIN.

# 16  Agent architecture, learning, compliance and governance

## Nine intelligence roles (agents propose; deterministic services execute)
| Agent | Target scope | Human oversight / guard |
| --- | --- | --- |
| A01 Market | Seasonality, evidence-backed market research, research/source summaries | Do not create unverified price/market-share claims |
| A02 Competitor | Peer matching interpretation, offer/content change synthesis | Only source-backed observations; no fake competitor sales |
| A03 Keyword | Term clusters, gap prioritisation, rank/intent hypotheses | No invented search volume or exact rank |
| A04 Listing | Safe SEO drafts, attribute completion, content tradeoffs | Fact registry and editorial/compliance approval |
| A05 Creative | Briefs, variant hypotheses, QA suggestions | No misleading photo/health claim; person QC |
| A06 Ads | Proposal ranking and tactical scenarios | Profit floor, sample rules, spend caps and approval |
| A07 Pricing | Competing offer analysis and margin-constrained options | No automatic unapproved price-cut |
| A08 Reviews | Clustering and root-cause requests | No fabricated reviews, permitted reviews only |
| A09 Governance | Coordinate jobs, priorities, experiments, learning evaluations | Read-only intelligence; backend policy engine retains authority |

### AIG-01  |  P1  |  Learning store and outcomes measured
- Requirement: Memory must survive restart and reflect verified results rather than confident narratives.
- Implement: Persist input references, action/event IDs, assumptions, experiment results, 7/14/28-day outcomes, confidence update and rollback reasons; distinguish statistical evidence from opinion.
- Acceptance: After restart, identical learned rules and evidence accessible; no learning recorded for unexecuted proposal.

### AIG-02  |  P1  |  Governed LLM runtime and cost caps
- Requirement: Prevent unbounded AI cost and unsafe hallucinated actions.
- Implement: Provider abstraction with budget by role/day/month, cache, prompt/version log, redaction, context citations, model failover, rate limit, fallback to deterministic rules; no secrets passed in prompts.
- Acceptance: When AI unavailable, correct read-only analytics persists; LLM cannot invoke direct marketplace writes.

### POL-01  |  P0  |  FSSAI / marketplace compliance gate
- Requirement: Prevent product facts fabricated from templates.
- Implement: Verified fact registry per SKU; collect FSSAI/licence/label/proof, nutrition/ingredients/allergen and claim evidence; copy drafting defaults to safe omission when unknown.
- Acceptance: Unverified health, origin, nitrogen flush or no-added-sugar claim triggers NEEDS_EVIDENCE; approved facts cite source.

### OPS-01  |  P1  |  Monitor availability, failures and backup
- Requirement: Reliable service and incident response for 24/7 operation.
- Implement: Error dashboard, provider limits, alert routing, job dead letters, DB backups, restore exercises, SLOs, health/readiness; weekly change reports.
- Acceptance: Simulated provider outage alerts within agreed SLA; restore exercise retains actions and audit log.

# 17  Delivery plan | coordinated parallel workstreams
**Execution pattern:** Shared architecture and source-of-truth first. Different engineering teams can work in parallel using agreed contracts; launch gates are sequential. The following are planning estimates, not guarantees.
| Sprint group | Parallel team streams | Integrate / exit checkpoint |
| --- | --- | --- |
| 0: Freeze baseline | Lead: requirements/architecture; DevOps: private infra; QA: snapshot current tests | Commit pinned, backlog assigned, secrets scan & access verified |
| 1: Safety + data | Backend auth/actions; data schema/migrations; frontend live-state refactor | GATE-A and core of GATE-B; no unauthenticated access |
| 2: Read-only ingestion | Amazon connector; Flipkart feasibility/CSV; QA finance reconciliation | Raw-to-canonical imports; replay/idempotency tests pass |
| 3: Profit + Ads | Finance fee engine; Ads Studio; UX data dashboards | Approve only when margins known; consistent period metrics |
| 4: Research + comparison | Keyword adapter and gaps; competitor peer store; listing/creative QA | Source/capture proof; compare demo and real evidence correctly |
| 5: Verified action | Approvals; remote write verifier; scheduler/monitoring; pilot fixtures | Dry-run/approved write to permitted sandbox or small live test |
| 6: Experimental learning | Rank tracker; experiment registry; measured outcomes; UX polishing | Pilot report on net contribution, CVR, rank with caveats |
| 7: Expansion | Agency, inventory/BOM, D2C and additional platforms | Only after stability + cost/access signoff |

## Multi-developer parallel ownership / package boundaries
| Owner / team | API or artifact contract | Does not block initially |
| --- | --- | --- |
| Tech lead | OpenAPI schemas, DB migrations, auth model, flags, CI/branch protection | UI copy and mockups can proceed with fixture schema |
| Data engineer | Raw ingest, canonical mapping, seller/account dimensions, finance views | Keyword research uses sample fixture data until licensed feed |
| Integrations engineer | Amazon/Flipkart capabilities, OAuth, sync and write adapters | Seller account access after read-only implementation |
| Growth/ML engineer | Ads, profit rules, keyword scoring, ranking hypotheses, experiments | No direct platform writes; outputs signed proposals |
| UI/UX team | Design tokens, component library, 16 production screens, responsive QA | Typed stubs with quality-state controls |
| QA/Security | Contract, property, reconciliation, role, action/retry, E2E tests, load+security | Synthetic data environment available from Sprint 0 |
| Business owner/agency | Source data, facts, SKU costs, competitors shortlist, approval rules | May supply in secure portal, not code/chat |

# 18  End-to-end use cases developers must demonstrate

### UC-01  Low selling Cashew W320 200g
**Scenario:** Ingest last 30-day own ads, product, cost, listing and approved peers. Compare STRICT comparable peers and explain CVR/CTR bottleneck. Draft factual keyword+image proposal. Show threshold and approval.
**Mandatory recorded evidence:** Screenshot peer match + own profit sensitivity + keyword data source + draft/QA gate + 14-day monitoring.

### UC-02  California Almond 200g keyword expansion
**Scenario:** Discover relevant grade/pack seed terms, map to own converting search terms, use licensed reverse product data when present, filter wholesale/wrong grade and rank by contribution opportunity.
**Mandatory recorded evidence:** Keyword opportunity grid shows provenance and no fabricated volume in missing-provider state.

### UC-03  Cranberry high spend, poor ROAS
**Scenario:** Compare matched attribution periods, target ACOS and margin; propose conservative bids/campaign restructure with exact diff and test.
**Mandatory recorded evidence:** Remote change verified; report distinguishes report-based prior spend from guaranteed future saving.

### UC-04  Brazil Nuts high-performing SKU
**Scenario:** Compare stable CVR, inventory coverage, profit floor, rising CPC and organic rank before proposing ad scale.
**Mandatory recorded evidence:** Spend cap + COGS check prevents margin-negative expansion; scenario documented.

### UC-05  Competitor price drop alert
**Scenario:** Two dated snapshots prove STRICT peer changed same pack. Compute own possible response options: maintain, coupon, enhanced A+, lower price.
**Mandatory recorded evidence:** No auto price slash; effects shown for best/worst cost and delivery assumptions.

### UC-06  Flipkart unsupported ads API
**Scenario:** Flipkart seller data works read-only; Ads CSV imported and clearly dated. UI does not offer disabled/fictional write action.
**Mandatory recorded evidence:** Capabilities dashboard labels "report-only"; no claim "ads paused" on manual flow.

### UC-07  Two-SKU order and repeat import
**Scenario:** Import one order with Almond and Cashew lines twice.
**Mandatory recorded evidence:** Two line items retained, financial totals invariant, duplicate import detected.

### UC-08  Risky health claim in listing
**Scenario:** LLM drafts "diabetes-friendly" for nuts without supporting product evidence.
**Mandatory recorded evidence:** Compliance workflow blocks publish and cites missing evidence rather than auto rewriting as fact.

### UC-09  Kill-switch during queued bid updates
**Scenario:** Two bid changes pending, kill engaged before execution.
**Mandatory recorded evidence:** No write applies; queue quarantined; owner sees evidence and what is/not remotely paused.

### UC-10  Festival hamper stock and profit
**Scenario:** Propose pack with multiple dry fruits/packaging, demand assumptions and listing creative.
**Mandatory recorded evidence:** Warehouse BOM reserves component quantities; margin includes box, labor and marketplace charges.

# 19  Acceptance matrix | tests, SLOs and rejection reasons
| ID | Test and success condition | Reject release when... |
| --- | --- | --- |
| QA-01 | RBAC authenticated E2E; outsider cannot access seller data or changes | Any public management API or bypass exists |
| QA-02 | Same CSV twice; order lines + campaign IDs correct; metric windows explicit | Numbers change on repeated identical imports |
| QA-03 | Every rendered production table comes from API and has timestamp | Demo products/ROI/strength claims appear in LIVE mode |
| QA-04 | Read-only Amazon and Flipkart account certification with documented scope | Mocks are labelled production-tested |
| QA-05 | Approval tier2 double-check + remote write and re-fetch | UI says executed without vendor verification |
| QA-06 | Kill switch persists restart and suppresses all outbound writes | State is browser-only |
| QA-07 | Min profit and unknown cost blocks ad scale | Margin calculated with cost=0 placeholder |
| QA-08 | Competitor peers have match confidence and source capture | W240 and W320 treated as exact equals |
| QA-09 | Volume/rank values sourced; missing values = unavailable | Clicks*20 presented as Amazon search volume |
| QA-10 | Copy compliance blocks unproven product facts | Nitrogen flushing and health claims generated without evidence |
| QA-11 | Scheduler persists retries and does not duplicate actions | Schedule only a list of clock strings |
| QA-12 | Experiment readout lists baseline, caveats and net profit outcome | Pearson correlation called definitive ranking cause |
| QA-13 | Core workflows usable on 360/768/1440 px, keyboard and screen reader | Major filter or approval inaccessible |
| QA-14 | DB restore exercise, secret scan, vendor outage alerts pass | No recovery plan; lost approvals and actions |

## Quantitative non-functional targets - proposed SLOs, negotiate with team
- Availability target: 99.5% for authenticated read-only dashboard, excluding provider outages. Show last-known data with stale badge during outages.
- UI: p95 War Room initial data under 3 seconds for typical scoped 30-day view on provisioned hardware; heavy tables paginated and async.
- Normal owned-data sync: daily within business-defined reporting cutoff; freshness indicator and 2 consecutive failure alerts; provider lag isolated.
- Action pipeline: 100% actions idempotent by key; 100% audit records; no unapproved financial write actions; verifier records remote ID and final state.
- Data reconciliation: mismatch thresholds decided from actual settlement reports; no silent reconciliation rounding or cross-period TACOS.
- Accessibility: keyboard navigation and WCAG 2.2 AA-like contrast/interaction review at agreed screen sizes.

# 20  Developer work orders and first-iteration backlog
Developer can create one ticket per requirement ID above. Each ticket requires source module(s), schema/API migration, unit/contract/E2E tests, screenshots in dark/light/mobile, migration notes, operational runbook entry and business-owner acceptance evidence.
| Order | Batch of work | Owner sign-off |
| --- | --- | --- |
| W01: Secure | SEC-01, SEC-02, SEC-03, SEC-04, UI-01 | Owner + security QA |
| W02: Trust | DAT-01, DAT-02, FIN-01, POL-01 | Finance + data owner |
| W03: Sync | JOB-01, INT-01, INT-02, INT-04 | Integration QA |
| W04: Marketplace | INT-03, INT-05, FIN-02, INV-01 | Operations + QA |
| W05: Ads | ADS-01 through ADS-06 | Growth lead + owner |
| W06: Keyword/Rank | KWD-01 through KWD-04; RNK-01 through RNK-04 | Research + QA |
| W07: Listings/Creative | LST-01 through LST-05; CVR-01 through CVR-04 | Brand + compliance |
| W08: Competitive | CMP-01 through CMP-04 | Owner + research QA |
| W09: Expansion | INV-02, AGY-01, AIG-01, AIG-02, OPS-01 | Owner + relevant leads |
| W10: UX and regression | UX-01 through UX-16, UC-01 through UC-10, QA-01 through QA-14 | Product owner/QA formal go-no-go |

## Each pull request must contain
1. Linked requirement ID and why this change is needed; no undocumented scope expansion.
2. Description of current behavior, expected new behavior and reversible migration.
3. OpenAPI/JSON schema, database migration, validation and explicit error handling.
4. Unit + integration + E2E coverage, including unknown/stale/provider-down cases.
5. Before/after desktop and mobile screenshots where UI is touched; keyboard accessibility checklist.
6. No leaked secrets, no real customer PII in fixtures, lint/types/static scans green.
7. For marketplace writes: dry-run report, approval proof, remote verifier and rollback outcome.
8. Runbook update, last-synced status, user documentation and owner sign-off before merge to production.

# 20A  API endpoint contracts, persistence constraints and migrations
Use OpenAPI-generated TypeScript client to avoid dashboard/back-end mismatches. All API requests require appropriate session or scoped bearer credential; reads and writes must be partitioned by `seller_account_id`, platform and role. API paths below are illustrative product contracts, not claims of already existing endpoints.
| Method/path | Minimum response or request | Who may access / side effect |
| --- | --- | --- |
| GET /api/v1/warroom | Date range, platform, coverage, computed KPI bundle, source timestamps | Viewer+; no writes |
| GET /api/v1/products/{sku} | Own catalog listing, grade, financial/keyword/evidence summary | Viewer+; scoped by seller |
| GET /api/v1/competitors?sku=... | Strict/near peers, snapshots, match confidence, comparable metrics | Viewer+; respects source-license rights |
| POST /api/v1/competitors/matches | Our product, peer id, match class, reviewer justification | Analyst+, immutable override record |
| GET /api/v1/keywords | Query filters, origin, rank evidence, opportunity metrics, pagination | Viewer+; unknown estimates are null |
| GET /api/v1/campaigns | Campaign/target metrics, attributable dates and cost versions | Viewer+; filters and row-level details |
| POST /api/v1/proposals | Exact proposed change, predicted range, source evidence and policy results | Growth Lead+; DRAFT only |
| POST /api/v1/proposals/{id}/dry-run | Vendor state check, diff, risk and permission verifications | Growth Lead+; no vendor write |
| POST /api/v1/proposals/{id}/approve | Approver identity, tier, approval token and comment | Approved roles only; creates QUEUED state |
| GET /api/v1/actions/{id} | Lifecycle, attempts, remote vendor ID, reconciliation and rollback | Viewer+ per account; immutable history |
| POST /api/v1/control/kill | Owner action with reason and scope; kill ID and remote pause statuses | Owner only; immediate server-side fence |
| GET /api/v1/jobs/status | Last success, next planned run, error/retry, source latency, DLQ | Operations+ scoped |
| POST /api/v1/imports/preview | File metadata, date window, columns, errors and duplicate hash | Analyst+; preview no mutation |
| POST /api/v1/imports/commit | Preview token + authenticated actor; async import receipt | Data Operator+; idempotent import |

## Mandatory API response envelope
Example specification: `{ data: {...}, meta: { request_id, seller_account_id, source_ids[], observed_at, computed_at, freshness_status, coverage_pct, time_zone, currency, data_class }, errors: [] }`. Empty datasets use explicit null/empty values; any estimate carries `methodology_version` and confidence/interval. Errors use machine code and human-readable recovery action.

## Minimum relational constraints for production DB
- `order_headers UNIQUE(platform, seller_account_id, external_order_id)`; `order_items UNIQUE(platform, seller_account_id, external_order_id, line_id)` to support multi-item orders.
- `ad_campaigns UNIQUE(platform, seller_account_id, external_campaign_id)`; aggregated facts unique by campaign/target/date/grain/report_version/attribution_window.
- `ingest_batches UNIQUE(platform, account_id, file_sha256, report_type, period_start, period_end)`; row checksum and immutable original uploaded report.
- `competitor_snapshots UNIQUE(provider_id, competitor_listing_id, capture_id)`; store source URL, permission scope, confidence, comparable_grade and sample geography.
- `listing_versions` include previous_version_id, approved_by, accepted_claim_proofs, vendor_execution_id and effective start/end.
- `action_events` append-only state transitions with actor/remote acknowledgement/idempotency; no deleting audit rows through UI.
- `product_cost_versions` effective-dated; `product_bom` parent/child component quantities, lot availability and packaging costs.
- `keyword_observations` unique by provider/keyword/product/marketplace/geo/device/captured_at/rank_type; preserve estimate ranges.
- Every foreign key includes matching tenant/account context where necessary; indexing supports seller/date/SKU/keyword drill-down at scale.

## Integration fixtures and anti-corruption layer
Maintain curated fixtures for Amazon reporting versions, Flipkart seller CSV variants, duplicate campaign names, unknown fees, refunds after sale, return-to-inventory, multi-item order, null coupons, multiple pack sizes, changing categories and sanctioned inaccessible endpoints. Provider adapter transforms raw requests into canonical DTO; business logic must never assume a provider-specific attribute is universally present.

### API-01  |  P0  |  Typed API contracts and frontend generation
- Requirement: Avoid JS demo state or backend contract drift.
- Implement: Publish OpenAPI spec, generate TypeScript client, define paging, filtering, sorted numeric fields, validation/errors and feature capability switches; same-origin HTTPS.
- Acceptance: Contract test validates all critical endpoints; frontend cannot display live-looking hardcoded fallback records.

### API-02  |  P0  |  Idempotent execution and event outbox
- Requirement: Prevent duplicate campaign mutations and lost events.
- Implement: Action API writes proposal+outbox transactionally, worker claims once, uses idempotency key and executes remote post-check; logs failure/exhaustion and retries within safe limits.
- Acceptance: Concurrent approve requests produce one vendor change; failed/timeout result remains pending verification not blindly retried.

### API-03  |  P1  |  Provider permission capability registry
- Requirement: Platform features must reflect actual granted scopes and APIs.
- Implement: Store `platform_capability`: read_ads, write_ads, list_orders, edit_listing, keyword_provider, rank_provider, last_certified, reason and expiry. UI permissions adapt automatically.
- Acceptance: Flipkart with report-only ads correctly hides automated write, offers CSV/manual workflow and never misleads owner.

# 21  Inputs required from Dry Fruit Farm and access conditions
| Input | Minimum detail | Safe handoff |
| --- | --- | --- |
| Catalog | ASIN/FSN, SKU, category, grade, net weight, variant, listing URLs, verified claims | CSV/export through secure import |
| Costs | Per-pack landed cost, packaging and assembly, fulfilment model, variable expenses | Finance-only cost template |
| Ad history | Campaign, search term, targeting and attributed sales + named date windows | Seller Console exports / authorised API |
| Order/settlement | Item-level orders, refunds, payout reports, invoices and cost schedule | Restricted secure storage; least privilege |
| Competitor shortlist | Top 5-10 comparable seller product URLs per hero SKU | Manually curated seed, not assumed competitor rank |
| Controls | Owner roles, who approves, bid/budget caps, target margin, allowed auto-actions | Governance settings signed by owner |
| Access | SP-API registration, Ads API and Flipkart developer access approvals | Never send secrets over chat or store in GitHub |
| Team | Agency and core team owners, store/warehouse/marketplace responsibilities | Scoped identities and approvals |

## Feature availability and subscription decision policy
Build owned-data features first. For reverse-ASIN, market demand and rank history, compare **build with licensed data feed**, **use provider export/API under terms**, or **mark unavailable**. Explicit procurement decision requires data quality, India marketplace coverage, TOS/licence, cost, refresh cadence and the quality of decision improvement. Do not assume a Helium 10 subscription grants rights to extract or redistribute its data through unofficial means.

# 22  Risk register and audit corrections
| Risk / severity | Cause | Mitigation / accountable owner |
| --- | --- | --- |
| Financial action false-positive / Critical | UI says applied but only DB state changed | Backend remote verification; product/security owner |
| Unauthorised access / Critical | No login, public bind, static dashboard | MFA/RBAC/private ingress; security lead |
| Wrong profitability / Critical | Approx fees, cost defaults, duplicate imports | Settlement reconciliation; finance lead |
| Competitor data unavailable / High | Seller API does not give complete public intelligence | Licensed provider or approved manual evidence; research lead |
| Algorithm overclaim / High | Heuristic rank weights, correlation confusion | Evidence labels, experimental validation; data science lead |
| Policy/copyright/access / High | Unapproved crawling, scraping, copied creative | Permitted sources, licensing, original creatives; legal/product lead |
| Food claim violation / High | Template defaults create nutrition/packaging assertions | Product fact registry and approval; compliance lead |
| Agency conflict / Medium | Agency activities not verified; permissions unclear | Read-only logs, limited scope, auditable task ownership |
| API/version changes / High | Amazon Orders v0, Ads reporting formats change | Version tracking, contract tests, change-alert jobs; integration lead |
| Scope explosion / High | All modules treated as one big bang release | P0 gates, feature flags, phased rollout, sign-off |

# 22A  Production handover, deployment strategy and owner signoff

## Environments and data policy
| Environment | Allowed data and operations | Promotion checkpoint |
| --- | --- | --- |
| LOCAL / DEV | Synthetic fixtures, sandbox permissions, mocked providers; no customer PII or real API secrets in repo | Static checks, unit tests, feature flags and peer reviews |
| STAGING | Sanitised report samples, test credentials, restricted staging account; write adapters in dry-run unless allowed sandbox | Integration, browser, device, security and migration tests |
| PRODUCTION READ-ONLY | Real seller data ingested with least privilege, private access, full dashboard, monitoring | Run for one reporting cycle and reconcile totals |
| PRODUCTION SUPERVISED | Small capped set of campaign changes; Tier-1/Tier-2 controls, vendor-verification and rollback | 14-day controlled pilot, owner verifies action+profit outcomes |
| PRODUCTION SCALE | Expanded feature flags only for certified use cases and accounts | SLO, outcome and risk review; owner explicit go/no-go |

## Handover pack developer must include
1. Source branch/commit, package diagram, running services list, DB schema ERD, migration plan and rollback procedure.
2. All 49+ requirement tickets with linked PRs; testing screenshots/videos for core user flows and 360/768/1440-width responsive screens.
3. Authenticated live War Room, competitor intelligence provenance example, dry-run ad proposal, Tier-2 approval and vendor verification walkthrough.
4. Secure onboarding SOP for Amazon SP-API, Amazon Ads API, Flipkart developer access and optional research provider contract.
5. Data governance: which data is observed, estimated, hypothetical or manually entered; owner access and audit/export ability.
6. Finance settlement reconciliation workbook/test dataset and signed-off contribution margin rules.
7. Runbooks for provider outage, data lag, secret rotation, kill-switch, rollback and database restore, plus monitoring alerts.
8. Pilot report: pre/post contributions, keyword and CVR evidence, lessons, unresolved defects and next improvement backlog.
> **Owner go/no-go requirements** The system is NOT accepted on the basis of a beautiful dashboard or passing mock tests alone. Acceptance requires owner observed demonstration of comparable competitor analysis, valid data acquisition, profit-safe recommendations, human approval, actual verified change execution and measured business outcome.

# 22B  Copy-paste master execution brief for the development team
The developer may copy the following instructions into their issue tracker or AI coding agent. It deliberately avoids promising completion merely because files or tests exist.
> **Developer execution brief - full responsibility** **Repository:** `https://github.com/iamprateeknk-pixel/nutriscale-os` (baseline commit `73f7777...`). **Mission:** Implement all accepted requirements SEC, DAT, JOB, UI, INT, ADS, KWD, LST, CMP, RNK, CVR, FIN, INV, AGY, AIG, POL, OPS, API and UX in this PDF. Treat this as one integrated multi-team delivery, organised under staged release gates. Do not remove existing useful Python engine logic without equivalence tests. Never display demo business numbers as LIVE and never label a proposed action executed without vendor verification.
1. Perform a fresh source audit at the current HEAD, document differences versus this dated baseline, and create milestone-linked tickets for all requirement IDs and acceptance scenarios.
2. Immediately restrict unsafe server access, add auth/role scopes, remove demo approvals and browser-only kill switch, and implement production data-model migrations with invariant tests.
3. Define OpenAPI/DTO contracts first. Develop UI and backend in parallel with shared typed mocks; connect only verified, time-scoped, provenance-aware data sources.
4. Implement official Amazon and Flipkart integrations using currently supported APIs and permissions. Use CSV/manual import capability when a source or ads write API is unavailable. Do not reverse-engineer protected systems or violate provider terms.
5. Deliver listing, keyword, ads and peer-comparison functionality using verified product facts, margin-gated decisions, dated competitor evidence, rank measurement and safe action proposals.
6. Build the 16-screen UI and eight deep workflows with accessibility, responsive layouts, source freshness, finance sensitivity, accurate empty states, action explanation drawers and exportable evidence.
7. Integrate one complete vertical slice: choose Cashew W320 200g, match true competitors, diagnose gaps, draft a listing/ads experiment, get human approval, verify vendor changes and measure outcome.
8. Add full CI with unit, migration, contract, mocked-provider and permitted real-provider tests; screenshots of all important screens; negative tests for kill switch, permissions, fees and failed writes.
9. Create user documentation, runbooks, owner training, incident response, backup/restore drills and a 14-day supervised pilot report. State incomplete/unverified work explicitly in STATUS.md.
10. Only declare production ready after every relevant acceptance gate passes and Dry Fruit Farm owner signs off. Do not invent revenue uplift, ranking improvements, competitor traffic, search volume or marketplace approval.
**Required handback:** (1) GitHub PR list and pinned commit, (2) checked backlog and unresolved issues, (3) data-source permissions matrix, (4) live/empty mobile+desktop screenshots, (5) data reconciliation outputs, (6) example competitor strategic action and observed proof, (7) approved dry-run/write/rollback logs, (8) security and reliability test report, and (9) owner demo checklist.

# 23  Repository evidence and external references
**Audit provenance:** Repo commit `73f7777ae494d17e5e84d2747918fad613d5a5ff` on 22 October 2026; actual code paths and GitHub Actions logs inspected. Attached original V4 audit was used as historic baseline and not treated as final implementation proof. External official and product documentation checked on 22 October 2026.
- [R1] Repository: https://github.com/iamprateeknk-pixel/nutriscale-os
- [R2] GitHub Actions verified CI: https://github.com/iamprateeknk-pixel/nutriscale-os/actions/runs/39745463299
- [R3] Current repo audit and V4 comparison: https://github.com/iamprateeknk-pixel/nutriscale-os/blob/main/STATUS.md
- [S1] Amazon SP-API Orders v2026-01-01: https://developer-docs.amazon.com/sp-api/docs/orders-api
- [S2] Amazon SP-API AWS signing no longer required, official announcement: https://github.com/amzn/selling-partner-api-models/discussions/3701
- [S3] Amazon Ads Sponsored Products search-term report: https://advertising.amazon.com/help/G3HEFZYWZF84NPS9
- [S4] Flipkart Marketplace Seller API docs: https://seller.flipkart.com/api-docs/index.html
- [S5] Flipkart self-access and access-token guide: https://flipkart.github.io/fk-api-platform-docs/docs/intro
- [S6] Helium 10 Cerebro (Plus Magnet) keyword analysis: https://kb.helium10.com/hc/en-us/articles/44519579661211-How-to-Analyze-Keywords-Using-Cerebro-Plus-Magnet
- [S7] Helium 10 keyword suggestions: https://kb.helium10.com/hc/en-us/articles/44553831177883-How-to-Find-Suggestions-for-Additional-Keywords-Using-Cerebro-Plus-Magnet
- [S8] FSSAI labelling amendments, including 2026 amendment: https://www.fssai.gov.in/food-law/regulations/amendments/labelling-display
- [S9] FSSAI Advertising and Claims regulations: https://fssai.gov.in/food-law/regulations/amendments/advertising-claims
- [S10] Amazon Marketing Stream capabilities / applicability: https://advertising.amazon.com/library/guides/amazon-marketing-stream
> **Product owner acceptance rule** Developer completion is not measured by files created, tests green or AI agent counts. A feature is complete only when **owned data is accurate, UI is live, marketplace permissions are valid, user can take the intended action safely, result is verified, and the scenario passes acceptance tests**.
