"""Listing Rules Engine (V23) — marketplace_knowledge ke niyam ko CHALANE-YOGYA jaanch me badalna.

Do kaam:
1. audit_listing(): title / item highlights / bullets / backend / images ki jaanch — har issue ke saath
   rule_id (marketplace_knowledge me source dekho) aur severity:
     BLOCK = policy todta hai (Amazon khud badlega/chhupayega ya FSSAI ka khatra) — publish se pehle theek karo
     WARN  = jokhim ya kamzori
     TIP   = behtar karne ki salah
2. build_*(): niyam ke andar rahkar title (<=75), item highlights (<=125) aur backend (<=200 bytes) banana.
"""
import re, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import marketplace_knowledge as MK

STOP_WORDS = {"a", "an", "the", "and", "or", "for", "with", "of", "in", "on", "to", "by", "&", "|", "-", "x"}
SUBJECTIVE = ["best", "no.1", "no 1", "#1", "number one", "cheapest", "top rated", "sale", "offer", "discount",
              "free", "new arrival", "limited time", "hot deal", "bestseller", "best seller"]
GUARANTEE = [r"full refund", r"money.?back", r"100% guarantee", r"satisfaction guaranteed",
             r"pasand na aaye", r"if not satisfied", r"send it back"]
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF⭐✅]")
LEGAL_SYMBOLS = "™®©"
URL_RE = re.compile(r"(https?://|www\.|\.com\b|\.in\b|@\w+\.)", re.I)

def _stem(w: str) -> str:
    """Plural/roop ko ek ginne ke liye (almonds->almond, cashews->cashew, dates->date)."""
    w = w.lower().strip(".,;:()[]\"'")
    for suf in ("ies",):
        if w.endswith(suf) and len(w) > 4: return w[:-3] + "y"
    if w.endswith("es") and len(w) > 4 and w[-3] in "sxz": return w[:-2]
    if w.endswith("s") and len(w) > 3 and not w.endswith("ss"): return w[:-1]
    return w

def _words(text: str) -> list:
    return [w for w in re.split(r"[\s,/|]+", (text or "").lower()) if w]

def repeated_words(title: str, max_repeat: int = 2) -> dict:
    counts = {}
    for w in _words(title):
        s = _stem(w)
        if not s or s in STOP_WORDS or re.fullmatch(r"[\d.]+(g|kg|ml|gm)?", s): continue
        counts[s] = counts.get(s, 0) + 1
    return {w: c for w, c in counts.items() if c > max_repeat}

def byte_len(s: str) -> int:
    return len((s or "").encode("utf-8"))

def _issue(sev, field, rid, msg, fix=None):
    d = {"severity": sev, "field": field, "rule_id": rid, "message": msg}
    if fix: d["fix"] = fix
    return d

