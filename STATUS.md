# NutriScale OS — STATUS (sach ki diary)
_Updated: 23 Oct 2026 (V18 — data-correctness closure)_

## ✅ V18 — Chhathe audit ki data-correctness closure (23 Oct 2026)
Audit ke bache hue teen "partial" mudde poori tarah band + ginati ki ek aur chhupi galti (saboot: test_v18_closure.py, kul 24 suites pass):
- **Cancelled-order ginati bhi galat thi** — revenue to bahar tha, par "orders" ki sankhya cancelled ko ginti thi (dashboard ka order count bada dikhta tha). Ab `orders` saaf ginati, `cancelled_orders` alag se dikhega.
- **Finance-grade settlement matching** — totals ke milaan se aage: har order alag parkha jayega (canonical NET banam Finances gross/fees) — MATCHED / FEE_DATA_MISSING / AMOUNT_MISMATCH shreniyon + exceptions suchi ke saath. Settlements me order-key hota hi nahi, isiliye order-stariya milaan Finances se — ye seema report me saaf likhi hai.
- **Reporting completeness** — har reconciliation ke saath sampurnata: khidki me ads-coverage %, fee-coverage %, order-days ki maujudgi. Aadha data ab chup chaap "poora" nahi kahlayega.
- **Refund exact line-id** — vendor ne line-id diya to refund seedha usi line par; anupaat-baant sirf fallback.
- **Channel-specific stock hisaab** — velocity ab platform-wise; Product 360 ke channel view me usi channel ki raftaar se cover banta hai.
- TACOS kharch ka aadhaar bhi ab KPIs me label sahit hai (period-tagged search-terms).

## 🐛 V17 — Paanchve audit ke verified core bugs (22 Oct 2026)
Is baar audit ne mere hi V15/V16 ke kaam me asli bugs pakde — sab verify karke fix (saboot: test_v17_audit5.py incl. **asal HTTP regression test**, kul 23 suites pass):
| Bug | Fix |
|---|---|
| **SKU 360 API asal HTTP par crash** (undefined `u.query` — mera V15 code) | Sahi `_q.get('platform')`; ab backend ko asal chalakar login→360 (platform ke saath aur bina) 200 verify hota hai |
| campaign-map sync asal campaign metrics ko ₹0 se kuchal deta tha | Mapping ab sirf ID↔naam; campaign row sirf tab banti hai jab ho hi na, metrics ko haath nahi lagta |
| TACOS "false MATCHED" — rows hona hi kaafi tha | Ab **din-ginti coverage ≥80%** (30-din khidki) + channel-scope (gair-Amazon bikri + sirf-Amazon ads = NOT_COMPARABLE wajah sahit) + kam-se-kam 5 bikri-lines |
| Preflight alag DB (nutriscale.db) dekhta tha, backend growth_os.db | **Ek hi raasta**: `db_store.DEFAULT_PATH`, aur `NUTRISCALE_DB` env ab poore system (backend/jobs/preflight) me sammanit |
| Reconciliation unscoped thi | Platform + 30-din khidki scoped: khidki ke orders NET banam takraane wale settlements; purane settlements bahar |
| Refund ek order+SKU ki saari lines par poora lag jata tha | **Line-level anupaat baant** (gross ke hisse se, bacha sabse badi line par) |
| Backup ka koi scheduled job hi nahi tha | **23:30 backup_restore job** (data/backups/, restore-parikshan ke saath); preflight wahi jagah dekhta hai |

## 🚪 V16 — Acceptance Gates Kit (22 Oct 2026)
Audit ke 5 live gates ko "salah" se "chalane yogya astra" me badla — keys aate hi ek command:
- **`src/pilot.py` + `scripts/preflight.py`** — preflight report: har connector ki taiyaari, capability halat, Owner khata, kill switch, backup, HTTPS pack — jo nahi hai woh ✘ ke saath saaf dikhega, ready ka jhootha dawa kabhi nahi
- **Reconciliation report** — orders ↔ settlements ↔ ads ka milaan ek jagah (farq EXCEPTION ke roop me dikhega, chhupega nahi)
- **Controlled drill** — gate #3 poora: proposal → Owner approve → queue → adapter execute (vendor refetch-pushti) → rollback (purani halat ki pushti), har kadam ka saboot steps me. Taale teen: kill-switch ON = BLOCKED; live=False = sirf yojana; write_ads certified na ho = BLOCKED. Test me nakli vendor ke saath poora drill PASS aur campaign purani halat par wapas verified.
- Kul **22 test suites SAB PASS**.

