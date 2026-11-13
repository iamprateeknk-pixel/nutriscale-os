"""Marketplace Knowledge Base (V23) — listing and keyword rules from web research, each WITH ITS SOURCE.

Honesty rules (the backbone of this file):
- Every rule carries `sources` (URLs), `checked_on` and a `status`:
    OFFICIAL      = from Amazon/Flipkart/FSSAI's own page or announcement
    MULTI_SOURCE  = 3+ independent seller guides say the same thing; the official page is behind a login
    SINGLE_SOURCE = only one guide says it — a direction, not a firm rule
    HEURISTIC     = our own experience/assumption — only your own data can confirm it
- `reliability` (0-1) is the PRIOR for self-learning. Real outcomes move it up or down —
  see agent_brain.py. Reading a rule does not make it true.
- Amazon/Flipkart do not publish their ranking formulas. Anything written about ranking is
  directional, not a claim about the formula.
- Research date: 11 Nov 2026. Rules change — re-check anything whose `checked_on` is old
  (stale_rules() reports these).
"""
import datetime

CHECKED = "2026-11-11"

_S = {  # source shorthand -> URL
    "amz_title_jul26": "https://sellercentral.amazon.com/seller-forums/discussions/t/145b6d0f-999c-4555-896c-c694bda2e470",
    "amz_title_jul26_in": "https://sellerio.in/blog/amazon-in-75-character-title-limit-july-2026",
    "salesduo_75": "https://salesduo.com/blog/amazon-75-character-title-limit-item-highlights",
    "amz_title_jan25": "https://sellercentral-europe.amazon.com/seller-forums/discussions/t/3781c84d-4778-40fe-9dde-30039a0948f6",
    "sel_title_jan25": "https://searchengineland.com/?p=450485",
    "m4e_repeat": "https://marketing4ecommerce.net/en/amazon-product-title-policy/",
    "backend_200": "https://wisepim.com/guides/amazon-backend-keywords",
    "backend_bytes": "https://keywords.am/blog/amazon-character-limits/",
    "backend_bp": "https://www.sellersprite.com/en/blog/amazon-backend-search-terms",
    "backend_in_forum": "https://sellercentral.amazon.in/seller-forums/discussions/t/9a42d338-56cc-45b8-8bc5-446fd15ba579",
    "bullets_emoji": "https://emplicit.co/checklist-for-optimizing-amazon-bullet-points/",
    "bullets_rules": "https://www.goatconsulting.com/amazon-policy/amazon-product-detail-page-rules-violation-policy-compliance",
    "img_main": "https://www.sellerlabs.com/blog/amazon-product-image-requirements-2026/",
    "img_main2": "https://www.sellersprite.com/en/blog/Amazon-Image-Requirements-Optimization-Tips",
    "cosmo": "https://www.zonguru.com/blog/what-is-amazon-cosmo",
    "rufus": "https://sellermetrics.app/amazon-listing-optimization-for-rufus/",
    "sqp_merchantspring": "https://merchantspring.io/blog/10-powerful-ways-to-use-amazons-search-query-performance-sqp-report-new-api-update",
    "sqp_intentwise": "https://www.intentwise.com/blog/troubleshoot-your-sales-funnel-with-search-query-performance",
    "sqp_perpetua": "https://perpetua.io/blog-amazon-search-query-performance/",
    "fk_42signals": "https://www.42signals.com/blog/flipkart-listings-optimization-guide/",
    "fk_ecomva": "https://www.ecomva.com/wikis/how-to-do-flipkart-seo",
    "fk_base": "https://base.com/en-IN/blog/?p=20951",
    "fssai_claims_2018": "https://www.ecolex.org/details/legislation/food-safety-and-standards-advertising-and-claims-regulations-2018-lex-faoc221217/",
    "fssai_natural_fresh": "https://fssai.gov.in/upload/media/FSSAI_News_Labels_FNB_03_12_2018.pdf",
    "fssai_misleading": "https://fssai.gov.in/upload/media/fssaimisleading.pdf",
    "fssai_digest": "https://fssai-digest.fssai.gov.in/research-and-innovations/claims.php",
    # V24 research (11 Nov 2026)
    "ppc_channable": "https://www.channable.com/blog/amazon-ppc-campaign-structure",
    "ppc_sellersprite": "https://www.sellersprite.com/en/blog/Amazon-PPC-Campaign-Structure-Setup-for-Scalability",
    "ppc_novadata": "https://novadata.io/resources/blog/amazon-sponsored-products",
    "ppc_jobs": "https://www.sellersprite.com/en/blog/amazon-advertising-and-ppc-strategies",
    "acos_sellerboard": "https://blog.sellerboard.com/?p=3500",
    "acos_eightx": "https://eightx.co/blog/average-tacos-benchmarks",
    "acos_evanik": "https://www.evanik.ai/blog/amazon-acos-formula",
    "acos_cm": "https://ecommercefastlane.com/acos-misleading-contribution-margin-framework-amazon/",
    "vine_myamazonguy": "https://myamazonguy.com/reviews/amazon-vine-on-seller-central/",
    "vine_sellerlabs": "https://www.sellerlabs.com/knowledge-base/amazon-vine-is-it-worth-it-for-your-product/",
    "vine_shulex": "https://www.shulex.com/blog/amazon-vine-program",
    "aplus_neato": "https://neato.com/blog/amazon-a-plus-content-for-cpg-brands",
    "aplus_estore": "https://www.estorefactory.com/blog/does-amazon-a-content-really-increase-sales-the-data-and-what-to-do-about-it/",
    "aplus_premium": "https://www.sellersprite.com/en/blog/Is-It-Worth-the-Investment",
    "gif_official": "https://sell.amazon.in/events/great-indian-festival",
    "gif_forum": "https://sellercentral.amazon.com/seller-forums/discussions/t/ab9c3a53-0e40-463f-a349-8789124d9034",
    "gif_fibre2fashion": "https://emerge.fibre2fashion.com/blogs/10896/how-to-prepare-for-big-billion-days-or-great-indian-festival-inventory-coupons-and-ads-playbook",
    "gif_gonukkad": "https://www.gonukkad.com/blog/how-to-win-amazon-great-indian-festival-sale-2026",
    "qc_afaqs": "https://www.afaqs.com/news/mktg/indias-festive-buying-goes-instant-the-rise-of-q-commerce-over-kiranas-10601521",
    "qc_thirdeyesight": "https://www.thirdeyesight.in/quick-commerce-becomes-fmcgs-biggest-online-sales-channel-in-india/",
    "qc_fynd": "https://www.fynd.com/blog/what-instamarts-market-share-drop-reveals-about-quick-commerce",
    "fk_ads_gonukkad": "https://www.gonukkad.com/blog/flipkart-ads-optimization-for-sellers",
    "fk_ads_paxcom": "https://paxcom.ai/blog/how-to-get-started-with-flipkart-ads/",
    "fk_ads_swc": "https://swcybernetics.in/knowledge-base/flipkart-advertising-guide-2026",
    "mkt_credence": "https://www.credenceresearch.com/report/india-dry-fruits-market",
    "mkt_bonafide": "https://www.bonafideresearch.com/product/6212296106/india-dried-fruits-market",
    "mkt_gifting": "https://www.credenceresearch.com/report/india-dry-fruit-gifting-market",
}

