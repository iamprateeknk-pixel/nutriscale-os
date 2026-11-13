"""Listing Rules Engine (V23) — turns the marketplace_knowledge rules into RUNNABLE checks.

Two jobs:
1. audit_listing(): checks title / item highlights / bullets / backend / images — every issue carries a
   rule_id (see marketplace_knowledge for the source) and a severity:
     BLOCK = breaks policy (Amazon will rewrite/hide it, or FSSAI risk) — fix before publishing
     WARN  = a risk or weakness
     TIP   = a suggestion for improvement
2. build_*(): builds a title (<=75), item highlights (<=125) and backend terms (<=200 bytes) within the rules.
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
    """Counts plurals/forms as one word (almonds->almond, cashews->cashew, dates->date)."""
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
                              f"Title is {len(t)} characters — the Amazon limit is {mx}. Amazon's AI will rewrite longer titles.",
                              "Build it within 75 with build_title_amazon(); move the rest to Item Highlights"))
        v = MK.rule("AMZ-T-04")["value"]
        bad = sorted({c for c in t if c in v["banned"]})
        if bad: out.append(_issue("BLOCK", "title", "AMZ-T-04", f"Banned special characters: {' '.join(bad)}"))
        restr = sorted({c for c in t if c in v["restricted"]})
        if restr: out.append(_issue("WARN", "title", "AMZ-T-04", f"{' '.join(restr)} is only allowed in measurements/style numbers"))
    rep = repeated_words(t)
    if rep:
        out.append(_issue("BLOCK", "title", "AMZ-T-03" if platform == "Amazon" else "FK-T-01",
                          "Words used more than twice (plurals count): " + ", ".join(f"{w}×{c}" for w, c in rep.items()),
                          "Keep one form in the title and the other (Hinglish/synonym) in the backend"))
    low = t.lower()
    subj = [w for w in SUBJECTIVE if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", low)]
    if subj: out.append(_issue("WARN", "title", "AMZ-T-05", f"Promotional/subjective words in title: {', '.join(subj)}"))
    for b in competitor_brands:
        if b and b.lower() in low:
            out.append(_issue("BLOCK", "title", "AMZ-K-02", f"Competitor brand '{b}' in title — trademark/policy risk"))
    if t and t.isupper(): out.append(_issue("WARN", "title", "AMZ-T-05", "Whole title in CAPITALS — capitalise only the first letter of each word"))
    return out

def audit_bullets(bullets: list, platform: str = "Amazon") -> list:
    out, bl = [], [b for b in (bullets or []) if b and b.strip()]
    if len(bl) < 5: out.append(_issue("WARN", "bullets", "AMZ-B-03", f"Only {len(bl)} bullets — 5 needed"))
    lim = MK.rule("AMZ-B-03")["value"]
    for i, b in enumerate(bl, 1):
        if EMOJI_RE.search(b): out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-01", "Emojis are not allowed"))
        if any(c in b for c in LEGAL_SYMBOLS): out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-01", "™ ® © symbols are not allowed"))
        if any(re.search(p, b, re.I) for p in GUARANTEE):
            out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-02", "Guarantee/refund promises are not allowed in bullets"))
        if URL_RE.search(b): out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-02", "Website/email/contact details are not allowed in bullets"))
        if len(b) > lim["hard_max"]: out.append(_issue("BLOCK", f"bullet_{i}", "AMZ-B-03", f"{len(b)} characters — limit {lim['hard_max']}"))
        elif len(b) > lim["soft_max"]: out.append(_issue("TIP", f"bullet_{i}", "AMZ-B-03",
                                                          f"{len(b)} characters — mobile shows only the first ~{lim['soft_max']}; lead with the benefit"))
    return out

def audit_backend(backend: str, title: str = "", bullets=(), competitor_brands=()) -> list:
    out, b = [], backend or ""
    mx = MK.rule("AMZ-K-01")["value"]["max_bytes"]
    n = byte_len(b)
    if not b.strip(): out.append(_issue("WARN", "backend", "AMZ-K-03", "Backend search terms are empty — synonyms/Hinglish belong here"))
    if n > mx: out.append(_issue("BLOCK", "backend", "AMZ-K-01", f"{n} bytes — the Amazon.in limit is {mx} bytes; anything over it is not indexed",
                                 "Trim it with pack_backend_terms()"))
    if "," in b or ";" in b: out.append(_issue("TIP", "backend", "AMZ-K-02", "Use spaces instead of commas/semicolons — saves bytes"))
    seen = {_stem(w) for w in _words(title + " " + " ".join(bullets or []))}
    dup = sorted({w for w in _words(b) if _stem(w) in seen and _stem(w) not in STOP_WORDS})
    if dup: out.append(_issue("TIP", "backend", "AMZ-K-02", f"These words are already in the title/bullets, wasting bytes: {', '.join(dup[:10])}"))
    if re.search(r"\bb0[0-9a-z]{8}\b", b.lower()): out.append(_issue("BLOCK", "backend", "AMZ-K-02", "ASINs are not allowed in the backend"))
    for br in competitor_brands:
        if br and re.search(r"(?<!\w)" + re.escape(br.lower()) + r"(?!\w)", b.lower()):
            out.append(_issue("BLOCK", "backend", "AMZ-K-02", f"Competitor brand '{br}' in backend — not allowed"))
    subj = [w for w in SUBJECTIVE if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", b.lower())]
    if subj: out.append(_issue("WARN", "backend", "AMZ-K-02", f"Subjective/temporary words: {', '.join(subj)}"))
    return out

def audit_fssai(text: str, verified_conditions=()) -> list:
    """FSSAI: disease claims (claim_checker BLOCKs them) + conditional words (natural/fresh/...)."""
    from claim_checker import check_listing_text
    out = []
    cc = check_listing_text(text)
    for r in cc["blocked_reasons"]: out.append(_issue("BLOCK", "copy", "FS-C-01", r))
    for w in cc["warnings"]: out.append(_issue("WARN", "copy", "FS-C-01", w))
    low = (text or "").lower()
    for w in MK.rule("FS-C-02")["value"]["conditional_words"]:
        if w in verified_conditions: continue
        if re.search(r"(?<!\w)" + w + r"(?!\w)", low):
            out.append(_issue("WARN", "copy", "FS-C-02", f"'{w}' is a conditional word under FSSAI — keep it only if the conditions are met and you have evidence",
                              "Use factual wording: 'nitrogen-flushed pack' (with evidence), 'packed on <date>'"))
    return out

def audit_images(images: list, platform: str = "Amazon") -> list:
    """images: [{'role':'main'|'other','width':..,'height':..,'bg_rgb':(255,255,255),'fill_pct':85,'has_text':False}]"""
    out = []
    if images is None: return out
    if platform == "Flipkart":
        v = MK.rule("FK-I-01")["value"]
        if len(images) < v["min_count"]: out.append(_issue("BLOCK", "images", "FK-I-01", f"At least {v['min_count']} images needed"))
        if len(images) > v["max_count"]: out.append(_issue("WARN", "images", "FK-I-01", f"Flipkart allows at most {v['max_count']}"))
        rid, px = "FK-I-01", v["min_px"]
    else:
        v = MK.rule("AMZ-I-02")["value"]; rid, px = "AMZ-I-02", v["min_px"]
        if len(images) < 6: out.append(_issue("WARN", "images", "AMZ-I-02", f"Only {len(images)} images — aim for 6-7 (size proof, nutrition, use case)"))
    for i, im in enumerate(images, 1):
        longest = max(im.get("width", 0) or 0, im.get("height", 0) or 0)
        if longest and longest < px: out.append(_issue("WARN", f"image_{i}", rid, f"{longest}px — minimum {px}px"))
        if im.get("role") == "main" and platform == "Amazon":
            bg = tuple(im.get("bg_rgb") or ())
            if bg and bg != (255, 255, 255): out.append(_issue("BLOCK", "main_image", "AMZ-I-01", f"Background {bg} — must be pure white (255,255,255)"))
            if im.get("has_text"): out.append(_issue("BLOCK", "main_image", "AMZ-I-01", "Text/logo/badges are not allowed on the main image"))
            if im.get("fill_pct") is not None and im["fill_pct"] < 80:
                out.append(_issue("WARN", "main_image", "AMZ-I-01", f"Product fills only {im['fill_pct']}% of the frame — fill ~85%"))
    return out

def audit_evidence(db, sku: str, text: str) -> list:
    """NS-P-01: every claim in the copy that needs proof (nitrogen, organic, FSSAI, origin, grade...) must have evidence
    in the fact registry. The same check blocks approval — the builder now reports it up front."""
    import fact_registry as FR
    chk = FR.check_copy(db, sku, text)
    return [_issue("BLOCK", "copy", "NS-P-01", f"No evidence for '{ft}' in the fact registry — approval will be blocked",
                   "Record evidence (lab report/certificate/invoice) or remove this claim from the copy") for ft in chk["needs_evidence"]]

def audit_listing(platform: str = "Amazon", title: str = "", bullets=(), backend_terms: str = "",
                  item_highlights: str = None, images=None, competitor_brands=(), verified_conditions=(),
                  db=None, sku: str = None) -> dict:
    issues = audit_title(title, platform, competitor_brands) + audit_bullets(list(bullets), platform)
    if platform == "Amazon":
        issues += audit_backend(backend_terms, title, bullets, competitor_brands)
        if item_highlights is not None:
            mx = MK.rule("AMZ-T-02")["value"]["max_chars"]
            if len(item_highlights) > mx:
                issues.append(_issue("BLOCK", "item_highlights", "AMZ-T-02", f"{len(item_highlights)} characters — limit {mx}"))
            if len(title or "") > MK.rule("AMZ-T-01")["value"]["max_chars"]:
                issues.append(_issue("WARN", "item_highlights", "AMZ-T-02", "Item Highlights is only available when the title is <=75"))
    issues += audit_fssai(" ".join([title or "", item_highlights or ""] + list(bullets)), verified_conditions)
    issues += audit_images(images, platform)
    if db is not None and sku:
        issues += audit_evidence(db, sku, " ".join([title or "", item_highlights or ""] + list(bullets)))
    blocks = [i for i in issues if i["severity"] == "BLOCK"]
    warns = [i for i in issues if i["severity"] == "WARN"]
    score = max(0, 100 - 20 * len(blocks) - 5 * len(warns) - sum(1 for i in issues if i["severity"] == "TIP"))
    return {"platform": platform, "compliance_score": score, "can_publish": not blocks,
            "blocks": len(blocks), "warnings": len(warns), "issues": issues,
            "basis": "marketplace_knowledge rules (each issue's rule_id -> source URL); NOT a ranking claim",
            "rules_checked_on": MK.CHECKED}

# ---------------- BUILDERS ----------------
def _fit(parts: list, limit: int, sep: str = " ") -> str:
    """Most important parts first; drop whatever does not fit (never cut a word in half)."""
    out = ""
    for p in parts:
        if not p: continue
        cand = (out + sep + p) if out else p
        if len(cand) <= limit: out = cand
    return out

def build_title_amazon(brand: str, product: str, grade: str = "", weight: str = "",
                       hero_keyword: str = "", form: str = "", max_chars: int = None) -> dict:
    """Amazon 2026 title: Brand + Product (+hero keyword if it adds a new word) + Grade + Form + Weight, <=75.
    Hero-keyword words already present are not repeated (repeat rule)."""
    mx = max_chars or MK.rule("AMZ-T-01")["value"]["max_chars"]
    have = {_stem(w) for w in _words(f"{brand} {product} {grade} {form} {weight}")}
    extra = " ".join(w for w in (hero_keyword or "").split() if _stem(w) not in have and _stem(w) not in STOP_WORDS).title()
    core = f"{brand} {product}".strip()
    # Weight goes last but is essential — reserve its space first
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
    """candidates: in priority order (most important first). Removes words already in title/bullets, repeats,
    competitor brands and subjective words, then packs the rest into 200 bytes."""
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
