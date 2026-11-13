# NutriScale OS — Runbook (how the system runs)
_Repo: https://github.com/iamprateeknk-pixel/nutriscale-os · Brand: Dry Fruit Farm_

---

## 1. What the system is, in one line
A **daily operator** for an Amazon/Flipkart dry-fruits business: it brings in data, checks it, turns findings
into proposals, asks you to approve anything that changes money or listings, and measures the outcome of every
applied change so it can learn.

## 2. Where it lives
| Place | What is there |
|---|---|
| **GitHub repo** | All code, docs and tests — the source of truth |
| **The machine that runs it** (your PC, the Box, or a server) | A copy of the repo + `data/growth_os.db` (SQLite — all data, proposals, learning) |
| **Browser** | The dashboard at `http://<host>:8765` — where you look and approve |

## 3. Requirements
| Item | Detail |
|---|---|
| **Python 3.10+** (3.12 recommended) | The only hard requirement |
| **External libraries** | **None** — everything runs on the Python standard library |
| **Database** | SQLite — built into Python; file: `data/growth_os.db` |
| **Disk/RAM** | ~100 MB disk, little RAM — any ordinary laptop/server works |
| **Internet** | For API sync (CSV upload works without it) |
| **Optional** | Docker, an LLM API key (AI-written copy), platform API keys (automatic sync) |

## 4. Ways to run it
### A) On your own computer
```bash
git clone https://github.com/iamprateeknk-pixel/nutriscale-os.git
cd nutriscale-os
NUTRISCALE_OWNER_USER=owner NUTRISCALE_OWNER_PASSWORD='a-long-password' python3 backend/app.py   # first run creates the Owner
python3 src/jobrunner.py --daemon      # in a second terminal: the 24x7 scheduler
```
Open `http://localhost:8765` and log in. `python3 src/run_cycle.py` runs the whole daily cycle once, on demand.

### B) Docker
```bash
cp .env.example .env    # set NUTRISCALE_OWNER_PASSWORD
docker compose up -d    # backend + scheduler; data lives in a Docker volume
```
For HTTPS on your own domain: `DOMAIN=app.your-domain.in docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` (Caddy).

### C) The Box cloud computer (public HTTPS link)
```bash
~/nutriscale-os/deploy/box/start.sh
```
Starts the backend, the scheduler and a Serveo HTTPS tunnel, and prints the dashboard link (also saved in
`PUBLIC_URL.txt`). The Box sleeps when idle — run the script again after it wakes. The link changes on every
reconnect; a stable link needs a VPS + domain (option B with Caddy).

## 5. How data gets in
| Route | Status |
|---|---|
| **Dashboard upload** (Integrations → Upload a report) | ✅ Works today — CSV/TSV from Seller Central, Ads Console, Flipkart Seller Hub, Unicommerce; type auto-detected, duplicates blocked |
| **Brand Analytics drop folder** | ✅ Files in `data/brand_analytics_inbox/` are imported daily at 06:45 |
| **Amazon SP-API + Ads API** | Code ready; daily auto-sync once keys are in `config/connectors.json` |
| **Flipkart API** | Code ready; needs Flipkart API approval, otherwise use CSV |
| **Unicommerce API** | Code ready; 3-way stock reconciliation once a tenant/API user exists |

## 6. Daily schedule (IST)
| Time | Job | What it does |
|---|---|---|
| 06:00 | learning_crawl | Refresh research rules, learn from outcomes and from your data |
| 06:30 | data_sync | Fresh Amazon/Flipkart/Unicommerce data (when connectors are configured) |
| 06:45 | brand_analytics_import | Import new SQP/SCP files from the drop folder |
| 07:00 | measure_results | Measure 7/14-day outcomes of applied actions; update rule confidence |
| 07:15 | seller_health_check | ODR/cancellation/late dispatch — red alert near limits |
| 07:30 | stock_reconcile | 3-way stock reconciliation |
| 07:45 | growth_autopilot | Turn playbook findings into approval-gated proposals; expire old proposals |
| 08:00 | war_room_report | Daily one-page picture on the dashboard |
| 12:00 | fba_cover_check | Days-of-cover warning under 21 days |
| 18:00 | rank_probe | Record hero-keyword rank observations |
| 21:00 | weekly_report | Sundays only: weekly growth report in `data/reports/` |
| 23:00 | daily_learning_summary | Summary of the day's runs |
| 23:30 | backup_restore | Nightly DB backup in `data/backups/` with a restore test |

## 7. How decisions are made and applied
```
Data (API/CSV) → SQLite DB → engines (profit / ads / listing / keyword math)
   → agents + Growth Autopilot → proposals (with rule_ids and the reason)
   → approval tiers:
       Tier 0 AUTO      — small safe actions (legacy negatives) applied automatically
       Tier 1 ONE-TAP   — bids/negatives/harvest/listing patches: one tap in the Approval Inbox
       Tier 2 DOUBLE    — big money or listing decisions: two different Owners must approve
   → apply (today: by hand in Ads Console / Seller Central, then record the proof;
            with certified API capabilities: by the system, with refetch confirmation and rollback)
   → after 7/14 days the outcome is measured → VERIFIED outcomes update rule confidence
     (3 losses in a row = rule disabled)
```
The **Kill Switch** is in the top bar — one tap stops every live write. Guardrails (daily spend cap, minimum
margin floor) cannot be crossed by any agent. Proposals expire after 7 days without a decision.

## 8. What you do each day
- **Now (CSV mode):** upload fresh reports once or twice a week; review the Approval Inbox — **about 10 minutes a day**.
- **With API keys:** approvals only — data and plans arrive by themselves.
- **With an LLM key:** listing copy is written by the LLM (otherwise by rule templates); both pass the claim checker.

## 9. Costs
| Item | Cost |
|---|---|
| System/code | ₹0 (yours) |
| Hosting for 24×7 | ~₹500–900/month VPS (or an always-on machine you own = ₹0) |
| Amazon/Flipkart APIs | ₹0 (your own seller account keys) |
| LLM key (optional) | ~₹500–2,000/month (small model) |

## 10. Built-in safety rules
- API keys live **only in a file on your machine** — never on GitHub or in chat.
- Customers' raw data (names/addresses) never goes into the repo — only aggregates.
- Every decision is recorded in the DB (who, when, why) — a full audit trail.
- Listing copy with false or health-harming claims **never goes live** (claim checker + fact registry).
- Imports only accept uploaded files or files inside `data/` — never arbitrary server paths.

## 11. Changing the password
```bash
NUTRISCALE_DB=$PWD/data/growth_os.db python3 scripts/set_password.py <username>
```
The new password is asked for hidden; all existing logins of that user are signed out.

## 12. Current status
See [STATUS.md](../STATUS.md). In short: the code side is complete and tested (31 suites); what remains needs the
real world — your reports or API keys, your approvals, stable hosting, and the first 7/14-day outcomes.
