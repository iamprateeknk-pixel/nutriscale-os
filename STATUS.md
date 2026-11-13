# NutriScale OS — STATUS (the honest log)
_Updated: 13 Nov 2026 (V27 — the whole system is now in English; 31 suites pass)_

## 🌐 V27 — Everything in English (13 Nov 2026)
- Dashboard (all 23 screens, toasts, dialogs, empty states), API messages, agent/engine output, job outputs, CLI
  output, code comments and docstrings, docs (README, runbook, setup guides, OpenAPI, this log, blueprints, audits)
  — all English now.
- Kept on purpose: Hinglish/Hindi **search vocabulary** (badam, kaju, बादाम…) because shoppers really search that
  way, and Hinglish **detection keywords** (e.g. review complaint words, claim-checker patterns) because they
  match real customer and seller text.
- `seed_knowledge` / `seed_playbook` now refresh the text of rules already stored in a database, so a running
  system switches language after its next learning cycle.
- The autopilot now matches playbook findings by stable codes (`HARVEST_PENDING`, `SELF_COMPETITION`) instead of
  message text.
- Removed the two old demo pages (`dashboard/war_room.html`, `dashboard/legacy_v11_index.html`) — unlinked, fake demo numbers, replaced by the real dashboard in V12.
- `docs/SETUP_TEENO.md` → `docs/SETUP_GUIDE.md`. `docs/openapi.yaml` now lists all V23–V26 endpoints.

## 🛡️ V26 — Full-proof hardening: dashboard upload, import safety, stale-data guard, expiry (13 Nov 2026)
(evidence: test_v26_hardening.py — 5 tests incl. real HTTP and attack cases; **31 suites pass**; upload → preview → import → Keyword Lab exercised in a browser)
- **Security hole closed**: the CSV import API used to accept *any* server path (a logged-in user could try to read other files on the server). Now only CSV/TSV uploaded via the dashboard or inside `data/`; `../`, `/etc/passwd` and symlink escapes all return 400. Request limit 32MB, file limit 20MB.
- **Report upload from the dashboard**: choose or drag a file on Integrations → the type is detected (Search Term, Campaign, Orders, Inventory, Brand Analytics, Catalog/BSR) → preview → "Import". If not recognised, the type can be chosen. No terminal needed — the biggest obstacle to real data is gone.
- **No decisions on stale data**: if ads data is older than 21 days the autopilot creates no negative/harvest proposals, and the Today screen shows a red task "upload a fresh report". Every proposal records `data_freshness` (`AGE_UNKNOWN` for undated CLI imports).
- **Proposal expiry**: no decision within 7 days → `EXPIRED` (new state) — a proposal built on old data cannot be approved by mistake, the inbox stays clean, history is kept. The autopilot cleans up on every run.
- **Limitation (honest)**: for CSV uploads the age of search-term data is taken from the import date, not the dates inside the report — a two-month-old report uploaded today counts as "fresh". API sync carries the real report period.

## 🤖 V25 — Growth Autopilot: findings become proposals, the loop is closed (12 Nov 2026)
(evidence: test_v25_autopilot.py — 7 tests; **30 suites pass**; Autopilot → Approval Inbox flow exercised in a browser)
- **Before**: the playbook *showed* gaps but created no proposals — so confidence in the ads rules could never change from real outcomes.
- **Now** (`src/growth_autopilot.py`, daily at **07:45** — after outcomes are measured): wasted-spend terms → negative-exact; winning terms → harvested into Exact; bidding against yourself → negatives in Auto/Broad; SQP "scale up" / "no clicks" queries; ads paused for SKUs with 0 stock — all as **approval-gated proposals** (with `rule_ids` + `campaign`) → approve → measured after 7/14 days → the rule's confidence in the brain goes up or down.
- **Safety**: never changes anything live itself (ONE_TAP + kill switch); the same task at most once per week (idempotent); at most 15 per run, with every type getting room in turn (negatives do not crowd out revenue-growing harvests); no proposals for rules the brain has DISABLED; never negates a term that converted anywhere; stock-out pauses only when the campaign name contains the SKU.
- **Weekly report** — every Sunday at 21:00 IST, `data/reports/weekly-<date>.md` (proposals, outcomes, brain changes, ads structure, events in the next 45 days); API `/api/v1/reports/weekly`. (Previously the scheduler never ran weekly jobs.)
- **Dashboard**: Autopilot panel on the Growth screen (preview + "create proposals"), a **"what & why"** column with rule chips in the Approval Inbox, autopilot tasks on the Today screen.