def _k(rid, platform, topic, agents, rule, status, reliability, sources, value=None, action=None):
    return {"id": rid, "platform": platform, "topic": topic, "agents": agents, "rule": rule,
            "value": value, "action": action, "status": status, "reliability": reliability,
            "sources": [_S[s] for s in sources], "checked_on": CHECKED}

KNOWLEDGE = [
    # ---------------- AMAZON: TITLE ----------------
    _k("AMZ-T-01", "Amazon", "title", ["A04"],
       "From 27 Jul 2026 titles in every category except media must be 75 characters or fewer (including spaces). Amazon's AI "
       "gradually rewrites longer titles — the listing stays live, but you lose control of the wording.",
       "OFFICIAL", 0.95, ["amz_title_jul26", "amz_title_jul26_in", "salesduo_75"], value={"max_chars": 75},
       action="Write the title yourself within 75 chars — top keyword + product + grade + weight; everything else goes in Item Highlights/bullets"),
    _k("AMZ-T-02", "Amazon", "title", ["A04"],
       "New 'Item Highlights' field — up to 125 characters for comparison details such as material/use. Only available when the title is <=75.",
       "MULTI_SOURCE", 0.85, ["amz_title_jul26", "salesduo_75", "amz_title_jul26_in"], value={"max_chars": 125},
       action="Put use cases (gifting, daily snacking, baking) and pack/grade facts here; its search weight is unclear, so keep the hero keyword in the title"),
    _k("AMZ-T-03", "Amazon", "title", ["A04"],
       "No word may appear more than twice in a title (except short words like a/an/the/and/for/with). Plurals and other "
       "forms count as repeats (almond/almonds).",
       "OFFICIAL", 0.9, ["amz_title_jan25", "sel_title_jan25", "m4e_repeat"], value={"max_repeat": 2},
       action="Remove stuffing like 'Almonds Badam Almond' — one English form and one Hinglish form is enough"),
    _k("AMZ-T-04", "Amazon", "title", ["A04"],
       "Non-brand special characters are banned in titles: ! $ ? _ { } ^ ¬ ¦; ~ # < > * only in measurements/style numbers. "
       "Pipe | and dash - are allowed. Exempt if part of the brand name.",
       "MULTI_SOURCE", 0.8, ["amz_title_jan25", "sel_title_jan25", "m4e_repeat"],
       value={"banned": list("!$?_{}^¬¦"), "restricted": list("~#<>*")}),
    _k("AMZ-T-05", "Amazon", "title", ["A04", "A03"],
       "The title is now a search-matching field, not marketing: brand + product type + key differentiator (grade/variety) + size/weight. "
       "No words like 'Best', 'No.1', 'sale', 'offer' in the title.",
       "MULTI_SOURCE", 0.8, ["amz_title_jul26_in", "salesduo_75", "fk_42signals"]),
    # ---------------- AMAZON: BULLETS ----------------
    _k("AMZ-B-01", "Amazon", "bullets", ["A04"],
       "Emojis and symbols like ™ ® © are banned in bullets (since Aug 2024); Amazon may edit or hide bullets that break the rules.",
       "MULTI_SOURCE", 0.8, ["bullets_emoji", "bullets_rules"]),
    _k("AMZ-B-02", "Amazon", "bullets", ["A04"],
       "Guarantee/refund promises ('full refund', 'send it back if not satisfied'), company contact details and website links are banned in bullets.",
       "MULTI_SOURCE", 0.75, ["bullets_rules", "bullets_emoji"]),
    _k("AMZ-B-03", "Amazon", "bullets", ["A04"],
       "5 bullets; seller accounts allow ~500 characters, but mobile shows only the first ~250 — "
       "lead with the benefit. Common advice is to skip the full stop at the end of a bullet.",
       "SINGLE_SOURCE", 0.6, ["bullets_emoji", "backend_bytes"], value={"count": 5, "soft_max": 255, "hard_max": 500}),
    # ---------------- AMAZON: BACKEND SEARCH TERMS ----------------
    _k("AMZ-K-01", "Amazon", "backend", ["A03", "A04"],
       "The Amazon.in backend 'search terms' limit is 200 BYTES (not characters). One Hindi/Devanagari character takes 3 bytes. "
       "Over the limit = the field is not indexed, fully or partly.",
       "MULTI_SOURCE", 0.85, ["backend_200", "backend_bytes", "backend_in_forum"], value={"max_bytes": 200}),
    _k("AMZ-K-02", "Amazon", "backend", ["A03"],
       "Separate backend words with spaces (not commas), do not repeat words already in the title/bullets, "
       "never use competitor brand names or ASINs, and no subjective/temporary words like 'best/cheap/new'.",
       "MULTI_SOURCE", 0.8, ["backend_bp", "backend_200", "backend_bytes"]),
    _k("AMZ-K-03", "Amazon", "backend", ["A03"],
       "Synonyms and other-language words (badam, kaju, kishmish, akhrot, anjeer) belong in the backend. "
       "No need to add misspellings — Amazon handles those itself.",
       "MULTI_SOURCE", 0.75, ["backend_bp", "backend_200"]),
    # ---------------- AMAZON: IMAGES ----------------
    _k("AMZ-I-01", "Amazon", "images", ["A05", "A04"],
       "Main image: pure white background (RGB 255,255,255), product fills ~85% of the frame, no text/logo/watermark/props. "
       "Even off-white (#FAFAFA) fails the automated check.",
       "MULTI_SOURCE", 0.85, ["img_main", "img_main2"]),
    _k("AMZ-I-02", "Amazon", "images", ["A05"],
       "At least 1000px on the longest side (2000px recommended for zoom). 6-7 images: pack front, kernel close-up (size proof), "
       "nutrition panel, use case, pack sizes, trust (FSSAI/pack date).",
       "MULTI_SOURCE", 0.8, ["img_main", "img_main2"], value={"min_px": 1000, "zoom_px": 2000, "target_count": 7}),
    # ---------------- AMAZON: SEMANTIC / AI SEARCH ----------------
    _k("AMZ-S-01", "Amazon", "semantic", ["A04", "A03"],
       "COSMO (Amazon's common-sense knowledge system, SIGMOD 2024) links shopper INTENT (use, occasion, who it is for) to products. "
       "Fill structured attributes completely and state use cases clearly — Amazon has not confirmed a direct link to Rufus.",
       "SINGLE_SOURCE", 0.6, ["cosmo", "rufus"],
       action="Fill 100% of attributes (variety, grade, pack size, diet type, storage); bullets clearly answer 'who is it for / when'"),
    _k("AMZ-S-02", "Amazon", "semantic", ["A04", "A08"],
       "The AI shopping assistant also reads reviews and Q&A — answers to frequently asked questions should be in the listing.",
       "SINGLE_SOURCE", 0.55, ["rufus"]),
    # ---------------- AMAZON: KEYWORD RESEARCH (SQP) ----------------
    _k("AMZ-Q-01", "Amazon", "keyword_research", ["A03", "A06"],
       "Search Query Performance (Brand Analytics, needs Brand Registry) gives your impression/click/cart/purchase SHARE "
       "for every query. The funnel step where your share drops is the problem.",
       "MULTI_SOURCE", 0.85, ["sqp_merchantspring", "sqp_intentwise", "sqp_perpetua"]),
    _k("AMZ-Q-02", "Amazon", "keyword_research", ["A03", "A04"],
       "Low impression share = relevance/visibility gap (keyword missing from title/backend, or ads off). Good impressions but "
       "low click share = search-tile gap (main image, title, price, reviews, badge). Good clicks but low purchase share = "
       "offer/page gap (price, A+, reviews, delivery).",
       "MULTI_SOURCE", 0.8, ["sqp_intentwise", "sqp_merchantspring", "sqp_perpetua"]),
    _k("AMZ-Q-03", "Amazon", "keyword_research", ["A03", "A06"],
       "Purchase share > impression share while impression share is still small (<5%) = the product converts but is not seen — "
       "this is the query worth scaling (raise ads/bids, lock it into title/backend). Check margin first.",
       "MULTI_SOURCE", 0.75, ["sqp_merchantspring", "sqp_perpetua"], value={"low_impr_share": 0.05}),
    # ---------------- FLIPKART ----------------
    _k("FK-T-01", "Flipkart", "title", ["A04"],
       "On Flipkart too the title is the most heavily weighted text field; repeating words can get a listing blocked. "
       "Brand + product + variant + weight, clean and simple.",
       "MULTI_SOURCE", 0.7, ["fk_42signals", "fk_ecomva", "fk_base"]),
    _k("FK-I-01", "Flipkart", "images", ["A05"],
       "At least 2 and at most 8 images; images smaller than 1000x1000px do not open properly on mobile.",
       "SINGLE_SOURCE", 0.6, ["fk_42signals"], value={"min_count": 2, "max_count": 8, "min_px": 1000}),
    _k("FK-R-01", "Flipkart", "ranking", ["A04", "A07"],
       "Flipkart ranking runs on product-data quality + real shopper behaviour (conversion, reviews, seller performance); "
       "a suppressed listing has no rank. The formula is not published.",
       "MULTI_SOURCE", 0.65, ["fk_42signals", "fk_ecomva", "fk_base"]),
    # ---------------- FSSAI (India, sab platforms) ----------------
    _k("FS-C-01", "ALL", "compliance", ["A04", "A09"],
       "FSSAI Advertising & Claims Regulations 2018 (in force from 1 Jul 2019): claims to prevent/cure disease are banned; e-commerce "
       "platforms are also liable as 'marketers'; deceptive claims are punishable under Section 53 of the FSS Act.",
       "OFFICIAL", 0.95, ["fssai_claims_2018", "fssai_misleading", "fssai_digest"]),
    _k("FS-C-02", "ALL", "compliance", ["A04", "A09"],
       "Words like 'natural', 'fresh', 'original', 'traditional', 'authentic' are only allowed under conditions "
       "(e.g. not 'natural food', but 'made from natural ingredients' for composite foods). Do not use them unless the conditions are met.",
       "OFFICIAL", 0.85, ["fssai_natural_fresh", "fssai_digest"],
       value={"conditional_words": ["natural", "fresh", "original", "traditional", "authentic", "pure", "genuine", "real"]}),
    # ---------------- AMAZON: ADS (V24) ----------------
    _k("AMZ-A-01", "Amazon", "ads", ["A06"],
       "Give each campaign ONE job: Auto (discovery), Broad/Phrase (discovery), Exact (earning), Product targeting (competitor ASINs), Brand defense. "
       "If exact, phrase, broad and auto share one campaign/budget you cannot control where the money goes.",
       "MULTI_SOURCE", 0.8, ["ppc_jobs", "ppc_sellersprite", "ppc_channable"],
       action="A separate Auto + Exact campaign per SKU; winning terms go to Exact, and the same term becomes negative in Auto/Broad"),
    _k("AMZ-A-02", "Amazon", "ads", ["A06", "A03"],
       "Harvest cycle: run Auto for 2-4 weeks → move search terms with orders (2+) into an Exact campaign and add them as "
       "negative exact in Auto (so you do not bid against yourself).",
       "MULTI_SOURCE", 0.8, ["ppc_novadata", "ppc_sellersprite", "ppc_channable"], value={"discovery_weeks": [2, 4], "harvest_min_orders": 2}),
    _k("AMZ-A-03", "Amazon", "ads", ["A06"],
       "Review the Search Term Report weekly; if a term spends without sales and has the wrong intent, negate it right away. "
       "Start manual campaigns with only 5-10 highly relevant keywords.",
       "MULTI_SOURCE", 0.8, ["ppc_novadata", "ppc_channable", "ppc_sellersprite"], value={"review_cadence_days": 7, "seed_keywords": [5, 10]}),
    _k("AMZ-A-04", "Amazon", "ads", ["A06", "A07"],
       "Break-even ACOS = profit before ads ÷ selling price. ACOS above it = a loss on every ad sale. "
       "Target ACOS = break-even − desired net margin. Grocery margins are thin, so break-even ACOS is low.",
       "MULTI_SOURCE", 0.9, ["acos_sellerboard", "acos_evanik", "acos_eightx", "acos_cm"],
       action="Calculate break-even ACOS per SKU from cost + fees; set bids from that, not from category averages"),
    _k("AMZ-A-05", "Amazon", "ads", ["A06", "A01"],
       "At launch, ACOS can run above break-even for a while to win rank/share — but watch TACOS (total ad spend ÷ total sales); "
       "falling TACOS = organic sales are growing (the flywheel is working).",
       "MULTI_SOURCE", 0.75, ["acos_eightx", "acos_sellerboard", "acos_evanik"]),
    _k("AMZ-A-06", "Amazon", "ads", ["A06"],
       "+50-100% bid on top-of-search placement is a common starting point — but it comes from a single source; only raise it "
       "after checking ACOS in your own placement report.", "SINGLE_SOURCE", 0.5, ["ppc_novadata"], value={"tos_bid_adj_pct": [50, 100]}),
    # ---------------- AMAZON: REVIEWS / CONTENT (V24) ----------------
    _k("AMZ-R-01", "Amazon", "reviews", ["A08"],
       "Amazon Vine: needs Brand Registry + a Professional account, fewer than 30 reviews on the product and an FBA offer — then Vine "
       "reviewers provide early reviews. Check fees/availability in India in Seller Central yourself (sources disagree).",
       "MULTI_SOURCE", 0.7, ["vine_myamazonguy", "vine_sellerlabs", "vine_shulex"], value={"max_reviews": 30}),
    _k("AMZ-R-02", "Amazon", "reviews", ["A08", "A09"],
       "Free product/money/discounts in exchange for reviews, asking only happy customers for reviews, or rating-based follow-ups — "
       "are against Amazon policy (the account can be suspended). The 'Request a Review' button and Vine are the only safe routes.",
       "HEURISTIC", 0.85, [], action="The review agent only recommends Request-a-Review and Vine; never any incentive scheme"),
    _k("AMZ-C-01", "Amazon", "a_plus", ["A04", "A05"],
       "A+ Content (Brand Registry): blogs citing Amazon report 'up to 8%' sales lift from Basic A+ and 'up to 20%' from Premium A+ "
       "(Amazon's original page was not found). The comparison chart (your own pack sizes/variants) is considered the most useful module.",
       "MULTI_SOURCE", 0.65, ["aplus_neato", "aplus_estore", "aplus_premium"], value={"basic_lift_pct": 8, "premium_lift_pct": 20},
       action="In A+: grade/size close-up, origin, nutrition table, pack-size comparison chart, storage tips — only evidence-backed claims"),
    # ---------------- INDIA: SALE EVENTS (V24) ----------------
    _k("IN-E-01", "Amazon", "events", ["A01", "A06", "A07"],
       "For big sales (Great Indian Festival) Amazon itself says: have stock ready, seller coupons, and opt in to deals via the Sale Event "
       "Planner. Agencies: FBA stock should arrive 15-20 days before the sale; listings/coupons/ads ready ~7 days before.",
       "MULTI_SOURCE", 0.8, ["gif_official", "gif_forum", "gif_fibre2fashion", "gif_gonukkad"],
       value={"fba_lead_days": [15, 20], "ready_lead_days": 7}),
    _k("IN-E-02", "Amazon", "events", ["A07", "A06"],
       "Deal types: green coupons for everyday; Lightning Deals to move many units (100+) fast; leftover stock after the sale goes to "
       "clearance/removal. Keep deal discounts within margin — check them together with break-even ACOS.",
       "SINGLE_SOURCE", 0.6, ["gif_gonukkad", "gif_official"]),
    # ---------------- INDIA: MARKET (V24) ----------------
    _k("IN-M-01", "ALL", "market", ["A01"],
       "India dry fruits market ~USD 2.2 billion (2025), estimated 6-10% annual growth (research firms disagree); the online "
       "share (Amazon/Flipkart) is growing fast; gifting is a separate large segment.",
       "MULTI_SOURCE", 0.6, ["mkt_credence", "mkt_bonafide", "mkt_gifting"], value={"size_usd_bn_2025": 2.23}),
    _k("IN-Q-01", "ALL", "channels", ["A01", "A07"],
       "Quick commerce (Blinkit, Zepto, Instamart) has become the largest online sales channel for many FMCG companies "
       "(58-75% for some); dry fruits are among the top festive-season categories. Evaluate this channel alongside Amazon.",
       "MULTI_SOURCE", 0.65, ["qc_afaqs", "qc_thirdeyesight", "qc_fynd"],
       action="Small packs (100-250g) and gift boxes for q-commerce; keep prices from clashing with Amazon (channel conflict)"),
    # ---------------- FLIPKART ADS (V24) ----------------
    _k("FK-A-01", "Flipkart", "ads", ["A06"],
       "Flipkart PLA (Product Listing Ads) run on CPC; PLA has only a TOTAL budget (no daily cap) — you must watch the spend pace "
       "yourself. Start with PLA, then Brand Ads.",
       "MULTI_SOURCE", 0.7, ["fk_ads_paxcom", "fk_ads_gonukkad", "fk_ads_swc"]),
    _k("FK-A-02", "Flipkart", "ads", ["A06", "A04"],
       "Flipkart itself says ads work best when the listing (images, price, stock) is in order; keyword targeting only works "
       "on the search page. Remove non-performing keywords; 'Smart ROI' campaigns bid automatically to a target ROAS.",
       "MULTI_SOURCE", 0.65, ["fk_ads_gonukkad", "fk_ads_paxcom", "fk_ads_swc"]),
    # ---------------- OUR EXPERIENCE (HEURISTIC — to be confirmed by data) ----------------
    _k("NS-P-01", "ALL", "compliance", ["A04", "A09"],
       "Every claim that needs proof (nitrogen flush, organic, FSSAI licence, origin, grade, lab-tested, no added sugar) "
       "may only go into copy once its evidence is recorded in the fact registry — otherwise approve/publish is blocked.",
       "HEURISTIC", 0.95, [], action="Record the evidence first (certificate/lab report/invoice), then write the claim into the copy"),
    _k("NS-H-01", "Amazon", "keyword_research", ["A03"],
       "Dry-fruit shoppers search in both Hinglish/Hindi (badam, kaju, kishmish) and English — one form in the title, "
       "the other in the backend.", "HEURISTIC", 0.6, []),
    _k("NS-H-02", "Amazon", "keyword_research", ["A03", "A07"],
       "Pack-size queries (500g, 1kg) show stronger buying intent; grade terms (W240, W320, Mamra) separate out premium shoppers.", "HEURISTIC", 0.55, []),
    _k("NS-H-03", "Amazon", "seasonality", ["A01", "A06"],
       "In the Diwali/wedding season 'gift box' and 'dry fruits gift' queries spike — have listings/ads ready 3-4 weeks before the season.",
       "HEURISTIC", 0.6, []),
]