## 🎯 V15 — Chauthe audit ke data-accuracy mudde (22 Oct 2026)
| Issue | Fix |
|---|---|
| War Room TACOS lifetime unmatched totals se banta tha | **Matched-period enforcement**: TACOS sirf pichle 30 din ki dated NET bikri banam usi khidki ke period-tagged ads kharch par; data aparyapt to `tacos_pct = null, status = NOT_COMPARABLE` — screen par jhootha ratio nahi dikhega |
| Outcome maap campaign naam par nirbhar tha, actions me campaign_id hota hai | **campaign_map** (Ads sync se ID→naam naksha, roz ke sync me bhi); outcome ab ID se naam pakka dhoondhta hai |
| Kam dated data par bhi success ghoshit ho sakta tha | **Coverage gates**: campaign raah par khidki ke ≥70% din ke periods dono taraf; SKU raah par kul ≥4 order-lines — warna INSUFFICIENT_DATA |
| Canonical orders INSERT OR IGNORE — status/refund kabhi update nahi hote the | Teeno raasto (SP API, Flipkart, CSV) par **UPSERT**; refunds Finances se `order_items.refund` me; **revenue ab NET** hai aur **Cancelled orders ginati se bahar** |
| Boundary din share karne wale periods ka takraav choot jata tha | Periods ab **inclusive date hisaab** se — ek din ka takraav bhi BLOCK; satta hua par alag dinon wala saaf |
| Product 360 channels mix karta tha | `?platform=` par ek-channel nazar; bina platform ke **sales_by_platform** alag-alag + channels suchi |
| Bacha hua (code se bahar) | Competitor/rank ka licensed provider, live seller-account verification, asal reports ka reconciliation, controlled pilot — sab live duniya ke kadam (neeche suchi) |

## 🎯 V14 — Teesre audit ki correctness kamiyaan (22 Oct 2026)
Audit is baar aur gehrai me gaya — aur phir sahi nikla. Fixes (saboot: test_v14_audit3.py, kul 20 suites pass):
| Issue | Fix |
|---|---|
| Outcome maap jama-kul totals se hota tha, asal 7/14-din khidkiyon se nahi | **Windowed measurement**: lagne se pehle ke w din banam baad ke w din — campaign ke liye period-tagged terms, SKU ke liye dated canonical orders; data na mile to jhootha nateeja nahi, `INSUFFICIENT_DATA` |
| Overlapping Ads periods dohra gin sakte the | **Period Overlap Engine** (connectors/periods.py): contained=skip, supersede=replace, partial=BLOCK with wajah; roz ka sync ab 1-din ki khidki par |
| Production HTTPS bypass (base compose 8765 public) | Base compose ab `127.0.0.1:8765` — bahar ka rasta sirf Caddy/HTTPS |
| Listing publish ka backend endpoint nahi tha | `POST /api/v1/listings/publish` (execute perm) + dashboard par Preview-parkh/Live buttons |
| SKU fees scheduled sync se judi nahi thi | data_sync ab SP orders ke saath **order fees** bhi laata hai; Flipkart branch bhi scheduled sync me jud gaya |
| Ek SKU dono bazaaro par mix ho sakta tha | products/campaigns ki pehchan ab **(sku, platform)** — bina data khove migration |
| Days-of-cover ki raftaar zyada dikhti thi (sirf bikri-din ginna) | Denominator ab poori observation-window (pehli→aakhri bikri ka antar) |
| War Room organic/TACOS ka aadhaar chhupa tha | KPIs me `organic_basis`/`tacos_basis` saaf shabdon me — organic ek ANDAAZ hai, ye ab screen par bhi likha aayega |

## 🏁 V13 — Code-side jo kuch bhi bacha tha, sab band (22 Oct 2026)
| Bacha hua kaam | Hal |
|---|---|
| Self-learning aadha tha (action lagta, nateeja khud nahi maapa jata tha) | **Outcome Engine**: execute par baseline tasveer; 7/14 din par asal dobara-maap; jeet/guardrail se success; kind-wise asal jeet-dar (rule confidence) — seekh ab asal bikri se banti hai |
| SKU-wise exact fees baaki thi | **SP Finances API** se per-order fees → `order_fees`; contribution me sabse pakkī `SKU_EXACT` shreni sabse upar |
| Automatic listing publishing pending tha | **Listings Items API** path: APPROVED version hi; pehle VALIDATION_PREVIEW parkh; live sirf `write_listings=certified` par; Amazon ke issues jaise-aaye darj |
| SKU 360° drilldown nahi tha | Products screen me **360° panel** (bikri, munafa+fee precision, stock cover, listing versions) + War Room **platform filter** |
| HTTPS/protected deployment | `docker-compose.prod.yml` + Caddy (auto-HTTPS + security headers) — domain/host milte hi chalu |
| Security/load saboot | Injection-parakh, kill-switch par vendor execute block, 2000-order performance smoke — `test_v13_hundred.py` |