## 🚀 V24 — New dashboard + new agent playbooks from market research (11 Nov 2026)
(evidence: test_v24_growth.py — 9 tests incl. real HTTP; **29 suites pass**; all 23 screens without JS errors in Chromium, no horizontal scroll on a 390px mobile screen)
- **Dashboard rebuilt** (`dashboard/index.html`): grouped navigation (Today / Grow / Money / Brain / System), a **"Today" home** (urgent tasks first, setup progress, next sale event, brain), light + **dark mode**, mobile drawer, **Ctrl+K** to find a screen, toasts + modals instead of browser `alert/prompt`, "next step" buttons on empty screens, a **rule chip** with every recommendation (click for the rule + source).
- **New screens**: Listing Builder (live character/byte counters, copy buttons, check score), Keyword Plan (pick a nut → title/highlights/backend/negative), SQP Funnel, Growth Playbook, Agent Brain, Knowledge Base. All 16 old screens kept.
- **15 new research rules** (42 total), all with sources: Amazon ads structure (Auto = discovery, Exact = earning, the harvest cycle, weekly negatives), the **break-even ACOS** formula, TACOS at launch, Vine + review policy, A+ content, Great Indian Festival preparation (FBA 15-20 days ahead, coupons/deals ~7 days ahead), India dry-fruit market size, **quick commerce** (Blinkit/Zepto/Instamart), Flipkart PLA.
- **Growth Playbook engine** (`src/growth_playbook.py`) — rules applied to your data: SKU break-even/target ACOS, campaign structure score (self-competition, harvest pending, wasted spend), sale calendar countdown (dates are ESTIMATES — stated clearly), a policy-safe review plan, and the home screen's `today()`.
- **Fixes**: (1) the manual `run_cycle` now runs the same real learning cycle + backup + Brand Analytics import as the 24×7 scheduler; (2) default bullets contained unproven claims ("nitrogen flush", "FSSAI licensed", "return/replacement policy") — removed; (3) the Listing Builder now also checks the fact registry (NS-P-01) — an unproven claim is BLOCKED up front, not only at approval.
- **Honesty**: Amazon.in refused the search page even to the Box browser (bot protection) — so no real data on top listings was collected, only research rules. No trustworthy public source for brand-level market share was found. Sale dates are estimates.

## 🧠 V23 — Listing/keyword knowledge for the agents + self-learning (11 Nov 2026)
(evidence: test_v23_brain.py — 9 tests incl. real HTTP; **28 suites pass**)
- **Marketplace Knowledge Base** (`src/marketplace_knowledge.py`): 26 rules from web research (11 Nov 2026), **each with source URLs + a status** (OFFICIAL / MULTI_SOURCE / SINGLE_SOURCE / HEURISTIC) + confidence. Highlights:
  - Amazon **titles are now 75 characters** (from 27 Jul 2026, every category except media) — Amazon's AI rewrites longer titles; new **Item Highlights** field, 125 characters
  - No word more than twice in a title (plurals count); `! $ ? _ { } ^` banned
  - Amazon.in backend **200 BYTES** (a Hindi character = 3 bytes), spaces, no repeating title words, competitor brands/ASINs banned
  - Emojis, ™ ®, refund/guarantee promises and websites banned in bullets
  - Main image pure white 255, ~85% filled, 1000px+ (2000 for zoom)
  - How to read the SQP funnel (not visible / no clicks / no sales / scale up)
  - FSSAI 2018: disease claims banned; natural/fresh/pure/traditional/authentic are conditional words
  - Dry-fruit vocabulary: 8 nuts, Hinglish + Hindi + grades (W240, Mamra…) — **search volume deliberately absent** (only from SQP/licensed sources)
- **Listing Rules Engine** (`src/listing_rules.py`): audits title/highlights/bullets/backend/images/FSSAI (BLOCK/WARN/TIP + rule_id), and builders that produce a title (≤75), highlights (≤125) and backend (≤200 bytes, no repeats, only words for that grade/weight) within the rules.
- **Keyword Intelligence** (`src/keyword_intel.py`): Ads search terms + Brand Analytics SQP + vocabulary in one list, each term with an evidence label; a **placement plan** (TITLE / HIGHLIGHTS / BACKEND / NEGATIVE).
- **Agent Brain** (`src/agent_brain.py`) — real self-learning:
  - Research rules in `playbook_rules`; confidence changes **only from VERIFIED outcomes**, the Bayesian way; 3 losses in a row = DISABLED (only a human can re-enable)
  - Lessons from your own data: which terms sell (OWN-KW-WINNERS), which burn money (OWN-KW-WASTE), SQP problems — updated daily, no duplicates
  - The daily `learning_crawl` job is no longer a placeholder — it runs the real learning cycle; the playbook updates right after `measure_results`
  - The ListingAgent's new `build_listing()` puts proposals into `action_v12` **with rule_ids** — the 7/14-day outcome directly changes confidence in those rules