# ---------------- Dry-fruit vocabulary (seeds for the keyword universe) ----------------
# Search volume is DELIBERATELY absent here — it only comes from a licensed provider or Brand Analytics.
NUT_VOCAB = {
    "almond":    {"hinglish": ["badam", "badaam"], "hindi": ["बादाम"], "grades": ["california", "mamra", "gurbandi", "jumbo"]},
    "cashew":    {"hinglish": ["kaju"], "hindi": ["काजू"], "grades": ["w180", "w210", "w240", "w320", "w400", "splits"]},
    "raisin":    {"hinglish": ["kishmish", "munakka"], "hindi": ["किशमिश"], "grades": ["green", "golden", "black", "afghani", "indian"]},
    "walnut":    {"hinglish": ["akhrot"], "hindi": ["अखरोट"], "grades": ["kashmiri", "chile", "kernels", "inshell"]},
    "pistachio": {"hinglish": ["pista"], "hindi": ["पिस्ता"], "grades": ["iranian", "california", "roasted salted", "kernels"]},
    "fig":       {"hinglish": ["anjeer", "anjir"], "hindi": ["अंजीर"], "grades": ["afghani", "jumbo"]},
    "dates":     {"hinglish": ["khajoor", "khajur"], "hindi": ["खजूर"], "grades": ["medjool", "ajwa", "kimia", "seedless"]},
    "apricot":   {"hinglish": ["khubani"], "hindi": ["खुबानी"], "grades": ["turkish", "dried"]},
}
INTENT_MODIFIERS = {
    "pack": ["250g", "500g", "1kg", "200g", "100g"],
    "use": ["gift box", "gift pack", "daily snacking", "for kids", "for baking", "trail mix"],
    "occasion": ["diwali gift", "wedding gift", "rakhi gift", "corporate gift"],
    "form": ["raw", "roasted", "salted", "unsalted", "plain", "premium"],
    "diet": ["vegan", "gluten free", "high protein"],
}

