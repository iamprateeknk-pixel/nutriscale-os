# Seller Acceptance Report — 2026-10-22

_NutriScale OS ke asal numbers, unke aadhaar ke saath. Marketplace reports se tulna ke liye._

## Amazon
- Revenue (NET): ₹46,069.00 — aadhaar: LEGACY (orders table — purana import)
- Orders: 104 (cancelled alag: 0), lines: 104
- Finance matching (30d): DATA_APARYAPT — checked 0, matched 0, fee-missing 0, mismatch 0 (key: gross-vs-gross + refund-vs-refund, key=(seller_account, order_id) (V20))
- Completeness (30d): ads coverage 0.0%, fee coverage None%
- Reconciliation (30d): orders NET ₹0.00 banam settlements (prorated anumaan ₹0.00, sthiti: NON_FINAL — settlement period khidki se ...)
- Ads spend (period-tagged, 30d): ₹0.00

## Flipkart
- Revenue (NET): ₹0.00 — aadhaar: LEGACY (orders table — purana import)
- Orders: 0 (cancelled alag: 0), lines: 0
- Finance matching (30d): DATA_APARYAPT — checked 0, matched 0, fee-missing 0, mismatch 0 (key: gross-vs-gross + refund-vs-refund, key=(seller_account, order_id) (V20))
- Completeness (30d): ads coverage 0.0%, fee coverage None%
- Reconciliation (30d): orders NET ₹0.00 banam settlements (prorated anumaan ₹0.00, sthiti: NON_FINAL — settlement period khidki se ...)
- Ads spend (period-tagged, 30d): ₹0.00

## Stock
- SKUs with inventory: 0, kul qty: 0

## Capabilities
- Amazon / read_ads: code_ready
- Amazon / read_orders: code_ready
- Amazon / write_ads: not_certified
- Amazon / write_listings: not_certified
- External / keyword_provider: unavailable
- External / rank_provider: unavailable
- Flipkart / read_ads: report_only
- Flipkart / read_orders: code_ready
- Flipkart / write_ads: unavailable
- Flipkart / write_listings: not_certified

## Preflight
- ✘ connector:amazon_sp — 
- ✘ connector:amazon_ads — 
- ✘ connector:flipkart — 
- ✘ connector:unicommerce — 
- ✘ capability:Amazon:write_ads — halat=not_certified — pilot sign-off baki hai
- ✘ capability:Amazon:write_listings — halat=not_certified — pilot sign-off baki hai
- ✘ capability:Flipkart:read_orders — halat=code_ready — pilot sign-off baki hai
- ✔ owner_user — 1 Owner khata maujud
- ✔ kill_switch_off — band hai, theek
- ✔ backup_exists — 1 backup file(s)
- ✔ https_pack — Caddy + prod compose maujud
- ✘ llm_key — LLM key nahi — system rules par chalega (chalega, par AI-copy band)

_Ye report system ke apne DB se bani hai; marketplace ke asal reports se tulna hi acceptance hai._