- **API**: GET `/api/v1/knowledge`, `/api/v1/brain`, `/api/v1/keywords/plan?nut=`, `/api/v1/keywords/sqp`; POST `/api/v1/listings/audit`, `/api/v1/listings/build`
- **Bug fixes**: (1) `claim_checker` caught "cure" but not "cures/cured/heals/prevents" — now it does; (2) the old `generate_title` produced 200-character titles with "Fresh" — now within 75; (3) hardcoded dates in `test_v14` had gone stale (the velocity window is anchored to today) — dates are now relative; (4) the backup job created `backups/` in the repo for in-memory DBs — now it SKIPs.
- **Honesty**: Amazon/Flipkart do not publish ranking formulas — the rules are directions, not the formula. Most rules come from seller guides (Seller Central help is behind a login and could not be opened from this session) — so every rule states its status, and rules older than 90 days show as `stale`. Real sales/search data is not on Google — it only comes from your Seller Central (SQP/Ads reports).

## 🔧 V21 — Ninth audit: 5 calculation/data issues closed (23 Oct 2026)
(evidence: test_v21_v22_fixes.py + older suites updated to the new basis; 27 suites pass)
- **P0 Refund overwrite**: `record_refunds` now uses an **event ledger** (`refund_events`, scope = platform+seller_account+order+line) — several partial refunds on one line **add up** instead of erasing each other; the same event arriving twice is not double-counted. Pro-rata splitting now uses the cumulative total.
- **P0 Velocity denominator**: main velocity = units / **the full 30-day reporting window**; the span-based figure is a separate `run_rate_per_day` (informational) + `observed_sale_days` in the report. Cover is now based on this conservative figure.
- **P1 Stricter VERIFIED**: a SKU outcome is VERIFIED only with **≥8 order lines** in total and **≥max(2, 25% of the window) order days** in each window; otherwise LOW_COVERAGE (outcome recorded, no learning). Small samples are no longer called "verified".
- **P1 Event-ID stability**: financial event ids are now **independent of the response order** (fixed sort first, then counting within identical groups) — reordered responses keep the same ids, and adding a new event keeps old ids stable; regression tests for reordering/partial responses exist.
- **P1 Availability honesty**: Product 360 now shows **VERIFIED sellable** stock and **UNKNOWN availability** separately (without recorded sellable_qty the stock is "unknown", never silently counted as verified); every location has an availability tag.

## 🔌 V22 — Marketplace data automation (code side) (23 Oct 2026)
- **Scheduled Brand Analytics import**: daily 06:45 job `brand_analytics_import` — SQP/SCP files in `data/brand_analytics_inbox/` are imported automatically (SHA dedup). Only the Seller Central export remains manual.
- **Catalog ASIN/BSR snapshots**: `catalog_snapshots.py` + a wizard kind — dated snapshots, BSR trend (first vs last snapshot) in a summary.
- **Seller acceptance report**: `scripts/acceptance_report.py` — the first report from the real DB: `docs/ACCEPTANCE_2026-10-22.md` (legacy revenue ₹46,069 / 104 orders; the canonical 30-day window is still empty — that is the truth until live sync fills it).
- **First real backup created** ✔: `data/backups/growth_os-2026-10-22.db` (41 tables, restore-tested) — preflight `backup_exists` is now ✔.
- **What code CANNOT do (honestly)**: reaching 100% on all three parameters (core dev / workflows / production) needs the live world — SP-API/Ads/Flipkart live authorization, real 7/14-day pilot evidence, deployment on HTTPS hosting, a private repo (GitHub settings). Code-side development is **complete**; only live confirmation remains, which no code can provide without credentials/hosting/owner steps.