def rules_for(agent: str = None, platform: str = None, topic: str = None) -> list:
    out = []
    for r in KNOWLEDGE:
        if agent and agent not in r["agents"]: continue
        if platform and r["platform"] not in (platform, "ALL"): continue
        if topic and r["topic"] != topic: continue
        out.append(r)
    return sorted(out, key=lambda r: -r["reliability"])

def rule(rid: str) -> dict:
    for r in KNOWLEDGE:
        if r["id"] == rid: return r
    raise KeyError(rid)

def stale_rules(max_age_days: int = 90, today=None) -> list:
    """Rules not re-checked for 90 days — research them again (marketplace rules keep changing)."""
    t = today or datetime.date.today()
    return [r["id"] for r in KNOWLEDGE
            if (t - datetime.date.fromisoformat(r["checked_on"])).days > max_age_days]

def seed_knowledge(store) -> dict:
    """Load rules into the knowledge table — re-running never duplicates (identified by rule id + agent).
    Existing rows get their text refreshed, so wording changes (e.g. translation) reach existing databases."""
    added = refreshed = 0
    for r in KNOWLEDGE:
        for a in r["agents"]:
            lesson = f"[{r['id']}] {r['rule']}"
            src = r["sources"][0] if r["sources"] else "NutriScale heuristic"
            ex = store.db.execute("SELECT id, lesson FROM knowledge WHERE agent=? AND lesson LIKE ?", (a, f"[{r['id']}]%")).fetchone()
            if ex:
                if ex["lesson"] != lesson:
                    store.db.execute("UPDATE knowledge SET lesson=?, source=?, reliability=? WHERE id=?",
                                     (lesson, f"{r['status']} | {src}", r["reliability"], ex["id"])); refreshed += 1
                continue
            store.add_knowledge(lesson, f"{r['status']} | {src}", r["reliability"], a); added += 1
    store.db.commit()
    return {"added": added, "refreshed": refreshed, "total_rules": len(KNOWLEDGE)}