**Code-side: 19/19 suites, kuch pending nahi।** Iske aage ke % code se nahi badhenge — woh live duniya ke hain:
live certification (tumhari API keys), Ads/Listings pilot sign-off (certified gates), licensed rank data (contract),
repo Private (GitHub Settings), hosting + 14-din pilot, aur hero SKU cost sheet.

## 🔧 V12.2 — Dusre audit ke 6 asal source-mismatch fix (22 Oct 2026)
| Issue | Fix |
|---|---|
| War Room revenue mismatch (naya sync canonical, warroom legacy padhta tha) | `analytics.py` — canonical-first unified totals; warroom ab wahi se padhta hai, source label ke saath |
| Dashboard revenue field bug (`k.revenue` vs `total_sales`) | KPIs me ab revenue + total_sales + orders teeno; mapping pakka |
| Docker me dashboard missing | Dockerfile me `COPY dashboard/` — container se bhi dashboard serve hoga (smoke-verified pattern) |
| Ads sync duplication | search_terms me batch/period columns; file ke andar (term+campaign) aggregation; period-wise delete-then-insert — re-sync/re-import par totals double NAHI |
| FBA coverage adhoora (sirf <50 units andaaz) | Asal **days-of-cover**: canonical bikri-raftaar se; <21 din par SKU-ke-naam ke saath chetavni |
| Fee accuracy (platform average) | Coverage-weighted precision: ≥80% settlement coverage = REALIZED/HIGH, 30–80% BLENDED/MEDIUM, neeche ESTIMATE/LOW — har number par `fee_precision` label |
| Security (audit §5.2) | Login **rate-limit** (5 galat = 10-min lock) + MFA enrolment endpoint `/api/v1/auth/mfa/enable`; HTTPS deployment ki zimmedari (RUNBOOK: reverse proxy) |
Saboot: `tests/test_v12_2_fixes.py` — kul **18 suites SAB PASS**.

## 🔧 V12.1 — Bahari audit ka jawab (22 Oct 2026)
Ek bahari review ki zyadaatar baatein sahi nikli — jo code se fix ho sakti thi, sab ho gayi (17 suites sab pass, test_v12_hardening.py saboot):

| Audit point | Fix |
|---|---|
| Repo PUBLIC (hamari "private" jaankari galat thi — signed-out verify) | Private karna malik ka GitHub Settings kaam (1 min); repo me secret/raw PII kabhi nahi gaya (scan ✔); README ki galat line sudhar gayi |
| sync_service legacy; Flipkart sync adhoora | V2: SP orders+items canonical, Ads terms sync CLI, Flipkart orders+listings, CSV wizard-based |
| Daemon sab jobs ek hi daily_cycle se | `job_handlers.py` dedicated handlers + compose `worker` service; bina-connector data_sync imaandaar SKIP |
| ManualAdapter par vendor pushti nahi | `AmazonAdsWriteAdapter`: asal write + refetch-pushti + rollback; `write_ads=certified` gate bina nahi chalega |
| Fees assumptions | Settlements se realized fee-rate contribution/bids me; estimate par `fee_source` label |
| Dashboard :8765/CORS/token | Same-origin serving, XSS escaping, rank chart + spend bars, **TOTP MFA** |
| Helium10 data / live certification / pilot | Code se aage: licensed contract + API keys + hosting (neeche wali table) |

## 🚀 V12 — Master Blueprint ke hisaab se poora development (22 Oct 2026)
User ke bheje **V12 Blueprint + Developer Backlog** (docs/V12_BACKLOG.md) ke har requirement ID par kaam hua.
**Kul 16 test suites, sab pass** (purane 11 + 5 naye V12: p0, integrations, growth, uc, qa).