## 🔧 V20 — Eighth audit: all code issues closed (23 Oct 2026)
(evidence: test_v20_audit8.py — 9 tests incl. real HTTP; 26 suites pass)
- **P0 Stale velocity**: the window is now anchored to **today (the reporting date)** — sales from 60 days ago can no longer create "fresh" velocity; `sku_velocity_report` adds last-sale date, days since, and a **STALE warning**; included in Product 360.
- **P0 Finance seller-account key**: the `order_fees` PK is now (platform, **seller_account**, order, sku) — a data-safe rebuild migration for old DBs (into the 'default' account); matching and completeness also use the account-level key.
- **P1 Fee events**: every financial event is recorded separately (`order_fee_events`, event-id/content-hash identity, no double counting); `order_fees` is now the **sum** of events — several shipment events for the same order+SKU no longer overwrite each other. The SP connector returns per-event rows (SHIPMENT/REFUND now separate).
- **P1 Stock channel mapping**: an **explicit `stock_channel_map`** instead of name guessing (API: GET/POST `/api/v1/stock/channel-map`); the heuristic is only a fallback, and the basis (EXPLICIT/HEURISTIC/UNCLASSIFIED) is shown for each location. Inventory has separate **sellable/unsellable** — channel cover only uses sellable stock.
- **P1 Honest attribution**: outcomes are recorded with attribution — **VERIFIED / CONTAMINATED / LOW_COVERAGE**; when another channel/action collides (same SKU/campaign, overlapping window) the outcome is attributed to no one; **rule confidence comes only from VERIFIED outcomes**. SKU measurement is limited to the action's own platform.
- **Brand Analytics importer** (`src/brand_analytics.py`): dedicated import of SQP + SCP reports (SHA dedup, `brand_analytics` kind in the wizard), summary API `/api/v1/brand-analytics` — including brand purchase share. **No live report imported yet** — it works as soon as a file arrives from Seller Central.
- **Remaining (not doable in code)**: SP-API/Ads/Flipkart live sync + write pilot + real fees/settlement evidence = needs credentials; 24×7 deployment = a hosting decision; private repo = an owner step in GitHub settings. Preflight run on the real DB — owner/kill switch/HTTPS pack ✔, connectors/capabilities/backup ✘ (that is the truth).

## 🔧 V19 — Seventh audit: remaining bugs closed (23 Oct 2026)
(evidence: test_v19_finance_stock.py, 25 suites pass)
- **P0 False velocity**: no more dividing all-time units by 30 days — now only **trailing 30-day** sales, cancelled excluded. The old bug made cover look lower and velocity higher.
- **P0 The finance matching basis was backwards**: no more NET vs GROSS comparisons — **gross-to-gross and refund-to-refund** are checked separately; order_fees has a refund column + refunds from Finances recorded per SKU.
- **Seller-account isolation**: all order joins now use the (platform, seller_account, order) triple key — identical order ids from two accounts never merge; order counts are per account too.
- **Product 360 channel stock**: stock is now per channel (identified by location name: Amazon FBA / Flipkart Warehouse / unclassified separately); a channel view shows only that channel's sellable stock and cover.
- **One capability name**: the registry's `edit_listing` is now `write_listings` — the same name the publish gate checks (before, certifying was impossible because the registry lacked that key); auto-migration for old DBs.
- **Settlement comparison declared NON-FINAL**: the full amount of an overlapping settlement is not treated as the window's — a day-pro-rata estimate is shown separately; the final match needs transaction-level data (stated clearly in the report).

## ✅ V18 — Sixth audit: data-correctness closure (23 Oct 2026)
The audit's three remaining "partial" items fully closed + one more hidden counting bug (evidence: test_v18_closure.py, 24 suites pass):
- **The cancelled-order count was also wrong** — revenue excluded them, but the "orders" count still included cancelled ones (the dashboard order count looked too high). Now `orders` is a clean count and `cancelled_orders` is shown separately.
- **Finance-grade settlement matching** — beyond matching totals: every order is checked separately (canonical NET vs Finances gross/fees) — MATCHED / FEE_DATA_MISSING / AMOUNT_MISMATCH classes + an exceptions list. Settlements have no order key, so order-level matching uses Finances — this limitation is stated in the report.
- **Reporting completeness** — every reconciliation includes completeness: ads coverage %, fee coverage %, order-day presence in the window. Half the data is no longer silently called "complete".
- **Exact refund line id** — when the vendor gives a line id the refund goes straight to that line; proportional splitting is only a fallback.
- **Channel-specific stock math** — velocity is per platform; Product 360's channel view computes cover from that channel's velocity.
- The TACOS spend basis is now labelled in the KPIs (period-tagged search terms).

