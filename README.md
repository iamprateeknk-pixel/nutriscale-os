# 🌰 NutriScale OS

**An approval-gated, self-learning sales growth system for a dry-fruits brand on Amazon India and Flipkart.**

It improves listings, manages ads, watches competitors, plans FBA and Unicommerce stock, and turns what it finds
into proposals. **Nothing changes live without the owner's approval.** Every applied change is measured after
7/14 days, and the result raises or lowers the agents' confidence in the rule behind it.

> Honest note: this system is not magic. It is a profit-first, data-first machine — it fixes listings, price and
> conversion first, then scales ads, and uses the organic flywheel (rank → free sales) to push blended ROAS up.
> Without real data (reports or API keys) it shows empty states, never made-up numbers.

## What it does

- **Dashboard** — "Today" home screen with the most urgent tasks first, Approval Inbox, War Room, Listing Builder,
  Keyword Plan, SQP Funnel, Ads Studio, Growth Playbook, Agent Brain, Knowledge Base and more (23 screens,
  light/dark mode, works on mobile, `Ctrl+K` to jump to a screen).
- **Growth Autopilot** — runs daily at 07:45 IST and turns findings into proposals: negatives for wasted spend,
  harvesting winning terms into Exact, fixing self-competition, SQP scale/click problems, pausing ads on
  out-of-stock SKUs. It never applies anything itself; stale ads data (21+ days) pauses it.
- **Self-learning brain** — 42 researched marketplace rules, each with sources and a confidence score. Confidence
  changes only from VERIFIED outcomes; a rule that loses 3 times in a row is disabled. Lessons are also derived
  from your own data (best-converting terms, wasted terms, SQP diagnoses).
- **Listing rules engine** — Amazon's 75-character title rule (from 27 Jul 2026), 125-character Item Highlights,
  200-byte backend terms, bullet/image rules, and FSSAI claim checks. Claims that need proof (origin, grade,
  organic, nitrogen flush…) are blocked until evidence is in the fact registry.
- **Profit-first ads** — break-even and target ACOS per SKU from real cost + fees; scaling is blocked without cost.
- **Safety** — login + roles (RBAC), optional TOTP MFA, a server-side kill switch, a proposal state machine
  (approve → queue → execute with proof → rollback), 7-day proposal expiry, nightly backups.
- **Connectors** — Amazon SP-API (LWA), Amazon Ads API (Reporting v3), Flipkart, Unicommerce, plus CSV/TSV upload
  straight from the dashboard (works today, no API approval needed).

## Run it

```bash
# First run: create the Owner login, then start the backend
NUTRISCALE_OWNER_USER=owner NUTRISCALE_OWNER_PASSWORD='a-long-password' python3 backend/app.py
# Open http://localhost:8765 and log in

# 24x7 scheduler (daily sync, learning, autopilot, backups) in a second terminal
python3 src/jobrunner.py --daemon

# Or both with Docker
docker compose up -d
```

Getting data in:
- **Easiest:** Integrations screen → *Upload a report* → drop the CSV from Seller Central / Ads Console.
- Command line: `python3 src/sync_service.py --csv-search-terms report.csv` (also `--csv-campaigns`, `--csv-orders`, `--csv-inventory`).
- API keys: see **[CONNECTORS_SETUP.md](CONNECTORS_SETUP.md)** — never send keys over chat or GitHub.

Change a password: `python3 scripts/set_password.py <username>` (asks for the new password hidden).

Running on the Box cloud computer with a public HTTPS link: `deploy/box/start.sh` (see [docs/RUNBOOK.md](docs/RUNBOOK.md)).

## Tests

```bash
python3 run_tests.py   # all suites at once (31 suites as of V26)
```

## Status

What is built and what is left — the honest log: **[STATUS.md](STATUS.md)**.
How the system runs day to day: **[docs/RUNBOOK.md](docs/RUNBOOK.md)**.

## Design documents

| File | What it is |
|---|---|
| `MASTER_BLUEPRINT.md` | V1 — original 12-agent design, ads/listing systems |
| `MASTER_BLUEPRINT_V2.md` | V2 — autonomous approval mode, flywheel, FBA, Unicommerce |
| `MASTER_BLUEPRINT_V3_SELF_LEARNING.md` | V3 — self-learning layer |
| `GAP_AUDIT_AND_BLUEPRINT_V4.md` | V4 — gap audit, 9 agents + 10 flows, algorithm intelligence |
| `ULTIMATE_AUDIT_V5.md` | V5 — honest scorecard and odds |
| `docs/V12_BACKLOG.md` | V12 requirements backlog (requirement IDs referenced throughout the code) |
| `docs/openapi.yaml` | API reference |

## Safety rules

- `config/connectors.json`, `.env` and `data/` are gitignored — **never commit them**.
- No money-moving action happens without approval and an audit log.
- Listing score < 70 → ads scaling blocked (listing first, then money).

---
*This repository is PUBLIC on GitHub. Business data is therefore never pushed — no raw orders or customer data.
To make it private: GitHub → Settings → Danger Zone → Change visibility.*