| ID | Kya bana | Saboot |
|---|---|---|
| SEC-01 | Login + RBAC (6 roles), saare API band bina token ke | test_v12_p0 + HTTP parikshan (401/200) |
| SEC-02 | Kill switch server-side, DB me persist — restart par bhi yaad | test kill + QA-06 (file-DB restart) |
| SEC-03 | Approval state machine (9 states), Tier-2 par 2 alag Owner, idempotency key, poora event audit | test_v12_p0, UC-09 |
| SEC-04 | Keys sirf env/file; repo-wide secret scan script + CI-ready | scripts/secret_scan.py (QA-14 me pass) |
| DAT-01 | Canonical schema: order_headers/order_items (line-level), settlements, batch SHA-256, duplicate import block | UC-07, wizard test |
| DAT-02 | Matched-period gating — windows na milein to TACOS = NOT_COMPARABLE | test_v12_p0 metrics |
| JOB-01 | Durable job runner: IST next_run DB me, lock, retry/backoff, dead-letter record, daemon mode | QA-11 |
| UI-01 | Naya dashboard: koi demo number nahi; khaali DB = imaandaar khaali state | QA-03 |
| INT-01 | SP-API LWA-only (AWS keys ki shart khatm), orders pagination | test_v12_integrations |
| INT-02 | Ads Reporting v3 poora pipeline: create→poll→gzip download→DB import + batch record | mock-transport test |
| INT-03/05, API-03 | Capability registry: Flipkart ads = report-only, write = unavailable (fictional button kabhi nahi); Intel adapter bina license ke UNAVAILABLE | UC-06 |
| INT-04 | CSV Wizard: preview (hash/kind/rows) → commit, duplicate block, receipt | wizard test |
| ADS-01..06 | Ads Studio: health, **profit-led bid** (SKU margin se target ACOS, max CPC, 20% daily cap), harvest/negative safety, pacing, 3 budget scenarios | test_v12_growth, UC-03/04 |
| KWD-01..04 | **clicks×20 wala jhootha volume hata diya**; taxonomy (badam↔almond), opportunity matrix (volume = null/UNAVAILABLE), rank alerts ≥3 points | UC-02 |
| RNK-01..04 | Rank observations scope ke saath (locale/device/source), funnel ki neev, experiment verdict se jod | keyword_lab |
| CMP-01..04 + CP-01..05 | Peer matching (grade/pack/processing; **W240≠W320**), ₹/100g, dated snapshots + change feed, decision packets (saboot→farq→parikalpana→margin guardrail→tajurba) | UC-01/05 |
| LST-01..05 | Listing Score **v2** (versioned, 'Amazon formula nahi' saaf likha), content gap audit, listing versions + approve gate + rollback | UC-08 |
| CVR-01..04 | Creative brief endpoint, experiment registry (min sample bina jeet nahi), season/BOM lab | UC-10 |
| FIN-01/02 | Versioned costs; **cost unknown/stale = scale band**; settlement import + reconciliation (MATCHED/EXCEPTION) | QA-07 prakar ke tests |
| INV-01/02 | Stock-to-ads gate (STOCKOUT = scale band), hamper BOM feasibility | UC-04/10 |
| AGY-01 | Agency scorecard — saboot bina task DONE nahi, fees + verified badlav | growth test |
| AIG-01/02 | Learning store (lagu na hue action se seekh nahi), LLM budget governor (roz/mahina cap, prompt hash-matra log) | growth test |
| POL-01 | Verified Fact Registry — saboot bina dawa copy me nahi (NEEDS_EVIDENCE) | UC-08 |
| OPS-01 | System health (jobs/kill/capabilities/alerts), backup + restore parikshan | QA-14 |
| API-01/02 | OpenAPI spec (docs/openapi.yaml), envelope {data, meta, errors}, idempotent proposals/execution | backend HTTP test |
| UX-01..16 | Dashboard ke **16 screens** saare API-backed, login ke saath, evidence badges, live kill switch | QA-13 + JS syntax + saare endpoints 200 |

### V12 me bhi jo CODE se aage ki cheez hai (jhooth nahi bolenge)
| Cheez | Asli wajah |
|---|---|
| Live API certification (QA-04 asal) | Tumhari SP-API/Ads keys lagein tabhi — code + mock pipeline taiyaar hai |
| Vendor par asal write + verification (GATE-D) | ManualAdapter saboot (ref) maangta hai; live write adapter owner ke pilot sign-off ke baad |
| Licensed keyword/rank data (Helium10 aadi) | Contract kharidna tumhara faisla hai — tab tak volume/rank 'unknown' hi dikhega |
| PostgreSQL/Next.js jaisi badi migration | Blueprint ki 'suggested' topology hai; maujuda stdlib+SQLite asal kaam kar raha hai — bojh badhne par migration ka faisla |
| GATE-F pilot (2 hafto ki asal chaap) | System 24×7 host par chalega tabhi gin sakte hain — hosting faisla tumhara |

---

# Purana record (V11 tak)

