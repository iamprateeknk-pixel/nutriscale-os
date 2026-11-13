# Connectors Setup Guide — connect each platform yourself (15–30 min per platform)

**Rule: never send your keys over chat, WhatsApp or GitHub.** Keys only go into the `config/connectors.json`
file on the machine that runs NutriScale.

## First, check what is ready
```bash
python3 src/sync_service.py --status
```
Connectors showing `✔ CONFIGURED` are ready; follow the steps below for the rest.

Create the config file:
```bash
cp config/connectors.example.json config/connectors.json
```
Then open `connectors.json` and fill in each platform's keys.

---

## 1. Amazon SP-API (orders, listings, FBA stock, fees)
1. **Seller Central** → Settings → **Develop Apps** → "Add new app client" — name it e.g. `NutriScale`.
2. Copy the **LWA Client ID** and **Client Secret** → `amazon_sp.client_id / client_secret`.
3. On the same app page, **Authorize** it to get a **Refresh Token** → `amazon_sp.refresh_token`.
4. `marketplace_id` is pre-filled: `A21TJRUUN4KGV` (Amazon India). Put your Seller Central Merchant ID in `seller_id`.
5. Test: `python3 src/sync_service.py --connector amazon_sp --orders-since 2026-10-01T00:00:00Z`

> Apps registered after 2023 do **not** need AWS IAM keys — LWA alone is enough. Old `aws_*` keys in the config are ignored.
> Some data (e.g. Brand Analytics) needs an extra role approval from Amazon — if it is refused you get a clear message, never fake data.

## 2. Amazon Ads API (campaigns, search terms — the Ads agent's input)
1. **advertising.amazon.com** → Access & Settings → **API applications** → create an application (it runs on Login with Amazon).
2. Copy the Client ID/Secret → `amazon_ads.client_id / client_secret`.
3. Authorize your ad account via the authorization URL to get a **Refresh Token** + **Profile ID** → fill them in.
4. Test: `python3 src/sync_service.py --connector amazon_ads_terms --start 2026-10-01 --end 2026-10-07`
5. The system requests the search-term report via Reporting v3 itself (request → status poll → download).

## 3. Flipkart API
1. The Flipkart API is not open to every seller. Request **API Access** via **Seller Hub** → Help/Support, or ask your account manager.
2. Once approved you get an **App ID + App Secret** → `flipkart.app_id / app_secret`.
3. **If it is not approved, that is fine** — the CSV route (#5) works fully for Flipkart: Seller Hub → Reports/Orders → export → upload.

## 4. Unicommerce API
1. **Unicommerce panel** → Settings → Users/API access — create a user for the API (or ask support to enable API access).
2. Find your tenant URL — like the browser address: `https://your-company.unicommerce.com` → `unicommerce.tenant_url`.
3. Put that API user's **username/password** in the config.
4. Test: `python3 src/sync_service.py --connector unicommerce` — facilities and inventory sync.

## 5. CSV route — works TODAY, no approval needed
The easiest way is the dashboard: **Integrations → Upload a report**. The report type is detected automatically,
you see a preview, then press **Import**. The same file is never imported twice.

| What you need | Where to get it | Command-line alternative |
|---|---|---|
| Search Term Report | Ads Console → Measurement & Reporting → Reports → Sponsored Products → Search term | `python3 src/sync_service.py --csv-search-terms report.csv` |
| Campaign Report | Ads Console → Campaign Manager → Export | `python3 src/sync_service.py --csv-campaigns report.csv` |
| Orders | Seller Central → Orders → Order Reports / Business Reports | `python3 src/sync_service.py --csv-orders orders.csv` |
| Stock sheet | Unicommerce → Inventory export, or your own sheet (sku, quantity columns) | `python3 src/sync_service.py --csv-inventory stock.csv` |
| Flipkart orders | Seller Hub → Orders → Export | `python3 src/sync_service.py --csv-orders fk.csv --platform Flipkart` |
| Brand Analytics (SQP/SCP) | Seller Central → Brand Analytics → Search Query Performance | Upload, or drop it in `data/brand_analytics_inbox/` (auto-imported daily at 06:45) |

## 6. Connected — what next?
1. Start the backend (`python3 backend/app.py`) and open `http://localhost:8765`.
2. The dashboard now shows **real numbers** from your own records.
3. Sync runs daily by itself (scheduler: data sync at 06:30) — nothing to do by hand.
4. If anything looks wrong, press the **Kill Switch** first — then investigate.

## Security
- Keep `config/connectors.json` **gitignored** and never send it to anyone — there is no need to paste keys into any chat; the system reads them from the file.
- To rotate keys, put the new ones in the file and revoke the old ones on the platform.
