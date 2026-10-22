# NutriScale OS — RUNBOOK (System kaise chalega, poori jankari)
_Repo: https://github.com/iamprateeknk-pixel/nutriscale-os (Private) · Brand: Dry Fruit Farm_

---

## 1. System hai kya — ek line me
Tumhare Amazon/Flipkart dry-fruits business ka **roz ka operator**: data lata hai, parkhta hai,
faisle (proposals) banata hai, tumse sirf bade faislo par approval leta hai, aur har faisle ka
nateeja maap kar khud seekhta hai.

## 2. System kahan rehta hai
| Jagah | Kya hai wahan |
|---|---|
| **GitHub repo** (private) | Poora code, saare docs, tests — yahi "asli daftar" hai |
| **Jis machine par chalega** (tumhara PC ya server) | Repo ki copy + `data/growth_os.db` (SQLite — saara data, proposals, seekh) |
| **Browser** | Dashboard (`dashboard/index.html`) — yahi se tum dekhte/approve karte ho |

## 3. Requirements (kya-kya chahiye)
| Cheez | Detail |
|---|---|
| **Python 3.10+** (3.12 best) | Bas yahi ek shart hai |
| **Bahari libraries** | **EK BHI NAHI** — poora system Python ki stdlib par hai (isiliye kahin bhi atakta nahi, install jhanjhat zero) |
| **Database** | SQLite — Python ke saath built-in, alag install nahi; file: `data/growth_os.db` |
| **Disk/RAM** | ~100 MB disk, halki RAM — koi bhi aam laptop/server chalega |
| **Internet** | API sync ke liye (CSV rasta bina internet ke bhi chalta hai) |
| **Optional** | Docker (server par ek-command chalane ke liye), LLM API key (AI copy ke liye), platform API keys (auto-sync/auto-apply ke liye) |

## 4. Chalane ke 3 tareeke (kahan se run hoga)
### A) Apne computer par — aaj se, 2 minute me
```
git clone https://github.com/iamprateeknk-pixel/nutriscale-os.git
cd nutriscale-os
python3 backend/app.py          # backend: http://localhost:8765
python3 src/run_cycle.py        # ek command me poore din ka cycle + report
```
Dashboard dekhne ke liye `dashboard/index.html` browser me kholo — woh backend se live data legi.

### B) Docker — ek command (server ke liye saaf tareeka)
```
docker compose up -d            # .env file ke saath; data volume me surakshit rahega
```

### C) 24×7 Server (asal istemal ke liye yahi sahi hai) ⭐
Scheduler ko hamesha jagti hui machine chahiye. Ek chhota **VPS (₹500–900/mahina wala)**
ya ghar/daptar ki hamesha-on machine par Docker wala tareeka laga do — phir system
bina tumhare computer khule roz apna kaam karega.

## 5. Data andar kaise aata hai (flow ki shuruaat)
| Rasta | Halat |
|---|---|
| **CSV import** (Ads/Search-Term/Orders reports download karke) | ✅ **Aaj se chal raha hai** — tumne use karke dikha bhi diya |
| **Amazon SP-API + Ads API** | Code taiyaar; keys `config/connectors.json` me padte hi roz auto-sync |
| **Flipkart API** | Code taiyaar; Flipkart ki API-manzuri ya CSV rasta |
| **Unicommerce API** | Code taiyaar; tenant/API-user milte hi stock ka 3-way milaan |

## 6. Roz ka flow (Scheduler — IST)
| Samay | Kaam | Kaun karta hai |
|---|---|---|
| 06:00 | Nayi seekh crawl (fee/policy badlav sabse pehle) | A09 Governance |
| 06:30 | **Data sync** — Amazon/Flipkart/Unicommerce ka taaza data DB me | F1 |
| 07:00 | Purane faislo ke **nateeje maapo** (7/14 din) — jo rule fail, uska confidence kam | A09 |
| 07:15 | Seller health check (ODR/cancel/late) — khatra ho to laal alert | F10 |
| 07:30 | Stock ka 3-way milaan (Amazon vs Flipkart vs asal) | F2 |
| 08:00 | **War Room report taiyaar** — din ki 1-page tasveer dashboard par | F8 |
| 12:00 | FBA stock cover check — 15 din se kam = replenishment proposal | F3 |
| 18:00 | Hero keywords ki rank probe | A03/A09 |
| 23:00 | Din ki seekh ka summary — kal kya hoga | A09 |
| **Sunday** | Agent Strength report + playbook review (haftawar sudhar) | A09 |

## 7. Faisle kaise bante aur lagu hote hain (dil ka flow)
```
Data (API/CSV) → SQLite DB → Engines (profit/ads/listing/keyword hisaab)
   → 9 Agents parkhte hain → Proposals (actions table me)
   → Approval ke 3 star:
       Tier 0 AUTO      — chhote surakshit kaam (negative keywords jaise) khud lagu
       Tier 1 ONE-TAP   — bid/badlav jaise: dashboard par ek tap me approve
       Tier 2 DOUBLE    — bade paise/listing ke faisle: do baar pushti
   → Lagu (abhi: Action Plan ki checklist se Ads Console me haath se;
           API keys judte hi: system khud)
   → 7/14 din baad nateeja maapa jata hai → rule seekhta hai (3 baar fail = rule band)
```
**Kill Switch** dashboard me hai — ek dabate hi saari automation ruk jati hai. Guardrails:
roz ke kharch ki seema, minimum margin ka floor — ye paar karke koi agent nahi ja sakta.

## 8. Tumhe roz kya karna padega (sach)
- **Abhi (CSV mode):** hafte me 1–2 baar reports download karke de dena (ya mujhe bhej dena),
  dashboard par proposals approve/reject karna — **roz 10 minute se zyada nahi**.
- **API keys ke baad:** sirf approvals — data apne aap aayega, plan apne aap banega.
- **LLM key ke baad:** listing copy/strategy AI se aur behtar banegi (abhi rules se banti hai).

## 9. Kharcha (saara hisaab)
| Cheez | Kharcha |
|---|---|
| System/code | ₹0 (tumhara apna hai) |
| Hosting VPS (24×7 ke liye) | ~₹500–900/mahina (ya apni hamesha-on machine = ₹0) |
| Amazon/Flipkart API | ₹0 (apne seller account ki keys) |
| LLM key (optional) | ~₹500–2,000/mahina (chhota model) |
| **Kul** | **Agency ke ek mahine ke kharche se kam me poora saal** |

## 10. Suraksha ke niyam (system me bane hue)
- API keys **sirf tumhari machine ki file me** — GitHub/chat me kabhi nahi
- Graahako ka raw data (naam/address) repo me kabhi nahi jata — sirf kul hisaab
- Har faisla DB me darj (kisne, kab, kyon) — audit trail pakka
- Galat/health-harm dawaa wali listing copy claim-checker se **kabhi live nahi** jati

## 11. Aaj ki sachhi halat
✅ Chal raha hai: CSV data par poora cycle, audit, action plan, proposals, dashboard, CI tests (44 pass)
⏳ Tumhare inputs par: **cost sheet** (margin faisle), **Kaju/Badam listing links**, **Flipkart data**, API keys (auto ke liye), hosting ka faisla
