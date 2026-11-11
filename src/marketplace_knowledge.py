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
    # ---------------- HAMARA TAJURBA (HEURISTIC — data se pakka hoga) ----------------
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