## Ban gaya hai (code + tests ke saath)
| Hissa | Halat |
|---|---|
| Engines (profit/listing/ads/keyword/competitor/flywheel/FBA/claim-check) | ✅ 20+ modules, tested |
| Agent Layer — **saare 9 agents asal kaam ke saath**: A01 Market (season calendar), A02 Competitor (price-hamla pakadna), A03 Keyword (bank + HERO chunav), A04 Listing (title/bullets generation), A05 Creative (7-shot brief + video script), A06 Ads (DB se proposals), A07 Pricing (margin parakh + price proposals), A08 Review (shikayat mining), A09 Governance (daily cycle) | ✅ V9 |
| Chalane ke sadhan: `src/run_cycle.py` (ek command daily report), `run_tests.py`, Dockerfile | ✅ V9 |
| Flows design F1–F10 + Scheduler (9 daily + 2 weekly jobs) | ✅ |
| Self-Learning (knowledge store, outcome learner, A/B engine, source registry) | ✅ design+core tested |
| Algorithm Intelligence (Amazon/Flipkart rank models, Buy Box, change impact, Rank Probe) | ✅ |
| Connectors: Amazon SP-API (SigV4), Ads API, Flipkart, Unicommerce, CSV Import | ✅ code + mock tests; **live test data/keys aane par** |
| Database (SQLite: knowledge/actions/rank/products/orders/campaigns/search_terms/inventory) | ✅ |
| Backend API (health, warroom, connectors status, approvals DB se, cycle run) | ✅ |
| Dashboard (11 sections, controls, kill switch, live-data loader) | ✅ |
| Control Center + Approval Engine (Tier 0/1/2 + guardrails) | ✅ |

## Data LIVE hai — Phase-0 Audit ho gaya (21 Oct 2026) 🟢
| Cheez | Halat |
|---|---|
| User ki 3 reports import (224 campaign rows, 253 search-term rows, 104 orders) | ✅ Brand: **Dry Fruit Farm** (Amazon) |
| **Phase-0 Audit** `docs/PHASE0_AUDIT_2026-10-21.md` | ✅ TACOS ≈61%, ROAS 1.48, 14/23 campaigns zero-sale, bikri ka 87% Brazil Nuts + Cranberry par, CVR sirf 3.6% |
| CI workflow file (user ne web se lagayi) | ✅ GitHub par verify |
| Ads Agent ke asal proposals | ✅ 15 bid-down proposals (approval ke intezaar me) |
| **Action Planner (V10)** — pause/scale/watch/negative lists asal data se | ✅ `docs/ACTION_PLAN_2026-10-21.md`: 16 tay kaam, pause se ₹3,808/cycle bachat; dono hero listings ke sudhar packs (score 35→65) |
| Importer ke 2 asal bug fix (order-id column, campaign aggregation) + Keyword Agent ka term-aggregation fix | ✅ asal data ne pakde |

## Baki hai (kis ka intezaar hai)
| Kaam | Kis par atka hai |
|---|---|
| Margin/break-even hisaab | User: **hero SKU cost sheet** (Brazil Nuts + Cranberry pehle) |
| Kaju/Badam listing jaanch (ads chal rahe, bikri ~0) | User: unki **listing links** |
| Flipkart ki halat | User: Flipkart data |
| Auto-sync (roz ka data bina bheje) | User: API keys (config/connectors.json) — CSV rasta ab chal raha hai |
| FBA status + agency fee ki jankari | User |
| LLM Agents ka dimaag (copy/strategy LLM se) | LLM API key (env: GOS_LLM_API_KEY) — interface taiyaar hai, key aate hi plug |
| Asal fee tables (Amazon/Flipkart category-wise) | Live Seller Central/Hub se milegi |
| Deployment (server par 24×7 chalana) | Server/hosting ka faisla (Phase-2 ke baad) |
| Quick Commerce (Blinkit/Zepto), D2C, AI creative generation, ML forecasting | Phase-3 |

## 🏁 Development Complete (code-side) — V11, 21 Oct 2026
Jo kuch bina user ke inputs ke ban sakta tha, **sab ban gaya hai**: 20+ engines, 9 asal agents, Action Planner,
Season Planner (Diwali combos), LLM ka asal call-code (key lagte hi live, claim-check ke saath), asal connectors
+ CSV import, backend (warroom/approvals/action-plan/season-pack/cycle), dashboard, Docker + compose, CI.
**Kul 44 tests, 11 suites, sab pass — aur system asal business data par chal bhi raha hai.**
Iske aage ka har kadam kisi na kisi input par ruka hai (neeche wali table), code par nahi.

## Niyam
- Jo nahi bana, woh yahan "baki" me likha rahega — README ya dashboard me kabhi "ho gaya" jhooth nahi likhenge.
- Har commit ke saath tests pass hone chahiye (CI laga hai).
