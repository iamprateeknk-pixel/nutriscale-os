# 🌰 NutriScale OS

**Autonomous Multi-Agent Ecommerce Growth System — Dry Fruits ke liye, Amazon IN + Flipkart par.**

Listings sudhare, Ads chalaye, Competitors par nazar rakhe, FBA + Unicommerce sambhale —
**khud sab kare, malik se sirf approval le.** Roz apne results aur web ke best sources se seekh kar strong hota jaye.

> Imaandar note: Ye system "magic" nahi hai. Ye ek profit-first, data-first machine hai —
> pehle listing/price/conversion fix karti hai, phir ads scale karti hai, aur organic flywheel
> (rank → free sales) se Blended ROAS ko 8–10 ki taraf le jati hai.

## Khaas baatein

- **9 Agents** (Market, Competitor, Keyword, Listing, Creative, Ads, Pricing, Review, Governance) + **10 Deterministic Flows** — jahan formula hai wahan agent nahi
- **Approval-Only Autonomous:** Tier-0 kaam khud, Tier-1 ek-tap approval, Tier-2 double confirm, aur bina-approval **Kill Switch**
- **Self-Learning:** har action ka result 7/14 din me maapa jata hai; fail rules khud band; web se roz subah learning crawl
- **Algorithm Intelligence:** Amazon (COSMO/Rufus era ke saath) + Flipkart ke alag rank models, Algo-Change Watcher, Rank Probe
- **Organic Flywheel math:** Paid ROAS nahi, **Blended ROAS / TACOS** hi asal KPI hai
- **FBA + Flipkart Warehouse planner**, **Unicommerce** 3-way stock reconciliation
- **FSSAI/Health-Claim checker** — galat dawa listing ko live hone se pehle rokta hai
- **Asal Connectors:** Amazon SP-API (SigV4), Amazon Ads API, Flipkart API, Unicommerce API + CSV import (bina manzuri ke aaj se chalta hai)

## Chalana

```bash
# 1) Kaunsa connector taiyaar hai
python3 src/sync_service.py --status

# 2) CSV se asal data bhariye (sabse tez shuruaat)
python3 src/sync_service.py --csv-search-terms report.csv
python3 src/sync_service.py --csv-campaigns campaigns.csv
python3 src/sync_service.py --csv-orders orders.csv

# 3) Backend + Dashboard
python3 backend/app.py            # http://localhost:8765
# browser me dashboard/index.html kholo — data hoga to LIVE dikhega, nahi to saaf khaali
```

API keys kaise bharni hain: **[CONNECTORS_SETUP.md](CONNECTORS_SETUP.md)** — keys kabhi chat/GitHub par mat bhejna.

## Tests

```bash
for t in tests/test_*.py; do python3 $t; done   # 7 suites, 28 tests
```

## Halat (Status)

Kya ban gaya, kya baki hai — imaandar diary: **[STATUS.md](STATUS.md)**

## Design ke kagaz (repo me hi hain)

| File | Kya hai |
|---|---|
| `MASTER_BLUEPRINT.md` | V1 — 12-agent mool design, ads/listing systems |
| `MASTER_BLUEPRINT_V2.md` | V2 — Autonomous approval mode, flywheel, FBA, Unicommerce |
| `MASTER_BLUEPRINT_V3_SELF_LEARNING.md` | V3 — Self-learning layer |
| `GAP_AUDIT_AND_BLUEPRINT_V4.md` | V4 — Gap audit, 9 agents + 10 flows, Algorithm Intelligence |
| `ULTIMATE_AUDIT_V5.md` | V5 — Imaandar scorecard aur % chances |

## Suraksha niyam

- `config/connectors.json` aur `data/` gitignore me hain — **kabhi commit mat karna**
- Har paisa-wala action approval + audit log ke bina nahi hota
- Listing score < 70 → ads scale band (pehle listing, phir paisa)

---
*Private repository — NutriScale OS, ek dry fruits business ke liye banaya gaya.*
