# NutriScale OS — Teeno Setup Ek Jagah
_Repo: https://github.com/iamprateeknk-pixel/nutriscale-os_

Teeno me se **koi bhi ek pehle** kar sakte ho. Sabse tez asar Setup-1 (CSV rasta) ka padega.

---

## SETUP 1 — Data / Connectors (system ko asal data milega)

### Rasta A: CSV (AAJ se, kisi manzuri ka intezaar nahi) ⭐ pehle yahi karo
1. **Amazon Ads Console** kholo → Measurement & Reporting → **Reports** → Sponsored Products → **Search Term Report** (pichle 60–90 din) → Download (CSV)
2. **Ads Console → Campaign Manager** → apne campaigns select karke **Export** (CSV)
3. **Seller Central** → Orders → **Order Reports** → pichle 90 din ke orders (CSV)
4. Teeno files **Muse ko yahin chat me bhej do** — ya khud chalana ho to:
   ```
   python3 src/sync_service.py --csv-search-terms search_terms.csv
   python3 src/sync_service.py --csv-campaigns campaigns.csv
   python3 src/sync_service.py --csv-orders orders.csv
   ```
5. Flipkart ke liye: Seller Hub → Orders → Export → wahi teesra command `--platform Flipkart` ke saath.

### Rasta B: API Keys (hamesha ke liye auto-sync chahiye to)
1. File banao: `config/connectors.example.json` ki copy → **`config/connectors.json`**
2. Platform-wise keys kahan se milengi (poori detail repo ki **CONNECTORS_SETUP.md** me hai):
   - **Amazon SP-API:** Seller Central → Develop Apps (LWA Client ID/Secret + Refresh Token) + **AWS IAM** se Access Key/Secret (ye SP-API ki shart hai)
   - **Amazon Ads:** advertising.amazon.com → API applications (Client ID/Secret + Refresh Token + Profile ID)
   - **Flipkart:** Seller Hub support se "API Access" ka anurodh → App ID/Secret (na mile to Rasta A hi chalega)
   - **Unicommerce:** Panel → Settings → API user banao → tenant URL + username/password
3. Check karo: `python3 src/sync_service.py --status` — ✔ CONFIGURED dikhna chahiye.
4. Pehla sync: `python3 src/sync_service.py --connector amazon_sp` (aur baki connectors isi tarah)
> ⚠️ Keys **kabhi chat me mat bhejna** — file tumhare computer par rahegi, system wahi se padhega. `config/connectors.json` gitignore me hai, GitHub par kabhi nahi jayegi.

---

## SETUP 2 — GitHub CI File (har push par tests apne aap chalenge)

GitHub ka niyam hai: `.github/workflows/` me file sirf repo ka malik web se daal sakta hai, koi app nahi. **1 minute:**
1. Repo kholo: https://github.com/iamprateeknk-pixel/nutriscale-os
2. **Add file → Create new file** dabao
3. File ka naam bilkul ye likho: `.github/workflows/tests.yml`
4. Repo ki **`docs/CI_SETUP.md`** file me jo YAML code diya hai, woh pura copy-paste karo
5. Neeche **Commit changes** dabao

Ho gaya — ab har push par Actions tab me hari tick dikhegi (sab tests pass).

---

## SETUP 3 — LLM Key (agents ko asal "dimaag" — copy/strategy ke liye, OPTIONAL)

Ye na ho to bhi system pura chalta hai (engines par). Ho to Listing/Keyword/Creative agents
bhasha samajhkar aur behtar copy/strategy banayenge.

1. **Key kahan se milegi** (koi ek chuno):
   - OpenAI: https://platform.openai.com → API keys (card se chhota recharge lagta hai)
   - Anthropic (Claude): https://console.anthropic.com → API keys
   - Google (Gemini): https://aistudio.google.com → Get API key (shuruaat ke liye sasta/free star)
2. **System ko key kaise doge** — chat me NAHI. Apne computer par terminal me:
   ```
   export GOS_LLM_API_KEY="apni-key-yahan"
   export GOS_LLM_MODEL="chune-hue-model-ka-naam"
   ```
   (Hamesha ke liye rakhna ho to ye do line apni `.env` file me daal do — `.env` bhi gitignore me hai.)
3. **Jaanch:** 
   ```
   python3 -c "import sys; sys.path.insert(0,'src'); from agents.base import LLMProvider; print('LLM taiyaar:', LLMProvider().available)"
   ```
   `True` aaye to samajho jud gaya. Key milte hi main LLM ka asal call-code jod dunga (interface pehle se taiyaar hai).
4. **Kharcha samajh lo:** chhote model se shuru karo — listing/copy ke kaam par andazan ₹500–2,000/mahina ka star kaafi hota hai; system me Cost Governor ka niyam hai ki koi agent bina budget ke nahi chalega.

---

## Teeno ke baad kya hoga
- Setup 1 → Phase-0 Audit shuru (paisa kahan jal raha hai) + dashboard 🟢 LIVE
- Setup 2 → repo khud apni sehat ki report dega har push par
- Setup 3 → agents ka V10 upgrade: LLM-wali copy/strategy live

_Koi step atke to screenshot ya error ka photo bhej do — wahin se aage badha dunga._
