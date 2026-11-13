"""Marketplace Knowledge Base (V23) — listing + keyword ke niyam, web research se, SOURCE ke saath.

Imaandaari ke niyam (is file ki reedh):
- Har niyam ke saath `sources` (URL), `checked_on` aur `status` hai:
    OFFICIAL      = Amazon/Flipkart/FSSAI ke apne page ya announcement se
    MULTI_SOURCE  = 3+ swatantra seller-guides ek hi baat kahte hain, official page login ke peeche hai
    SINGLE_SOURCE = ek hi guide ne kaha — disha hai, pakka niyam nahi
    HEURISTIC     = hamara apna tajurba/anuman — sirf apne data se pakka hoga
- `reliability` (0-1) self-learning ka PRIOR hai. Asal nateeje (outcomes) isse upar/neeche le jaate hain —
  agent_brain.py dekho. Sirf padh lene se koi niyam 'sach' nahi banta.
- Amazon/Flipkart apna ranking formula publish nahi karte. Ranking ke baare me jo bhi likha hai woh
  disha-suchak hai, formula ka dawa nahi.
- Research date: 11 Nov 2026. Niyam badalte hain — `checked_on` purana ho to dobara parkho
  (stale_rules() yahi batata hai).
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
       "27 Jul 2026 se media ko chhod har category me title 75 akshar (spaces sahit) ya kam. Lamba title Amazon ka AI "
       "dheere-dheere khud badal deta hai — listing live rehti hai, par shabd tumhare haath se nikal jaate hain.",
       "OFFICIAL", 0.95, ["amz_title_jul26", "amz_title_jul26_in", "salesduo_75"], value={"max_chars": 75},
       action="Title khud 75 ke andar likho — sabse zaroori keyword + product + grade + weight; baaki Item Highlights/bullets me"),
    _k("AMZ-T-02", "Amazon", "title", ["A04"],
       "Naya field 'Item Highlights' — 125 akshar tak, material/upyog jaisi tulna ki baatein. Sirf tab milta hai jab title <=75 ho.",
       "MULTI_SOURCE", 0.85, ["amz_title_jul26", "salesduo_75", "amz_title_jul26_in"], value={"max_chars": 125},
       action="Use-case (gifting, daily snacking, baking) aur pack/grade ke tathya yahan; search-weight abhi saaf nahi, isliye hero keyword title me hi rakho"),
    _k("AMZ-T-03", "Amazon", "title", ["A04"],
       "Ek shabd title me 2 baar se zyada nahi (a/an/the/and/for/with jaise chhote shabd chhod kar). Plural/doosre roop bhi "
       "dohraav gine jaate hain (almond/almonds).",
       "OFFICIAL", 0.9, ["amz_title_jan25", "sel_title_jan25", "m4e_repeat"], value={"max_repeat": 2},
       action="'Almonds Badam Almond' jaisa stuffing hatao — ek roop English, ek Hinglish kaafi hai"),
    _k("AMZ-T-04", "Amazon", "title", ["A04"],
       "Title me non-brand special characters mana: ! $ ? _ { } ^ ¬ ¦; ~ # < > * sirf naap/style-number me. "
       "Pipe | aur dash - chalte hain. Brand ke naam ka hissa ho to chhoot.",
       "MULTI_SOURCE", 0.8, ["amz_title_jan25", "sel_title_jan25", "m4e_repeat"],
       value={"banned": list("!$?_{}^¬¦"), "restricted": list("~#<>*")}),
    _k("AMZ-T-05", "Amazon", "title", ["A04", "A03"],
       "Title ab search-matching field hai, prachaar ka nahi: brand + product type + mukhya fark (grade/variety) + size/weight. "
       "'Best', 'No.1', 'sale', 'offer' jaise shabd title me nahi.",
       "MULTI_SOURCE", 0.8, ["amz_title_jul26_in", "salesduo_75", "fk_42signals"]),
    # ---------------- AMAZON: BULLETS ----------------
    _k("AMZ-B-01", "Amazon", "bullets", ["A04"],
       "Bullets me emoji aur ™ ® © jaise symbols mana (Aug 2024 se); niyam todne wale bullets Amazon khud edit/chhupa sakta hai.",
       "MULTI_SOURCE", 0.8, ["bullets_emoji", "bullets_rules"]),
    _k("AMZ-B-02", "Amazon", "bullets", ["A04"],
       "Guarantee/refund vaade ('full refund', 'pasand na aaye to wapas'), company contact, website link bullets me mana.",
       "MULTI_SOURCE", 0.75, ["bullets_rules", "bullets_emoji"]),
    _k("AMZ-B-03", "Amazon", "bullets", ["A04"],
       "5 bullets; seller account par lambai ~500 tak dikhti hai, par mobile par pehle ~250 akshar hi dikhte hain — "
       "fayda shuru me likho. Bullet ke ant me poorn-viram na lagana aam salah hai.",
       "SINGLE_SOURCE", 0.6, ["bullets_emoji", "backend_bytes"], value={"count": 5, "soft_max": 255, "hard_max": 500}),
    # ---------------- AMAZON: BACKEND SEARCH TERMS ----------------
    _k("AMZ-K-01", "Amazon", "backend", ["A03", "A04"],
       "Amazon.in backend 'search terms' ki seema 200 BYTES (akshar nahi). Hindi/Devanagari ka ek akshar 3 byte leta hai. "
       "Seema paar = field poora ya aanshik roop se index nahi hota.",
       "MULTI_SOURCE", 0.85, ["backend_200", "backend_bytes", "backend_in_forum"], value={"max_bytes": 200}),
    _k("AMZ-K-02", "Amazon", "backend", ["A03"],
       "Backend me shabd spaces se alag karo (comma nahi), title/bullets me pehle se maujood shabd dohrao mat, "
       "competitor brand ka naam kabhi nahi, ASIN nahi, 'best/cheap/new' jaise subjective/temporary shabd nahi.",
       "MULTI_SOURCE", 0.8, ["backend_bp", "backend_200", "backend_bytes"]),
    _k("AMZ-K-03", "Amazon", "backend", ["A03"],
       "Synonyms aur doosri bhasha ke shabd (badam, kaju, kishmish, akhrot, anjeer) backend ki sabse achhi jagah hain. "
       "Galat spelling daalne ki zaroorat nahi — Amazon khud sambhalta hai.",
       "MULTI_SOURCE", 0.75, ["backend_bp", "backend_200"]),
    # ---------------- AMAZON: IMAGES ----------------
    _k("AMZ-I-01", "Amazon", "images", ["A05", "A04"],
       "Main image: shuddh safed background (RGB 255,255,255), product frame ka ~85% bhare, koi text/logo/watermark/props nahi. "
       "Off-white (#FAFAFA) bhi automated check me fail hota hai.",
       "MULTI_SOURCE", 0.85, ["img_main", "img_main2"]),
    _k("AMZ-I-02", "Amazon", "images", ["A05"],
       "Lambi taraf kam se kam 1000px (zoom ke liye 2000px salah). 6-7 images: pack-front, dana close-up (size proof), "
       "nutrition panel, use-case, pack sizes, trust (FSSAI/pack date).",
       "MULTI_SOURCE", 0.8, ["img_main", "img_main2"], value={"min_px": 1000, "zoom_px": 2000, "target_count": 7}),
    # ---------------- AMAZON: SEMANTIC / AI SEARCH ----------------
    _k("AMZ-S-01", "Amazon", "semantic", ["A04", "A03"],
       "COSMO (Amazon ka common-sense knowledge system, SIGMOD 2024) kharidaar ke IRADE (upyog, mauka, kiske liye) ko product "
       "se jodta hai. Structured attributes poore bharna aur use-case saaf likhna zaroori — Rufus se seedha jod Amazon ne pakka nahi kiya.",
       "SINGLE_SOURCE", 0.6, ["cosmo", "rufus"],
       action="Attributes (variety, grade, pack size, diet type, storage) 100% bharo; bullets me 'kiske liye/kab' ke saaf jawab"),
    _k("AMZ-S-02", "Amazon", "semantic", ["A04", "A08"],
       "AI shopping assistant reviews aur Q&A bhi padhta hai — jo sawal baar-baar aate hain unke jawab listing me hone chahiye.",
       "SINGLE_SOURCE", 0.55, ["rufus"]),
    # ---------------- AMAZON: KEYWORD RESEARCH (SQP) ----------------
    _k("AMZ-Q-01", "Amazon", "keyword_research", ["A03", "A06"],
       "Search Query Performance (Brand Analytics, Brand Registry chahiye) har query par tumhara impression/click/cart/purchase "
       "SHARE deta hai. Funnel ki jis seedhi par share girta hai, wahi problem hai.",
       "MULTI_SOURCE", 0.85, ["sqp_merchantspring", "sqp_intentwise", "sqp_perpetua"]),
    _k("AMZ-Q-02", "Amazon", "keyword_research", ["A03", "A04"],
       "Impression share kam = relevance/dikhne ki kami (keyword title/backend me nahi ya ads band). Impression theek par "
       "click share kam = search-tile ki kami (main image, title, price, reviews, badge). Click theek par purchase share kam = "
       "offer/page ki kami (price, A+, reviews, delivery).",
       "MULTI_SOURCE", 0.8, ["sqp_intentwise", "sqp_merchantspring", "sqp_perpetua"]),
    _k("AMZ-Q-03", "Amazon", "keyword_research", ["A03", "A06"],
       "Purchase share > impression share aur impression share abhi chhota (<5%) = product convert karta hai par dikhta nahi — "
       "yahi scale karne layak query hai (ads/bid badhao, title/backend me pakka karo). Pehle margin parkho.",
       "MULTI_SOURCE", 0.75, ["sqp_merchantspring", "sqp_perpetua"], value={"low_impr_share": 0.05}),
    # ---------------- FLIPKART ----------------
    _k("FK-T-01", "Flipkart", "title", ["A04"],
       "Flipkart par bhi title sabse bhaari text field hai; shabd dohraane se listing block ho sakti hai. "
       "Brand + product + variant + weight, saaf aur seedha.",
       "MULTI_SOURCE", 0.7, ["fk_42signals", "fk_ecomva", "fk_base"]),
    _k("FK-I-01", "Flipkart", "images", ["A05"],
       "Kam se kam 2, zyada se zyada 8 images; 1000x1000px se chhoti images mobile par theek nahi khulti.",
       "SINGLE_SOURCE", 0.6, ["fk_42signals"], value={"min_count": 2, "max_count": 8, "min_px": 1000}),
    _k("FK-R-01", "Flipkart", "ranking", ["A04", "A07"],
       "Flipkart ranking product-data ki quality + asal kharidaar vyavhaar (conversion, reviews, seller performance) par "
       "chalti hai; suppressed listing ki koi rank nahi. Formula publish nahi hai.",
       "MULTI_SOURCE", 0.65, ["fk_42signals", "fk_ecomva", "fk_base"]),
    # ---------------- FSSAI (India, sab platforms) ----------------
    _k("FS-C-01", "ALL", "compliance", ["A04", "A09"],
       "FSSAI Advertising & Claims Regulations 2018 (1 Jul 2019 se laagu): bimari rokne/theek karne ke dawe mana; e-commerce "
       "platform bhi 'marketer' ke roop me zimmedar; deceptive claim FSS Act ki dhara 53 ke tahat dandneeya.",
       "OFFICIAL", 0.95, ["fssai_claims_2018", "fssai_misleading", "fssai_digest"]),
    _k("FS-C-02", "ALL", "compliance", ["A04", "A09"],
       "'Natural', 'fresh', 'original', 'traditional', 'authentic' jaise shabd sharton ke saath hi chalte hain "
       "(jaise 'natural food' nahi, 'made from natural ingredients' composite food ke liye). Bina shart poori kiye mat likho.",
       "OFFICIAL", 0.85, ["fssai_natural_fresh", "fssai_digest"],
       value={"conditional_words": ["natural", "fresh", "original", "traditional", "authentic", "pure", "genuine", "real"]}),
    # ---------------- AMAZON: ADS (V24) ----------------
    _k("AMZ-A-01", "Amazon", "ads", ["A06"],
       "Campaign ka ek hi KAAM ho: Auto (khoj), Broad/Phrase (khoj), Exact (kamai), Product targeting (competitor ASIN), Brand-defense. "
       "Exact, phrase, broad aur auto ek hi campaign/budget me hon to tay nahi kar sakte ki paisa kis par jaaye.",
       "MULTI_SOURCE", 0.8, ["ppc_jobs", "ppc_sellersprite", "ppc_channable"],
       action="Har SKU ke liye alag Auto + Exact campaign; jeetne wale terms Exact me, wahi term Auto/Broad me negative"),
    _k("AMZ-A-02", "Amazon", "ads", ["A06", "A03"],
       "Harvest chakra: Auto 2-4 hafte chalao → jo search term orders de (2+), use Exact campaign me daalo aur Auto me "
       "negative exact karo (dono jagah apni hi bid se ladai na ho).",
       "MULTI_SOURCE", 0.8, ["ppc_novadata", "ppc_sellersprite", "ppc_channable"], value={"discovery_weeks": [2, 4], "harvest_min_orders": 2}),
    _k("AMZ-A-03", "Amazon", "ads", ["A06"],
       "Search Term Report har hafte dekho; kharch ho raha hai par bikri nahi aur irada galat hai to turant negative. "
       "Shuruaat me manual campaign me 5-10 hi bahut relevant keywords.",
       "MULTI_SOURCE", 0.8, ["ppc_novadata", "ppc_channable", "ppc_sellersprite"], value={"review_cadence_days": 7, "seed_keywords": [5, 10]}),
    _k("AMZ-A-04", "Amazon", "ads", ["A06", "A07"],
       "Break-even ACOS = ads se pehle ka munafa ÷ selling price. ACOS isse upar = har ad-bikri par ghaata. "
       "Target ACOS = break-even − chaha gaya net margin. Grocery me margin patla hai, isliye break-even ACOS neeche hota hai.",
       "MULTI_SOURCE", 0.9, ["acos_sellerboard", "acos_evanik", "acos_eightx", "acos_cm"],
       action="Har SKU ka break-even ACOS cost + fee se nikalo; bid wahi se tay karo, category ausat se nahi"),
    _k("AMZ-A-05", "Amazon", "ads", ["A06", "A01"],
       "Launch par rank/hissa jeetne ke liye ACOS kuch samay break-even se upar chal sakta hai — par TACOS (kul ad kharch ÷ kul bikri) "
       "par nazar rakho; TACOS girna = organic bikri badh rahi hai (flywheel chal raha hai).",
       "MULTI_SOURCE", 0.75, ["acos_eightx", "acos_sellerboard", "acos_evanik"]),
    _k("AMZ-A-06", "Amazon", "ads", ["A06"],
       "Top-of-search placement par bid +50-100% aam shuruaat hai — par yeh ek hi source ki salah hai; apne placement report se "
       "ACOS dekh kar hi badhao.", "SINGLE_SOURCE", 0.5, ["ppc_novadata"], value={"tos_bid_adj_pct": [50, 100]}),
    # ---------------- AMAZON: REVIEWS / CONTENT (V24) ----------------
    _k("AMZ-R-01", "Amazon", "reviews", ["A08"],
       "Amazon Vine: Brand Registry + Professional account, product par 30 se kam reviews, FBA offer — tab Vine reviewers se "
       "shuruaati reviews. Fees/India me uplabdhta Seller Central par khud dekho (sources me matbhed).",
       "MULTI_SOURCE", 0.7, ["vine_myamazonguy", "vine_sellerlabs", "vine_shulex"], value={"max_reviews": 30}),
    _k("AMZ-R-02", "Amazon", "reviews", ["A08", "A09"],
       "Review ke badle muft product/paisa/discount, sirf khush grahak se review maangna, ya rating ke hisaab se follow-up — "
       "Amazon policy ke khilaf (account suspend ho sakta hai). 'Request a Review' button aur Vine hi surakshit raaste hain.",
       "HEURISTIC", 0.85, [], action="Review agent sirf Request-a-Review aur Vine ki salah dega; incentive wali koi yojana kabhi nahi"),
    _k("AMZ-C-01", "Amazon", "a_plus", ["A04", "A05"],
       "A+ Content (Brand Registry): Amazon ke hawale se Basic A+ se 'up to 8%' aur Premium A+ se 'up to 20%' bikri-badhat batai "
       "jaati hai (blogs se, Amazon ka mool page nahi mila). Comparison chart (apne pack-sizes/variants) sabse kaam ka module mana jaata hai.",
       "MULTI_SOURCE", 0.65, ["aplus_neato", "aplus_estore", "aplus_premium"], value={"basic_lift_pct": 8, "premium_lift_pct": 20},
       action="A+ me: grade/size ka close-up, origin, nutrition table, pack-size comparison chart, storage tips — dawe sirf saboot wale"),
    # ---------------- INDIA: SALE EVENTS (V24) ----------------
    _k("IN-E-01", "Amazon", "events", ["A01", "A06", "A07"],
       "Bade sale (Great Indian Festival) ke liye Amazon khud kehta hai: stock taiyaar, seller coupons, Sale Event Planner se deal "
       "opt-in. Agencies: FBA stock sale se 15-20 din pehle pahunche; listing/coupon/ads ~7 din pehle taiyaar.",
       "MULTI_SOURCE", 0.8, ["gif_official", "gif_forum", "gif_fibre2fashion", "gif_gonukkad"],
       value={"fba_lead_days": [15, 20], "ready_lead_days": 7}),
    _k("IN-E-02", "Amazon", "events", ["A07", "A06"],
       "Deal ke prakar: roz ke liye green coupon; Lightning Deal jaldi zyada units (100+) nikaalne ke liye; sale ke baad bacha stock "
       "clearance/removal. Deal ka discount margin ke andar hi — break-even ACOS ke saath milakar dekho.",
       "SINGLE_SOURCE", 0.6, ["gif_gonukkad", "gif_official"]),
    # ---------------- INDIA: MARKET (V24) ----------------
    _k("IN-M-01", "ALL", "market", ["A01"],
       "India dry fruits bazaar ~USD 2.2 billion (2025), anumaan 6-10% saalana badhat (research firms me matbhed); online "
       "(Amazon/Flipkart) ka hissa tezi se badh raha hai; gifting alag bada segment hai.",
       "MULTI_SOURCE", 0.6, ["mkt_credence", "mkt_bonafide", "mkt_gifting"], value={"size_usd_bn_2025": 2.23}),
    _k("IN-Q-01", "ALL", "channels", ["A01", "A07"],
       "Quick commerce (Blinkit, Zepto, Instamart) kai FMCG companies ki online bikri ka sabse bada channel ban gaya hai "
       "(kuch ke liye 58-75%); festive season me dry fruits top bikne wali shreniyon me. Amazon ke saath yeh channel bhi parkho.",
       "MULTI_SOURCE", 0.65, ["qc_afaqs", "qc_thirdeyesight", "qc_fynd"],
       action="Q-commerce ke liye chhote pack (100-250g) aur gift box; daam Amazon se takraaye nahi (channel conflict)"),
    # ---------------- FLIPKART ADS (V24) ----------------
    _k("FK-A-01", "Flipkart", "ads", ["A06"],
       "Flipkart PLA (Product Listing Ads) CPC par chalte hain; PLA me sirf KUL budget hota hai (daily nahi) — kharch ki raftaar "
       "khud dekhni padti hai. Shuruaat PLA se, phir Brand Ads.",
       "MULTI_SOURCE", 0.7, ["fk_ads_paxcom", "fk_ads_gonukkad", "fk_ads_swc"]),
    _k("FK-A-02", "Flipkart", "ads", ["A06", "A04"],
       "Flipkart khud kehta hai ads tabhi achhe chalte hain jab listing (images, price, stock) theek ho; keyword targeting sirf "
       "search page par. Na chalne wale keywords hatao; 'Smart ROI' campaign target ROAS par khud bid karta hai.",
       "MULTI_SOURCE", 0.65, ["fk_ads_gonukkad", "fk_ads_paxcom", "fk_ads_swc"]),
    # ---------------- HAMARA TAJURBA (HEURISTIC — data se pakka hoga) ----------------
    _k("NS-P-01", "ALL", "compliance", ["A04", "A09"],
       "Listing ka har saboot-maangne wala tathya (nitrogen flush, organic, FSSAI licence, origin, grade, lab-tested, no added sugar) "
       "tabhi copy me jaaye jab uska saboot fact registry me darj ho — warna approve/publish ruk jaata hai.",
       "HEURISTIC", 0.95, [], action="Pehle saboot darj karo (certificate/lab report/invoice), phir copy me dawa likho"),
    _k("NS-H-01", "Amazon", "keyword_research", ["A03"],
       "Dry fruits me kharidaar Hinglish/Hindi (badam, kaju, kishmish) aur English dono me khojte hain — ek roop title me, "
       "doosra backend me.", "HEURISTIC", 0.6, []),
    _k("NS-H-02", "Amazon", "keyword_research", ["A03", "A07"],
       "Pack-size wali queries (500g, 1kg) ka kharidne ka irada zyada hota hai; grade (W240, W320, Mamra) premium kharidaar "
       "ko alag karta hai.", "HEURISTIC", 0.55, []),
    _k("NS-H-03", "Amazon", "seasonality", ["A01", "A06"],
       "Diwali/shaadi ke mausam me 'gift box', 'dry fruits gift' queries uchhalti hain — season se 3-4 hafte pehle listing/ads taiyaar.",
       "HEURISTIC", 0.6, []),
]

# ---------------- Dry-fruit shabdkosh (keyword universe ke beej) ----------------
# Search volume yahan JAAN-BUJH KAR nahi hai — woh sirf licensed provider ya Brand Analytics se aayega.
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
    """Jo niyam 90 din se dobara nahi parkhe gaye — inhe phir se research karo (marketplace niyam badalte rehte hain)."""
    t = today or datetime.date.today()
    return [r["id"] for r in KNOWLEDGE
            if (t - datetime.date.fromisoformat(r["checked_on"])).days > max_age_days]

def seed_knowledge(store) -> dict:
    """Knowledge table me niyam bharo — dobara chalane par dohraav nahi (lesson+agent par pehchan)."""
    added = 0
    for r in KNOWLEDGE:
        for a in r["agents"]:
            lesson = f"[{r['id']}] {r['rule']}"
            if store.db.execute("SELECT 1 FROM knowledge WHERE agent=? AND lesson LIKE ?", (a, f"[{r['id']}]%")).fetchone():
                continue
            src = r["sources"][0] if r["sources"] else "NutriScale heuristic"
            store.add_knowledge(lesson, f"{r['status']} | {src}", r["reliability"], a); added += 1
    return {"added": added, "total_rules": len(KNOWLEDGE)}
