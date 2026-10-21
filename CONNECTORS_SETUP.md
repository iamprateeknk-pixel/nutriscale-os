# Connectors Setup Guide — tum khud connect karoge (15–30 min per platform)
**Niyam: apni keys kabhi chat/WhatsApp/GitHub par mat bhejna.** Keys sirf apne computer ki `config/connectors.json` file me bhari jayengi.

## Pehle check karo kya taiyaar hai
```
cd DryFruit_Ecommerce_Growth_OS
python3 src/sync_service.py --status
```
Jo connector `✔ CONFIGURED` dikhe woh taiyaar; baaki ke liye neeche ke steps.

Config file banao:
```
cp config/connectors.example.json config/connectors.json
```
Phir connectors.json ko kholkar har platform ki keys bharo.

---

## 1. Amazon SP-API (Orders, Listings, FBA Stock)
1. **Seller Central** → Settings → **Develop Apps** → "Add new app client" — app ka naam `GrowthOS` rakho.
2. Wahan se **LWA Client ID** aur **Client Secret** milega → config me `amazon_sp.client_id / client_secret`.
3. Usi app page par **"Authorize"** karke **Refresh Token** lo → `amazon_sp.refresh_token`.
4. **AWS IAM** (console.aws.amazon.com) → Users → ek user banao sirf is kaam ke liye → **Access Key + Secret Key** banao → `aws_access_key / aws_secret_key`.
   (SP-API har request ko AWS sign mangta hai — signer system me bana hua hai.)
5. `marketplace_id` pehle se bhara hai: `A21TJRUUN4KGV` (Amazon India). `seller_id` apna Seller Central ka Merchant ID daalo.
6. Test: `python3 src/sync_service.py --connector amazon_sp --orders-since 2026-10-01T00:00:00Z`

> Note: Kuch data (brand analytics type) ke liye Amazon alag role ki manzuri mangta hai — application reject ho to message aayega, system jhootha data nahi dega.

## 2. Amazon Ads API (Campaigns, Search Terms — A06 ka khana)
1. **advertising.amazon.com** → Access & Settings → **API applications** → naya application (Login with Amazon par banta hai).
2. Client ID/Secret milega → `amazon_ads.client_id / client_secret`.
3. Authorization URL se apne ad account ko authorize karke **Refresh Token** + **Profile ID** lo → config me bharo.
4. Test: `python3 src/sync_service.py --connector amazon_ads`
5. Search-term report ke liye system khud Reporting v3 se report mangwayega (request → status → download flow code me hai).

## 3. Flipkart API
1. Flipkart API har seller ko khula nahi milta. **Seller Hub** → Help/Support se **"API Access"** ka anurodh karo, ya apne account manager se bolo.
2. Manzuri mile to **App ID + App Secret** milega → `flipkart.app_id / app_secret`.
3. **Manzoori na mile to koi baat nahi** — CSV rasta (neeche #5) Flipkart par poori tarah chalega: Seller Hub → Reports/Orders se export → import.

## 4. Unicommerce API
1. **Unicommerce panel** → Settings → Users/API access — API ke liye ek user banao (ya support se API enable karwayo).
2. Apna tenant URL dekho — browser ke address jaisa: `https://tumhari-company.unicommerce.com` → `unicommerce.tenant_url`.
3. Us API user ka **username/password** → config me bharo.
4. Test: `python3 src/sync_service.py --connector unicommerce` — facilities aur inventory sync ho jayega.

## 5. CSV Rasta — AAJ se chalega, kisi manzuri ka intezaar nahi
| Kya chahiye | Kahan se milega | Import command |
|---|---|---|
| Search Term Report | Ads Console → Measurement & Reporting → Reports → Sponsored Products → Search Term | `python3 src/sync_service.py --csv-search-terms report.csv` |
| Campaign Report | Ads Console → Campaign Manager → Export | `python3 src/sync_service.py --csv-campaigns report.csv` |
| Orders | Seller Central → Orders → Order Reports / Business Reports | `python3 src/sync_service.py --csv-orders orders.csv` |
| Stock Sheet | Unicommerce → Inventory export, ya apni sheet (sku, quantity columns) | `python3 src/sync_service.py --csv-inventory stock.csv` |
| Flipkart Orders | Seller Hub → Orders → Export | `python3 src/sync_service.py --csv-orders fk.csv --platform Flipkart` |

## 6. Connect ho gaya — phir kya?
1. `python3 backend/app.py` chalao → browser me `dashboard/index.html` kholo.
2. Dashboard ab **🟢 LIVE** dikhayega aur saare numbers tumhare asal records se honge.
3. Sync roz khud chalega (Scheduler: subah 6:30 data sync) — tumhe roz kuch nahi karna.
4. Kuch galat lage to pehle **Kill Switch** — phir baat karenge.

## Suraksha
- `config/connectors.json` ko **gitignore** me rakho, kisi ko mat bhejo — mujhe (Muse ko) bhi chat me keys bhejne ki zaroorat nahi; system file se khud padh lega.
- Keys badalni hon to file me nayi daal do; purani ko platform se revoke kar do.