## 🐛 V17 — Fifth audit: verified core bugs (22 Oct 2026)
This time the audit found real bugs in my own V15/V16 work — all verified and fixed (evidence: test_v17_audit5.py incl. a **real HTTP regression test**, 23 suites pass):
| Bug | Fix |
|---|---|
| **SKU 360 API crashed over real HTTP** (undefined `u.query` — my V15 code) | Correct `_q.get('platform')`; the backend is now started for real and login→360 (with and without platform) is verified as 200 |
| Campaign-map sync crushed real campaign metrics with ₹0 | The mapping is now only ID↔name; a campaign row is created only when none exists, metrics are untouched |
| TACOS "false MATCHED" — rows existing was enough | Now **day-count coverage ≥80%** (30-day window) + channel scope (non-Amazon sales + Amazon-only ads = NOT_COMPARABLE with a reason) + at least 5 sales lines |
| Preflight looked at a different DB (nutriscale.db) than the backend (growth_os.db) | **One path**: `db_store.DEFAULT_PATH`, and the `NUTRISCALE_DB` env var is now honoured system-wide (backend/jobs/preflight) |
| Reconciliation was unscoped | Scoped to platform + a 30-day window: the window's NET orders vs overlapping settlements; older settlements excluded |
| A refund was applied in full to every line of an order+SKU | **Line-level proportional split** (by gross share, remainder on the largest line) |
| There was no scheduled backup job | **23:30 backup_restore job** (data/backups/, restore-tested); preflight checks the same place |

## 🚪 V16 — Acceptance Gates Kit (22 Oct 2026)
Turned the audit's 5 live gates from "advice" into "runnable tools" — one command once keys arrive:
- **`src/pilot.py` + `scripts/preflight.py`** — a preflight report: each connector's readiness, capability status, Owner account, kill switch, backup, HTTPS pack — anything missing shows a clear ✘, never a false "ready"
- **Reconciliation report** — orders ↔ settlements ↔ ads matched in one place (gaps shown as EXCEPTION, never hidden)
- **Controlled drill** — gate #3 complete: proposal → Owner approval → queue → adapter execute (vendor refetch confirmation) → rollback (previous-state confirmation), evidence for every step. Three locks: kill switch ON = BLOCKED; live=False = plan only; write_ads not certified = BLOCKED. In tests the full drill PASSES with a fake vendor and the campaign is verified back in its previous state.
- **22 test suites ALL PASS**.

## 🎯 V15 — Fourth audit: data-accuracy issues (22 Oct 2026)
| Issue | Fix |
|---|---|
| War Room TACOS was built from lifetime unmatched totals | **Matched-period enforcement**: TACOS only from the last 30 days of dated NET sales vs period-tagged ad spend in the same window; with insufficient data `tacos_pct = null, status = NOT_COMPARABLE` — no fake ratio on screen |
| Outcome measurement relied on campaign names, while actions carry campaign_id | **campaign_map** (ID→name map from Ads sync, also in the daily sync); outcomes now resolve IDs to names reliably |
| Success could be declared on thin dated data | **Coverage gates**: the campaign path needs periods covering ≥70% of the window's days on both sides; the SKU path needs ≥4 order lines in total — otherwise INSUFFICIENT_DATA |
| Canonical orders used INSERT OR IGNORE — status/refunds never updated | **UPSERT** on all three paths (SP API, Flipkart, CSV); refunds from Finances into `order_items.refund`; **revenue is now NET** and **cancelled orders are excluded from counts** |
| Overlaps of periods sharing a boundary day were missed | Periods now use **inclusive date math** — even a one-day overlap is BLOCKED; adjacent but distinct days are fine |
| Product 360 mixed channels | `?platform=` gives a single-channel view; without a platform, **sales_by_platform** separately + a channel list |
| Remaining (outside code) | A licensed competitor/rank provider, live seller-account verification, reconciliation against real reports, a controlled pilot — all live-world steps (list below) |

## 🎯 V14 — Third audit: correctness gaps (22 Oct 2026)
The audit went deeper this time — and was right again. Fixes (evidence: test_v14_audit3.py, 20 suites pass):
| Issue | Fix |
|---|---|
| Outcomes were measured from cumulative totals, not real 7/14-day windows | **Windowed measurement**: w days before applying vs w days after — period-tagged terms for campaigns, dated canonical orders for SKUs; without data no fake outcome, `INSUFFICIENT_DATA` |
| Overlapping Ads periods could be double-counted | **Period Overlap Engine** (connectors/periods.py): contained = skip, supersede = replace, partial = BLOCK with a reason; the daily sync now uses a one-day window |
| Production HTTPS bypass (base compose exposed 8765 publicly) | Base compose now binds `127.0.0.1:8765` — outside access only via Caddy/HTTPS |
| No backend endpoint for listing publish | `POST /api/v1/listings/publish` (execute permission) + Preview check/Live buttons on the dashboard |
| SKU fees were not in the scheduled sync | data_sync now also fetches **order fees** with SP orders; the Flipkart branch joined the scheduled sync too |
| One SKU could be mixed across both marketplaces | Products/campaigns are now identified by **(sku, platform)** — migration without data loss |
| Days-of-cover velocity looked too high (counting only sale days) | The denominator is now the full observation window (first → last sale) |
| The basis of War Room organic/TACOS was hidden | KPIs now carry `organic_basis`/`tacos_basis` in plain words — organic is an ESTIMATE, and the screen says so |

