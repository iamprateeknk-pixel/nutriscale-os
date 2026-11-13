# NutriScale OS — Setup Guide (data, CI, LLM)
_Repo: https://github.com/iamprateeknk-pixel/nutriscale-os_

You can do these in any order. The biggest immediate impact comes from Setup 1 (getting real data in).

---

## SETUP 1 — Data / connectors (the system gets real data)

### Route A: report upload (works TODAY, no approval needed) ⭐ do this first
1. **Amazon Ads Console** → Measurement & Reporting → **Reports** → Sponsored Products → **Search term** report (last 60–90 days) → download (CSV)
2. **Ads Console → Campaign Manager** → select your campaigns → **Export** (CSV)
3. **Seller Central** → Orders → **Order Reports** → last 90 days of orders (CSV)
4. In the dashboard: **Integrations → Upload a report** → drop each file → check the preview → **Import**.
   Command-line alternative:
   ```bash
   python3 src/sync_service.py --csv-search-terms search_terms.csv
   python3 src/sync_service.py --csv-campaigns campaigns.csv
   python3 src/sync_service.py --csv-orders orders.csv
   ```
5. Flipkart: Seller Hub → Orders → Export → upload it the same way (or the third command with `--platform Flipkart`).
6. Brand Analytics: Seller Central → Brand Analytics → Search Query Performance → export and upload.

### Route B: API keys (permanent automatic sync)
1. Create the file: copy `config/connectors.example.json` → **`config/connectors.json`**
2. Where each platform's keys come from (full details in **CONNECTORS_SETUP.md**):
   - **Amazon SP-API:** Seller Central → Develop Apps (LWA Client ID/Secret + Refresh Token). AWS IAM keys are no longer needed.
   - **Amazon Ads:** advertising.amazon.com → API applications (Client ID/Secret + Refresh Token + Profile ID)
   - **Flipkart:** request "API Access" via Seller Hub support → App ID/Secret (if refused, Route A works fully)
   - **Unicommerce:** Panel → Settings → create an API user → tenant URL + username/password
3. Check: `python3 src/sync_service.py --status` — it should show ✔ CONFIGURED.
4. First sync: `python3 src/sync_service.py --connector amazon_sp` (and the same for the other connectors)
> ⚠️ **Never send keys over chat** — the file stays on your machine and the system reads it from there. `config/connectors.json` is gitignored and never goes to GitHub.

---

## SETUP 2 — GitHub CI (tests run on every push)

Already done: `.github/workflows/tests.yml` is in the repo. See **docs/CI_SETUP.md** if it ever needs to be re-added.
Every push and pull request then shows a green tick in the Actions tab when all tests pass.

---

## SETUP 3 — LLM key (OPTIONAL — better copy/strategy)

The system works fully without it (rule-based engines). With a key, the Listing/Keyword/Creative agents write
better copy. All generated copy still passes the claim checker and the fact registry.

1. **Where to get a key** (any one):
   - Anthropic (Claude): https://console.anthropic.com → API keys
   - OpenAI: https://platform.openai.com → API keys
   - Google (Gemini): https://aistudio.google.com → Get API key
   The provider must offer an OpenAI-compatible chat endpoint (set `GOS_LLM_BASE_URL` accordingly).
2. **Give the key to the system** — NOT over chat. In a terminal on the machine:
   ```bash
   export GOS_LLM_API_KEY="your-key"
   export GOS_LLM_MODEL="the-model-name"
   ```
   To keep it permanently, put these lines in your `.env` file (also gitignored).
3. **Check:**
   ```bash
   python3 -c "import sys; sys.path.insert(0,'src'); from agents.base import LLMProvider; print('LLM ready:', LLMProvider().available)"
   ```
   `True` means it is connected.
4. **Costs:** start with a small model — listing/copy work typically costs about ₹500–2,000/month. A built-in
   budget guard stops LLM use when the daily/monthly budget is used up (agents fall back to rules).

---

## After all three
- Setup 1 → the dashboard shows real numbers; the autopilot and learning start working on your data
- Setup 2 → the repo reports its own health on every push
- Setup 3 → LLM-written listing copy

_If a step gets stuck, share a screenshot or the error message._
