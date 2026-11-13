"""POL-01 Verified Fact Registry — evidence first for every 'fact' in listing copy.
Template se bane dawe (nitrogen flush, organic, no added sugar, diabetic-friendly, origin)
never go into copy without a verified fact in the registry — they get NEEDS_EVIDENCE.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from platform_core import ensure_v12, now_utc

# words that need evidence: (pattern, fact_type)
PROOF_CLAIMS = [
    (r"nitrogen", "PROCESSING_NITROGEN"),
    (r"organic|jaivik", "CERT_ORGANIC"),
    (r"no added sugar|bina chini|unsweetened|sugar.?free", "NO_ADDED_SUGAR"),
    (r"diabet|madhumeh", "HEALTH_DIABETES"),
    (r"lab test|lab tested|parikshan", "LAB_TEST"),
    (r"a\+\+|grade a", "GRADE_PROOF"),
    (r"afghan|afghani", "ORIGIN"),
    (r"california", "ORIGIN"),
    (r"mamra", "ORIGIN_GRADE"),
    (r"fssai", "LICENCE_FSSAI"),
]

def add_fact(db, sku: str, fact_type: str, fact_value: str, evidence_ref: str, verified_by: str) -> dict:
    ensure_v12(db)
    if not evidence_ref: return {"ok": False, "error": "A fact cannot be recorded without evidence (evidence_ref)"}
    db.execute("INSERT INTO fact_registry(sku,fact_type,fact_value,evidence_ref,verified_by,verified_at) VALUES (?,?,?,?,?,?)",
               (sku, fact_type, fact_value, evidence_ref, verified_by, now_utc())); db.commit()
    return {"ok": True, "sku": sku, "fact_type": fact_type}

def facts_for(db, sku: str) -> list:
    ensure_v12(db)
    return [dict(r) for r in db.execute("SELECT * FROM fact_registry WHERE sku=?", (sku,))]

def check_copy(db, sku: str, text: str) -> dict:
    """Whether the claims in the copy have evidence in the registry."""
    have = {f["fact_type"] for f in facts_for(db, sku)}
    missing, found = [], []
    low = text.lower()
    for pat, ftype in PROOF_CLAIMS:
        if re.search(pat, low):
            (found if ftype in have else missing).append(ftype)
    return {"sku": sku, "can_publish": not missing, "verified_claims": sorted(set(found)),
            "needs_evidence": sorted(set(missing)),
            "status": "OK" if not missing else "NEEDS_EVIDENCE",
            "note": "Remove these claims from the copy or record evidence first" if missing else "Evidence exists for all claims"}