## 🏁 V13 — Everything left on the code side, done (22 Oct 2026)
| Remaining work | Solution |
|---|---|
| Self-learning was half done (actions applied, outcomes never measured) | **Outcome Engine**: baseline snapshot at execution; real re-measurement after 7/14 days; success from win + guardrail; real win rate per kind (rule confidence) — learning now comes from real sales |
| SKU-level exact fees were missing | Per-order fees from the **SP Finances API** → `order_fees`; the most precise `SKU_EXACT` class ranks first in contribution |
| Automatic listing publishing was pending | **Listings Items API** path: APPROVED versions only; VALIDATION_PREVIEW check first; live only with `write_listings=certified`; Amazon's issues recorded as returned |
| No SKU 360° drilldown | A **360° panel** on the Products screen (sales, profit + fee precision, stock cover, listing versions) + a War Room **platform filter** |
| HTTPS/protected deployment | `docker-compose.prod.yml` + Caddy (auto-HTTPS + security headers) — ready once a domain/host exists |
| Security/load evidence | Injection checks, vendor execute blocked by the kill switch, a 2000-order performance smoke test — `test_v13_hundred.py` |

**Code side: 19/19 suites, nothing pending.** Further progress no longer comes from code — it is live-world work:
live certification (your API keys), Ads/Listings pilot sign-off (certified gates), licensed rank data (contract),
a private repo (GitHub settings), hosting + a 14-day pilot, and the hero SKU cost sheet.

## 🔧 V12.2 — Second audit: 6 real source-mismatch fixes (22 Oct 2026)
| Issue | Fix |
|---|---|
| War Room revenue mismatch (new sync is canonical, the war room read legacy) | `analytics.py` — canonical-first unified totals; the war room now reads from there, with a source label |
| Dashboard revenue field bug (`k.revenue` vs `total_sales`) | KPIs now carry revenue + total_sales + orders; mapping fixed |
| Dashboard missing in Docker | `COPY dashboard/` in the Dockerfile — the container serves the dashboard too (smoke-verified) |
| Ads sync duplication | batch/period columns on search_terms; (term+campaign) aggregation within a file; per-period delete-then-insert — re-sync/re-import never doubles totals |
| Incomplete FBA coverage (a "<50 units" guess) | Real **days of cover** from canonical sales velocity; a warning with the SKU name under 21 days |
| Fee accuracy (platform average) | Coverage-weighted precision: ≥80% settlement coverage = REALIZED/HIGH, 30–80% BLENDED/MEDIUM, below ESTIMATE/LOW — every number has a `fee_precision` label |
| Security (audit §5.2) | Login **rate limit** (5 failures = 10-minute lock) + MFA enrolment endpoint `/api/v1/auth/mfa/enable`; HTTPS deployment responsibility (RUNBOOK: reverse proxy) |
Evidence: `tests/test_v12_2_fixes.py` — **18 suites ALL PASS**.

## 🔧 V12.1 — Response to an external audit (22 Oct 2026)
Most points of an external review turned out to be right — everything fixable in code was fixed (17 suites pass, evidence test_v12_hardening.py):

| Audit point | Fix |
|---|---|
| The repo is PUBLIC (our "private" note was wrong — verified signed out) | Making it private is the owner's GitHub settings step (1 min); no secrets/raw PII ever entered the repo (scan ✔); the wrong README line was corrected |
| sync_service was legacy; Flipkart sync incomplete | V2: canonical SP orders+items, Ads terms sync CLI, Flipkart orders+listings, wizard-based CSV |
| The daemon ran every job through one daily_cycle | Dedicated handlers in `job_handlers.py` + a compose `worker` service; data_sync without connectors is an honest SKIP |
| No vendor confirmation in the ManualAdapter | `AmazonAdsWriteAdapter`: real write + refetch confirmation + rollback; does not run without `write_ads=certified` |
| Fee assumptions | Realized fee rates from settlements in contribution/bids; estimates carry a `fee_source` label |
| Dashboard :8765/CORS/token | Same-origin serving, XSS escaping, rank chart + spend bars, **TOTP MFA** |
| Helium10 data / live certification / pilot | Beyond code: a licensed contract + API keys + hosting (table below) |

