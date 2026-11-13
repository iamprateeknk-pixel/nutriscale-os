"""Seller Acceptance Report (V23 prep) — a one-page evidence report from the real DB.
NutriScale's own numbers in one place, with their basis, for comparison with the marketplace's real
numbers (Seller Central/Flipkart Hub): sales, orders, refunds, fees
coverage, finance matching verdict, TACOS sthiti, stock channels, capabilities, preflight.
Missing data is written as 'not available' — never an estimate.
Chalao: python3 scripts/acceptance_report.py [--out docs/ACCEPTANCE_YYYY-MM-DD.md]"""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db_store import Store
import analytics as AN, pilot as P
from platform_core import ensure_v12

def build_report(store) -> str:
    db = store.db; ensure_v12(db)
    today = datetime.date.today().isoformat()
    L = [f"# Seller Acceptance Report — {today}", "",
         "_NutriScale OS real numbers, with their basis. For comparison with marketplace reports._", ""]
    for plat in ("Amazon", "Flipkart"):
        t = AN.sales_totals(db, plat)
        L += [f"## {plat}", f"- Revenue (NET): ₹{t['revenue']:,.2f} — basis: {t['source']}",
              f"- Orders: {t['orders']} (cancelled separately: {t.get('cancelled_orders', 0)}), lines: {t['lines']}"]
        fg = P.finance_grade_matching(db, plat, 30)
        comp = P.reporting_completeness(db, plat, 30)
        L += [f"- Finance matching (30d): {fg['verdict']} — checked {fg['orders_checked']}, matched {fg['matched']}, "
              f"fee-missing {fg['fee_data_missing']}, mismatch {fg['amount_mismatch']} (key: {fg['basis']})",
              f"- Completeness (30d): ads coverage {comp['ads_period_coverage_pct']}%, fee coverage {comp['fee_coverage_pct']}%"]
        rec = P.reconciliation_report(store, plat, 30)
        L += [f"- Reconciliation (30d): orders NET ₹{rec['orders_in_window']['net_revenue']:,.2f} vs settlements "
              f"(prorated estimate ₹{rec['settlements_overlapping_window']['gross_prorated_estimate']:,.2f}, "
              f"status: {rec['settlements_overlapping_window']['comparison_status'][:40]}...)",
              f"- Ads spend (period-tagged, 30d): ₹{rec['search_terms_spend_in_window']:,.2f}", ""]
    inv = db.execute("SELECT COUNT(DISTINCT sku) s, COALESCE(SUM(qty),0) q FROM inventory").fetchone()
    L += ["## Stock", f"- SKUs with inventory: {inv['s']}, total qty: {inv['q']}", ""]
    caps = [dict(r) for r in db.execute("SELECT platform, capability, status FROM capabilities ORDER BY platform, capability")]
    L += ["## Capabilities"] + ([f"- {c['platform']} / {c['capability']}: {c['status']}" for c in caps] or ["- (registry empty)"]) + [""]
    pf = P.preflight(db)
    L += ["## Preflight"] + [f"- {'✔' if c['ok'] else '✘'} {c['check']} — {c['detail']}" for c in pf["checks"]]
    L += ["", "_This report is built from the system's own DB; comparing it with the marketplace's real reports is the acceptance test._"]
    return "\n".join(L)

if __name__ == "__main__":
    out = None
    if "--out" in sys.argv: out = sys.argv[sys.argv.index("--out") + 1]
    store = Store()
    md = build_report(store)
    if out:
        with open(out, "w") as f: f.write(md)
        print(f"Acceptance report written: {out}")
    else:
        print(md)
    store.close()
