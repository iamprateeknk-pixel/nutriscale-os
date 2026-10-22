"""NutriScale OS Backend — V12: Auth + RBAC ke saath (SEC-01).
Bina login ke koi business data nahi dikhega (sirf /health aur login khule hain).
Pehla Owner banana:  NUTRISCALE_OWNER_USER=... NUTRISCALE_OWNER_PASSWORD=... python3 backend/app.py
ya:  python3 -c "import sys; sys.path.insert(0,'src'); from db_store import Store; import auth; s=Store(); print(auth.create_user(s.db,'owner','lamba-password','Owner')); s.close()"
API v1 envelope: {data, meta:{request_id, computed_at}, errors:[]}
Chalana: python3 backend/app.py  (port 8765)
"""
import json, sys, os, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from warroom_service import warroom_data
from db_store import Store
import auth as auth_mod
import actions as act
from platform_core import now_utc

def _waiting_approvals():
    s = Store()
    try:
        rows = s.db.execute("SELECT id, agent, action_type, description, tier, status, predicted FROM actions WHERE status LIKE 'WAITING%' ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally: s.close()

def _bootstrap_owner():
    u, p = os.environ.get("NUTRISCALE_OWNER_USER"), os.environ.get("NUTRISCALE_OWNER_PASSWORD")
    if u and p:
        s = Store()
        try:
            from platform_core import ensure_v12; ensure_v12(s.db)
            if not s.db.execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone():
                print("Owner user bana:", auth_mod.create_user(s.db, u, p, "Owner"))
        finally: s.close()

class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _env(self, code, data):
        return self._send(code, {"data": data, "meta": {"request_id": uuid.uuid4().hex[:12], "computed_at": now_utc()}, "errors": []})
    def _body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)).decode() or "{}")
        except Exception: return {}
    def _auth(self, perm):
        s = Store()
        user, err = auth_mod.require(s.db, self.headers, perm)
        if err: self._send(err[0], err[1])
        return s, user, err

    def _serve_dashboard(self, rel: str):
        base = os.path.join(os.path.dirname(__file__), "..", "dashboard")
        path = os.path.normpath(os.path.join(base, rel))
        if not path.startswith(os.path.normpath(base)) or not os.path.isfile(path):
            return self._send(404, {"error": "file nahi mili"})
        body = open(path, "rb").read()
        ct = "text/html; charset=utf-8" if path.endswith(".html") else "text/plain; charset=utf-8"
        self.send_response(200); self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/health": return self._send(200, {"status": "ok", "service": "NutriScale OS", "version": "V12.1"})
        # Same-origin serving (V12.1): dashboard isi backend se — CORS ki zaroorat hi nahi, token bhi ek hi origin par
        if p in ("/", "/dashboard", "/dashboard/"): return self._serve_dashboard("index.html")
        if p.startswith("/dashboard/"): return self._serve_dashboard(p[len("/dashboard/"):])
        s, user, err = self._auth("read")
        if err: s.close(); return
        try:
            from platform_core import ensure_v12; ensure_v12(s.db)
            if p == "/api/warroom": return self._env(200, warroom_data())
            if p == "/api/approvals": return self._env(200, {"approvals": _waiting_approvals()})
            if p == "/api/connectors/status":
                from connectors.config import status_all
                return self._env(200, {"connectors": status_all(), "setup_guide": "CONNECTORS_SETUP.md"})
            if p == "/api/action-plan":
                from action_planner import build_plan
                return self._env(200, {"plan": build_plan(s)})
            if p == "/api/season-pack":
                from season_planner import build_season_pack
                return self._env(200, build_season_pack(s))
            if p == "/api/v1/control/kill": return self._env(200, act.kill_status(s.db))
            if p == "/api/v1/jobs/status":
                from jobrunner import jobs_status
                return self._env(200, {"jobs": jobs_status(s.db)})
            if p == "/api/v1/proposals":
                rows = [dict(r) for r in s.db.execute("SELECT id,kind,platform,tier,state,created_by,created_at,vendor_ref FROM action_v12 ORDER BY id DESC LIMIT 100")]
                return self._env(200, {"proposals": rows})
            if p.startswith("/api/v1/actions/"):
                aid = int(p.split("/")[-1])
                a = s.db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
                if not a: return self._send(404, {"error": "action nahi mila"})
                return self._env(200, {"action": dict(a), "timeline": act.action_timeline(s.db, aid)})
            if p == "/api/v1/campaigns":
                rows = [dict(r) for r in s.db.execute("SELECT * FROM campaigns ORDER BY spend DESC LIMIT 200")]
                return self._env(200, {"campaigns": rows, "source": "DB campaigns (CSV/API import)", "observed_at": now_utc()})
            if p == "/api/v1/keywords":
                rows = [dict(r) for r in s.db.execute("""SELECT term, SUM(clicks) clicks, SUM(purchases) purchases, SUM(spend) spend, SUM(sales) sales
                                                         FROM search_terms GROUP BY term ORDER BY spend DESC LIMIT 200""")]
                return self._env(200, {"keywords": rows, "search_volume": None,
                                        "note": "Search volume koi licensed provider nahi — 'unknown' hai, andaaz nahi dikhaya jayega"})
            if p == "/api/v1/keywords/matrix":
                from keyword_lab import opportunity_matrix
                return self._env(200, {"matrix": opportunity_matrix(s), "evidence": "Observed (apne search terms); volume sirf licensed provider se"})
            if p == "/api/v1/ads/health":
                import ads_studio as AS
                return self._env(200, {"campaigns": AS.campaign_health(s), "alerts": AS.pacing_alerts(s, 1000),
                                       "harvest": AS.harvest_candidates(s), "scenarios": AS.portfolio_scenarios(s, 30000)})
            if p == "/api/v1/competitors":
                peers = []
                for r in s.db.execute("SELECT * FROM peer_products ORDER BY id DESC"):
                    d = dict(r)
                    snap = s.db.execute("SELECT * FROM peer_snapshots WHERE peer_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (d["id"],)).fetchone()
                    d["latest_snapshot"] = dict(snap) if snap else None
                    d["changes"] = []
                    peers.append(d)
                return self._env(200, {"peers": peers, "note": "Snapshots sirf dated observation par — na mile to unknown, zero nahi"})
            if p == "/api/v1/finance/reconciliation":
                import ops_finance as OF
                return self._env(200, OF.reconciliation(s))
            if p == "/api/v1/costs":
                rows = [dict(r) for r in s.db.execute("SELECT sku, effective_from, cogs, packaging, other_variable, source FROM cost_versions ORDER BY sku, effective_from DESC")]
                return self._env(200, {"costs": rows, "note": "Cost na ho to us SKU par scale band hai (FIN-01)"})
            if p == "/api/v1/agency/scorecard":
                import agency as AG
                return self._env(200, AG.scorecard(s.db))
            if p == "/api/v1/system/health":
                import ops_finance as OF
                return self._env(200, OF.system_health(s))
            if p == "/api/v1/experiments":
                rows = [dict(r) for r in s.db.execute("SELECT * FROM experiments ORDER BY id DESC LIMIT 50")]
                return self._env(200, {"experiments": rows})
            if p == "/api/v1/listings/versions":
                rows = [dict(r) for r in s.db.execute("SELECT id, sku, platform, version, title, status, created_by, approved_by FROM listing_versions ORDER BY id DESC LIMIT 50")]
                return self._env(200, {"versions": rows})
            if p == "/api/v1/capabilities":
                import capabilities as caps
                return self._env(200, {"capabilities": caps.all_capabilities(s.db)})
            if p in ("/api/v1/rank", "/api/v1/rank/diagnostic", "/api/v1/rank/funnel", "/api/v1/competitors/packet", "/api/v1/inventory/gate", "/api/v1/creative/brief"):
                from urllib.parse import urlparse, parse_qs
                q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
                if p == "/api/v1/rank":
                    from keyword_lab import rank_trend
                    return self._env(200, rank_trend(s.db, q.get("term", ""), q.get("sku", "")))
                if p == "/api/v1/rank/diagnostic":
                    from keyword_lab import rank_diagnostic
                    return self._env(200, rank_diagnostic(s, q.get("term", ""), q.get("sku", "")))
                if p == "/api/v1/rank/funnel":
                    from keyword_lab import rank_funnel
                    return self._env(200, rank_funnel(s, q.get("term", ""), q.get("sku", "")))
                if p == "/api/v1/inventory/gate":
                    import ops_finance as OF
                    return self._env(200, OF.stock_gate(s, q.get("sku", "")))
                if p == "/api/v1/creative/brief":
                    from agents.creative_agent import main_image_brief
                    return self._env(200, main_image_brief(q.get("product", "Dry Fruits"), q.get("grade", "Premium"), q.get("weight", "200g")))
                import competitor_lab as CL
                prod = s.db.execute("SELECT * FROM products WHERE sku=?", (q.get("sku", ""),)).fetchone()
                if not prod: return self._send(404, {"error": "Apna product mila nahi — pehle catalog import karo"})
                pd = dict(prod)
                own = {"sku": pd["sku"], "name": pd["name"], "price": pd["price"],
                       "nut_type": q.get("nut", ""), "grade": q.get("grade", ""), "pack_g": float(q.get("pack_g", 200))}
                return self._env(200, CL.decision_packet(s.db, own, int(q.get("peer", 0))))
            return self._send(404, {"error": "not found"})
        finally: s.close()

    def do_POST(self):
        p = self.path.split("?")[0]; parts = p.strip("/").split("/")
        if p == "/api/v1/auth/login":
            b = self._body(); s = Store()
            try:
                r = auth_mod.verify_login(s.db, b.get("username", ""), b.get("password", ""), b.get("totp"))
                if not r: return self._send(401, {"error": "LOGIN_FAIL", "message": "Username/password galat hai"})
                if r.get("mfa_required"): return self._send(401, {"error": "MFA_REQUIRED", "message": r["message"]})
                return self._env(200, r)
            finally: s.close()
        # legacy approvals (purane agents ki table) — execute perm chahiye
        if len(parts) == 4 and parts[:2] == ["api", "approvals"] and parts[3] in ("approve", "reject"):
            s, user, err = self._auth("execute")
            if err: s.close(); return
            try:
                aid = int(parts[2]); new_status = "APPROVED_EXECUTING" if parts[3] == "approve" else "REJECTED"
                cur = s.db.execute("UPDATE actions SET status=? WHERE id=? AND status LIKE 'WAITING%'", (new_status, aid)); s.db.commit()
                if cur.rowcount == 0: return self._send(404, {"error": "approval nahi mila ya faisla ho chuka"})
                return self._env(200, {"id": aid, "status": new_status})
            finally: s.close()
        if p == "/api/cycle/run":
            s, user, err = self._auth("execute")
            if err: s.close(); return
            try:
                from agents.governance import GovernanceAgent
                return self._env(200, GovernanceAgent(s).daily_cycle())
            finally: s.close()
        if p == "/api/v1/control/kill":
            s, user, err = self._auth("kill")
            if err: s.close(); return
            try:
                b = self._body()
                return self._env(200, act.set_kill(s.db, bool(b.get("engaged")), user["username"], b.get("reason", "")))
            finally: s.close()
        if p == "/api/v1/proposals":
            s, user, err = self._auth("propose")
            if err: s.close(); return
            try:
                b = self._body()
                r = act.create_proposal(s.db, b.get("kind", "GENERIC"), b.get("platform", "Amazon"), b.get("account", "default"),
                                        b.get("payload", {}), b.get("tier", "ONE_TAP"), user["username"],
                                        b.get("idempotency_key") or uuid.uuid4().hex, b.get("predicted", ""))
                return self._env(200, {k: r[k] for k in ("id", "state", "duplicate") if k in r})
            finally: s.close()
        if p in ("/api/v1/competitors/peers", "/api/v1/competitors/snapshots", "/api/v1/costs",
                 "/api/v1/listings/draft", "/api/v1/listings/approve", "/api/v1/imports/preview",
                 "/api/v1/imports/commit", "/api/v1/experiments"):
            perm = "import" if "imports" in p else ("costs" if p.endswith("costs") else "propose")
            s, user, err = self._auth(perm)
            if err: s.close(); return
            try:
                b = self._body()
                if p == "/api/v1/competitors/peers":
                    import competitor_lab as CL
                    pid = CL.add_peer(s.db, b.get("platform", "Amazon"), b.get("peer_ref", ""), b.get("url", ""),
                                      b.get("title", ""), b.get("nut_type", ""), b.get("grade", ""),
                                      float(b.get("pack_g", 0)), b.get("processing", "raw"), added_by=user["username"])
                    return self._env(200, {"peer_id": pid})
                if p == "/api/v1/competitors/snapshots":
                    import competitor_lab as CL
                    sid = CL.add_snapshot(s.db, int(b["peer_id"]), price=b.get("price"), mrp=b.get("mrp"),
                                          coupon=b.get("coupon"), rating=b.get("rating"), reviews=b.get("reviews"),
                                          image_count=b.get("image_count"), in_stock=b.get("in_stock"),
                                          title=b.get("title"), source=b.get("source", "manual-observation"))
                    return self._env(200, {"snapshot_id": sid, "changes": CL.detect_changes(s.db, int(b["peer_id"]))})
                if p == "/api/v1/costs":
                    import finance as F
                    return self._env(200, F.set_cost(s.db, b["sku"], float(b["cogs"]), float(b.get("packaging", 0)),
                                                     float(b.get("other_variable", 0)), b.get("source", "manual"),
                                                     approved_by=user["username"]))
                if p == "/api/v1/listings/draft":
                    import listing_v2 as L2
                    return self._env(200, L2.save_draft(s.db, b["sku"], b.get("platform", "Amazon"), b.get("title", ""),
                                                        b.get("bullets", []), b.get("backend_terms", ""), user["username"]))
                if p == "/api/v1/listings/approve":
                    import listing_v2 as L2
                    return self._env(200, L2.approve_version(s.db, int(b["id"]), user["username"]))
                if p == "/api/v1/imports/preview":
                    from import_wizard import preview_import
                    return self._env(200, preview_import(s.db, b["path"], b.get("platform", "Amazon")))
                if p == "/api/v1/imports/commit":
                    from import_wizard import commit_import
                    return self._env(200, commit_import(s, b["path"], b.get("kind"), b.get("platform", "Amazon"),
                                                        imported_by=user["username"]))
                if p == "/api/v1/experiments":
                    import experiments as EX
                    return self._env(200, EX.create_experiment(s.db, b.get("name", ""), b.get("sku", ""),
                                                               b.get("platform", "Amazon"), b.get("hypothesis", ""),
                                                               b.get("primary_metric", "CVR"), b.get("intervention", ""),
                                                               user["username"]))
            finally: s.close()
        if len(parts) == 5 and parts[:3] == ["api", "v1", "proposals"]:
            aid, op = int(parts[3]), parts[4]
            perm = {"approve": None, "dry-run": "propose", "queue": "execute", "execute": "execute", "rollback": "execute"}[op]
            s, user, err = self._auth(perm or "approve_tier1")
            if err: s.close(); return
            try:
                if op == "approve": return self._env(200, act.approve(s.db, aid, user))
                if op == "dry-run": return self._env(200, act.dry_run(s.db, aid))
                if op == "queue": return self._env(200, act.queue_action(s.db, aid, user))
                if op == "execute":
                    b = self._body()
                    row = s.db.execute("SELECT * FROM action_v12 WHERE id=?", (aid,)).fetchone()
                    payload = {}
                    try: payload = json.loads(row["payload"] or "{}") if row else {}
                    except Exception: pass
                    if payload.get("adapter") == "amazon_ads":
                        from vendor_adapters import AmazonAdsWriteAdapter
                        return self._env(200, act.execute(s.db, aid, user, AmazonAdsWriteAdapter(s)))
                    conf = {row["idempotency_key"]: b["manual_ref"]} if row and b.get("manual_ref") else {}
                    return self._env(200, act.execute(s.db, aid, user, act.ManualAdapter(conf)))
                if op == "rollback":
                    from vendor_adapters import AmazonAdsWriteAdapter
                    return self._env(200, act.rollback(s.db, aid, user, AmazonAdsWriteAdapter(s)))
            finally: s.close()
        return self._send(404, {"error": "not found"})
    def log_message(self, *a): pass

if __name__ == "__main__":
    _bootstrap_owner()
    port = int(os.environ.get("PORT", "8765"))
    print(f"NutriScale OS backend (V12, auth on): http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), H).serve_forever()