## 🚀 V12 — Full development per the Master Blueprint (22 Oct 2026)
Every requirement ID in the **V12 Blueprint + Developer Backlog** (docs/V12_BACKLOG.md) was worked on.
**16 test suites, all passing** (the old 11 + 5 new V12 suites: p0, integrations, growth, uc, qa).

| ID | What was built | Evidence |
|---|---|---|
| SEC-01 | Login + RBAC (6 roles), every API closed without a token | test_v12_p0 + HTTP checks (401/200) |
| SEC-02 | Server-side kill switch persisted in the DB — remembered across restarts | kill test + QA-06 (file-DB restart) |
| SEC-03 | Approval state machine (9 states), 2 different Owners for Tier-2, idempotency keys, full event audit | test_v12_p0, UC-09 |
| SEC-04 | Keys only in env/file; a repo-wide secret scan script, CI-ready | scripts/secret_scan.py (passes in QA-14) |
| DAT-01 | Canonical schema: order_headers/order_items (line-level), settlements, batch SHA-256, duplicate imports blocked | UC-07, wizard test |
| DAT-02 | Matched-period gating — if windows do not match, TACOS = NOT_COMPARABLE | test_v12_p0 metrics |
| JOB-01 | Durable job runner: IST next_run in the DB, lock, retry/backoff, dead-letter record, daemon mode | QA-11 |
| UI-01 | New dashboard: no demo numbers; an empty DB = an honest empty state | QA-03 |
| INT-01 | SP-API LWA-only (no more AWS key requirement), orders pagination | test_v12_integrations |
| INT-02 | Full Ads Reporting v3 pipeline: create → poll → gzip download → DB import + batch record | mock-transport test |
| INT-03/05, API-03 | Capability registry: Flipkart ads = report-only, write = unavailable (never a fictional button); the intel adapter is UNAVAILABLE without a licence | UC-06 |
| INT-04 | CSV wizard: preview (hash/kind/rows) → commit, duplicates blocked, receipt | wizard test |
| ADS-01..06 | Ads Studio: health, **profit-led bids** (target ACOS from SKU margin, max CPC, 20% daily cap), harvest/negative safety, pacing, 3 budget scenarios | test_v12_growth, UC-03/04 |
| KWD-01..04 | **The fake clicks×20 volume removed**; taxonomy (badam↔almond), opportunity matrix (volume = null/UNAVAILABLE), rank alerts need ≥3 points | UC-02 |
| RNK-01..04 | Rank observations with scope (locale/device/source), the funnel's foundation, linked to experiment verdicts | keyword_lab |
| CMP-01..04 + CP-01..05 | Peer matching (grade/pack/processing; **W240≠W320**), ₹/100g, dated snapshots + change feed, decision packets (evidence → gap → hypothesis → margin guardrail → experiment) | UC-01/05 |
| LST-01..05 | Listing Score **v2** (versioned, "not Amazon's formula" stated clearly), content gap audit, listing versions + approval gate + rollback | UC-08 |
| CVR-01..04 | Creative brief endpoint, experiment registry (no win without a minimum sample), season/BOM lab | UC-10 |
| FIN-01/02 | Versioned costs; **unknown/stale cost = scaling blocked**; settlement import + reconciliation (MATCHED/EXCEPTION) | QA-07-type tests |
| INV-01/02 | Stock-to-ads gate (STOCKOUT = scaling blocked), hamper BOM feasibility | UC-04/10 |
| AGY-01 | Agency scorecard — no task DONE without evidence, fees + verified changes | growth test |
| AIG-01/02 | Learning store (no learning from unapplied actions), LLM budget governor (daily/monthly caps, prompt-hash-only logging) | growth test |
| POL-01 | Verified fact registry — no claim in copy without evidence (NEEDS_EVIDENCE) | UC-08 |
| OPS-01 | System health (jobs/kill/capabilities/alerts), backup + restore test | QA-14 |
| API-01/02 | OpenAPI spec (docs/openapi.yaml), envelope {data, meta, errors}, idempotent proposals/execution | backend HTTP test |
| UX-01..16 | All **16 dashboard screens** API-backed, with login, evidence badges, a live kill switch | QA-13 + JS syntax + all endpoints 200 |

### What is beyond code even in V12 (no false claims)
| Item | The real reason |
|---|---|
| Live API certification (real QA-04) | Only once your SP-API/Ads keys are in — code + mock pipeline are ready |
| Real vendor write + verification (GATE-D) | The ManualAdapter asks for proof (a ref); the live write adapter comes after the owner's pilot sign-off |
| Licensed keyword/rank data (Helium10 etc.) | Buying a contract is your decision — until then volume/rank show as "unknown" |
| A big migration such as PostgreSQL/Next.js | It is the blueprint's "suggested" topology; the current stdlib + SQLite does the real work — migrate when load demands it |
| GATE-F pilot (2 weeks of real footprint) | Only countable once the system runs on a 24×7 host — hosting is your decision |