# ---------------- AUDIT ----------------
def audit_title(title: str, platform: str = "Amazon", competitor_brands=()) -> list:
    out, t = [], title or ""
    if platform == "Amazon":
        mx = MK.rule("AMZ-T-01")["value"]["max_chars"]
        if len(t) > mx:
            out.append(_issue("BLOCK", "title", "AMZ-T-01",
                              f"Title {len(t)} akshar ka hai — Amazon seema {mx}. Lamba title Amazon ka AI khud badal dega.",
                              "build_title_amazon() se 75 ke andar banao; baaki baatein Item Highlights me"))
        v = MK.rule("AMZ-T-04")["value"]
        bad = sorted({c for c in t if c in v["banned"]})
        if bad: out.append(_issue("BLOCK", "title", "AMZ-T-04", f"Mana special characters: {' '.join(bad)}"))
        restr = sorted({c for c in t if c in v["restricted"]})
        if restr: out.append(_issue("WARN", "title", "AMZ-T-04", f"{' '.join(restr)} sirf naap/style-number me chalta hai"))
    rep = repeated_words(t)
    if rep:
        out.append(_issue("BLOCK", "title", "AMZ-T-03" if platform == "Amazon" else "FK-T-01",
                          "Shabd 2 se zyada baar (plural bhi gina): " + ", ".join(f"{w}×{c}" for w, c in rep.items()),
                          "Ek roop title me rakho, doosra (Hinglish/synonym) backend me"))
    low = t.lower()
    subj = [w for w in SUBJECTIVE if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", low)]
    if subj: out.append(_issue("WARN", "title", "AMZ-T-05", f"Prachaar/subjective shabd title me: {', '.join(subj)}"))
    for b in competitor_brands:
        if b and b.lower() in low:
            out.append(_issue("BLOCK", "title", "AMZ-K-02", f"Competitor brand '{b}' title me — trademark/policy jokhim"))
    if t and t.isupper(): out.append(_issue("WARN", "title", "AMZ-T-05", "Poora title CAPITAL me — har shabd ka pehla akshar bada rakho"))
    return out

def audit_bullets(bullets: list, platform: str = "Amazon") -> list:
    out, bl = [], [b for b in (bullets or []) if b and b.strip()]
    if len(bl) < 5: out.append(_issue("WARN", "bullets", "AMZ-B-03", f"Sirf {len(bl)} bullets — 5 chahiye"))
    lim = MK.rule("AMZ-B-03")["value"]
    for i, b in enumerate(bl, 1):
        if EMOJI_RE.search(b): out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-01", "Emoji mana hai"))
        if any(c in b for c in LEGAL_SYMBOLS): out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-01", "™ ® © symbols mana hain"))
        if any(re.search(p, b, re.I) for p in GUARANTEE):
            out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-02", "Guarantee/refund ka vaada bullet me mana hai"))
        if URL_RE.search(b): out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-02", "Website/email/contact bullet me mana hai"))
        if len(b) > lim["hard_max"]: out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-03", f"{len(b)} akshar — seema {lim['hard_max']}"))
        elif len(b) > lim["soft_max"]: out.append(_issue("TIP", f"bullet_{i}", "AMZ-B-03",
                                                          f"{len(b)} akshar — mobile par pehle ~{lim['soft_max']} hi dikhte hain, fayda shuru me rakho"))
    return out

def audit_backend(backend: str, title: str = "", bullets=(), competitor_brands=()) -> list:
    out, b = [], backend or ""
    mx = MK.rule("AMZ-K-01")["value"]["max_bytes"]
    n = byte_len(b)
    if not b.strip(): out.append(_issue("WARN", "backend", "AMZ-K-03", "Backend search terms khaali — synonyms/Hinglish yahin jaate hain"))
    if n > mx: out.append(_issue("BLOCK", "backend", "AMZ-K-01", f"{n} bytes — Amazon.in seema {mx} bytes; zyada hua to index nahi hoga",
                                 "pack_backend_terms() se kaato"))
    if "," in b or ";" in b: out.append(_issue("TIP", "backend", "AMZ-K-02", "Comma/semicolon ki jagah sirf space — byte bachenge"))
    seen = {_stem(w) for w in _words(title + " " + " ".join(bullets or []))}
    dup = sorted({w for w in _words(b) if _stem(w) in seen and _stem(w) not in STOP_WORDS})
    if dup: out.append(_issue("TIP", "backend", "AMZ-K-02", f"Ye shabd title/bullets me pehle se hain, byte barbaad: {', '.join(dup[:10])}"))
    if re.search(r"\bb0[0-9a-z]{8}\b", b.lower()): out.append(_issue("BLOCK", "backend", "AMZ-K-02", "ASIN backend me mana hai"))
    for br in competitor_brands:
        if br and re.search(r"(?<!\w)" + re.escape(br.lower()) + r"(?!\w)", b.lower()):
            out.append(_issue("BLOCK", "backend", "AMZ-K-02", f"Competitor brand '{br}' backend me — mana hai"))
    subj = [w for w in SUBJECTIVE if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", b.lower())]
    if subj: out.append(_issue("WARN", "backend", "AMZ-K-02", f"Subjective/temporary shabd: {', '.join(subj)}"))
    return out

def audit_fssai(text: str, verified_conditions=()) -> list:
    """FSSAI: bimari-dawa (claim_checker BLOCK karta hai) + shart-wale shabd (natural/fresh/...)."""
    from claim_checker import check_listing_text
    out = []
    cc = check_listing_text(text)
    for r in cc["blocked_reasons"]: out.append(_issue("BLOCK", "copy", "FS-C-01", r))
    for w in cc["warnings"]: out.append(_issue("WARN", "copy", "FS-C-01", w))
    low = (text or "").lower()
    for w in MK.rule("FS-C-02")["value"]["conditional_words"]:
        if w in verified_conditions: continue
        if re.search(r"(?<!\w)" + w + r"(?!\w)", low):
            out.append(_issue("WARN", "copy", "FS-C-02", f"'{w}' FSSAI me shart-wala shabd hai — shart poori ho aur saboot ho tabhi rakho",
                              "Tathya-wala shabd likho: 'nitrogen-flushed pack' (saboot ke saath), 'packed on <date>'"))
    return out

def audit_images(images: list, platform: str = "Amazon") -> list:
    """images: [{'role':'main'|'other','width':..,'height':..,'bg_rgb':(255,255,255),'fill_pct':85,'has_text':False}]"""
    out = []
    if images is None: return out
    if platform == "Flipkart":
        v = MK.rule("FK-I-01")["value"]
        if len(images) < v["min_count"]: out.append(_issue("BLOCK", "images", "FK-I-01", f"Kam se kam {v['min_count']} images chahiye"))
        if len(images) > v["max_count"]: out.append(_issue("WARN", "images", "FK-I-01", f"Flipkart par zyada se zyada {v['max_count']}"))
        rid, px = "FK-I-01", v["min_px"]
    else:
        v = MK.rule("AMZ-I-02")["value"]; rid, px = "AMZ-I-02", v["min_px"]
        if len(images) < 6: out.append(_issue("WARN", "images", "AMZ-I-02", f"Sirf {len(images)} images — 6-7 ka lakshya (size-proof, nutrition, use-case)"))
    for i, im in enumerate(images, 1):
        longest = max(im.get("width", 0) or 0, im.get("height", 0) or 0)
        if longest and longest < px: out.append(_issue("WARN", f"image_{i}", rid, f"{longest}px — kam se kam {px}px"))
        if im.get("role") == "main" and platform == "Amazon":
            bg = tuple(im.get("bg_rgb") or ())
            if bg and bg != (255, 255, 255): out.append(_issue("BLOCK", "main_image", "AMZ-I-01", f"Background {bg} — shuddh safed (255,255,255) chahiye"))
            if im.get("has_text"): out.append(_issue("BLOCK", "main_image", "AMZ-I-01", "Main image par text/logo/badge mana hai"))
            if im.get("fill_pct") is not None and im["fill_pct"] < 80:
                out.append(_issue("WARN", "main_image", "AMZ-I-01", f"Product sirf {im['fill_pct']}% frame me — ~85% bharo"))
    return out

def audit_evidence(db, sku: str, text: str) -> list:
    """NS-P-01: copy ke har saboot-maangne wale dawe (nitrogen, organic, FSSAI, origin, grade...) ka saboot fact registry me.
    Approve ke waqt yahi jaanch rokti hai — builder ab pehle hi bata deta hai."""
    import fact_registry as FR
    chk = FR.check_copy(db, sku, text)
    return [_issue("BLOCK", "copy", "NS-P-01", f"'{ft}' ka saboot fact registry me nahi — approve par rukega",
                   "Saboot (lab report/certificate/invoice) darj karo ya ye dawa copy se hatao") for ft in chk["needs_evidence"]]

def audit_listing(platform: str = "Amazon", title: str = "", bullets=(), backend_terms: str = "",
                  item_highlights: str = None, images=None, competitor_brands=(), verified_conditions=(),
                  db=None, sku: str = None) -> dict:
    issues = audit_title(title, platform, competitor_brands) + audit_bullets(list(bullets), platform)
    if platform == "Amazon":
        issues += audit_backend(backend_terms, title, bullets, competitor_brands)
        if item_highlights is not None:
            mx = MK.rule("AMZ-T-02")["value"]["max_chars"]
            if len(item_highlights) > mx:
                issues.append(_issue("BLOCK", "item_highlights", "AMZ-T-02", f"{len(item_highlights)} akshar — seema {mx}"))
            if len(title or "") > MK.rule("AMZ-T-01")["value"]["max_chars"]:
                issues.append(_issue("WARN", "item_highlights", "AMZ-T-02", "Item Highlights tabhi milta hai jab title <=75 ho"))
    issues += audit_fssai(" ".join([title or "", item_highlights or ""] + list(bullets)), verified_conditions)
    issues += audit_images(images, platform)
    if db is not None and sku:
        issues += audit_evidence(db, sku, " ".join([title or "", item_highlights or ""] + list(bullets)))
    blocks = [i for i in issues if i["severity"] == "BLOCK"]
    warns = [i for i in issues if i["severity"] == "WARN"]
    score = max(0, 100 - 20 * len(blocks) - 5 * len(warns) - sum(1 for i in issues if i["severity"] == "TIP"))
    return {"platform": platform, "compliance_score": score, "can_publish": not blocks,
            "blocks": len(blocks), "warnings": len(warns), "issues": issues,
            "basis": "marketplace_knowledge niyam (har issue ka rule_id -> source URL); ranking ka dawa NAHI",
            "rules_checked_on": MK.CHECKED}

# ---------------- BUILDERS ----------------
def _fit(parts: list, limit: int, sep: str = " ") -> str:
    """Zaroori hisse pehle; jo seema me na samaye woh chhod do (beech se kaat kar adhoora shabd kabhi nahi)."""
    out = ""
    for p in parts:
        if not p: continue
        cand = (out + sep + p) if out else p
        if len(cand) <= limit: out = cand
    return out

def build_title_amazon(brand: str, product: str, grade: str = "", weight: str = "",
                       hero_keyword: str = "", form: str = "", max_chars: int = None) -> dict:
    """Amazon 2026 title: Brand + Product (+hero keyword agar naya shabd jode) + Grade + Form + Weight, <=75.
    Hero keyword ke jo shabd pehle se hain unhe dohrate nahi (repeat-niyam)."""
    mx = max_chars or MK.rule("AMZ-T-01")["value"]["max_chars"]
    have = {_stem(w) for w in _words(f"{brand} {product} {grade} {form} {weight}")}
    extra = " ".join(w for w in (hero_keyword or "").split() if _stem(w) not in have and _stem(w) not in STOP_WORDS).title()
    core = f"{brand} {product}".strip()
    # Weight sabse aakhir par par zaroori — pehle jagah rakho
    reserve = (len(weight) + 1) if weight else 0
    head = _fit([core, extra, grade, form], mx - reserve)
    title = f"{head} {weight}".strip() if weight else head
    issues = audit_title(title, "Amazon")
    return {"title": title, "chars": len(title), "max": mx, "dropped_keyword_words": extra if extra and extra not in title else "",
            "issues": issues, "rule_ids": ["AMZ-T-01", "AMZ-T-03", "AMZ-T-04", "AMZ-T-05"]}

def build_item_highlights(points: list, max_chars: int = None) -> dict:
    mx = max_chars or MK.rule("AMZ-T-02")["value"]["max_chars"]
    s = _fit([p.strip() for p in points if p and p.strip()], mx, sep=", ")
    return {"item_highlights": s, "chars": len(s), "max": mx, "rule_ids": ["AMZ-T-02"]}

def pack_backend_terms(candidates: list, title: str = "", bullets=(), competitor_brands=(),
                       max_bytes: int = None) -> dict:
    """candidates: priority order me (sabse zaroori pehle). Title/bullets ke shabd, dohraav,
    competitor brands, subjective shabd hata kar 200 bytes me pack karta hai."""
    mx = max_bytes or MK.rule("AMZ-K-01")["value"]["max_bytes"]
    seen = {_stem(w) for w in _words(title + " " + " ".join(bullets or []))}
    brands = {b.lower() for b in competitor_brands if b}
    out, used, dropped = [], set(), []
    for c in candidates:
        for w in _words(c):
            s = _stem(w)
            if s in seen or s in used or s in STOP_WORDS: continue
            if w in brands or any(w == x for x in SUBJECTIVE) or re.fullmatch(r"b0[0-9a-z]{8}", w): continue
            cand = " ".join(out + [w])
            if byte_len(cand) <= mx: out.append(w); used.add(s)
            else: dropped.append(w)
    s = " ".join(out)
    return {"backend_terms": s, "bytes": byte_len(s), "max_bytes": mx, "words": len(out),
            "dropped_for_space": dropped, "rule_ids": ["AMZ-K-01", "AMZ-K-02", "AMZ-K-03"]}