---

# Older record (up to V11)

## Built (with code + tests)
| Part | Status |
|---|---|
| Engines (profit/listing/ads/keyword/competitor/flywheel/FBA/claim check) | ✅ 20+ modules, tested |
| Agent layer — **all 9 agents doing real work**: A01 Market (season calendar), A02 Competitor (catching price attacks), A03 Keyword (bank + HERO selection), A04 Listing (title/bullet generation), A05 Creative (7-shot brief + video script), A06 Ads (proposals from the DB), A07 Pricing (margin checks + price proposals), A08 Review (complaint mining), A09 Governance (daily cycle) | ✅ V9 |
| Run tools: `src/run_cycle.py` (one-command daily report), `run_tests.py`, Dockerfile | ✅ V9 |
| Flow designs F1–F10 + scheduler (9 daily + 2 weekly jobs) | ✅ |
| Self-learning (knowledge store, outcome learner, A/B engine, source registry) | ✅ design + core tested |
| Algorithm intelligence (Amazon/Flipkart rank models, Buy Box, change impact, Rank Probe) | ✅ |
| Connectors: Amazon SP-API (SigV4), Ads API, Flipkart, Unicommerce, CSV import | ✅ code + mock tests; **live test once data/keys arrive** |
| Database (SQLite: knowledge/actions/rank/products/orders/campaigns/search_terms/inventory) | ✅ |
| Backend API (health, warroom, connector status, approvals from the DB, cycle run) | ✅ |
| Dashboard (11 sections, controls, kill switch, live-data loader) | ✅ |
| Control Center + Approval Engine (Tier 0/1/2 + guardrails) | ✅ |

## Data is LIVE — Phase-0 audit done (21 Oct 2026) 🟢
| Item | Status |
|---|---|
| The user's 3 reports imported (224 campaign rows, 253 search-term rows, 104 orders) | ✅ Brand: **Dry Fruit Farm** (Amazon) |
| **Phase-0 audit** `docs/PHASE0_AUDIT_2026-10-21.md` | ✅ TACOS ≈61%, ROAS 1.48, 14/23 campaigns with zero sales, 87% of sales from Brazil Nuts + Cranberry, CVR only 3.6% |
| CI workflow file (added by the user via the web) | ✅ verified on GitHub |
| Real proposals from the Ads agent | ✅ 15 bid-down proposals (awaiting approval) |
| **Action Planner (V10)** — pause/scale/watch/negative lists from real data | ✅ `docs/ACTION_PLAN_2026-10-21.md`: 16 concrete tasks, ₹3,808/cycle saved by pausing; improvement packs for both hero listings (score 35→65) |
| 2 real importer bugs fixed (order-id column, campaign aggregation) + the Keyword agent's term-aggregation fix | ✅ caught by real data |

## Still pending (waiting on what)
| Work | Blocked on |
|---|---|
| Margin/break-even math | User: **hero SKU cost sheet** (Brazil Nuts + Cranberry first) |
| Cashew/almond listing review (ads running, sales ~0) | User: their **listing links** |
| Flipkart status | User: Flipkart data |
| Auto-sync (daily data without sending files) | User: API keys (config/connectors.json) — the CSV route works now |
| FBA status + agency fee details | User |
| LLM agent brain (copy/strategy from an LLM) | An LLM API key (env: GOS_LLM_API_KEY) — the interface is ready, it plugs in once the key arrives |
| Real fee tables (Amazon/Flipkart by category) | From live Seller Central/Hub |
| Deployment (24×7 on a server) | Server/hosting decision (after Phase 2) |
| Quick commerce (Blinkit/Zepto), D2C, AI creative generation, ML forecasting | Phase 3 |

## 🏁 Development complete (code side) — V11, 21 Oct 2026
Everything that could be built without the user's inputs **is built**: 20+ engines, 9 real agents, the Action
Planner, the Season Planner (Diwali combos), real LLM call code (live as soon as a key is added, with the claim
check), real connectors + CSV import, backend (warroom/approvals/action-plan/season-pack/cycle), dashboard,
Docker + compose, CI.
**44 tests, 11 suites, all passing — and the system is already running on real business data.**
Every further step was blocked on some input (table above), not on code.

## Rules
- Whatever is not built stays listed here as "pending" — the README or dashboard never falsely say "done".
- Tests must pass with every commit (CI is in place).
