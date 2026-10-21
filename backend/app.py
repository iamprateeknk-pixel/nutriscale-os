"""Growth OS Backend API — koi bahari library nahi, Python ke saath chalta hai.
Endpoints: GET /health | GET /api/warroom | GET /api/approvals | POST /api/approvals/{id}/approve|reject
Production me yahi FastAPI + Postgres + auth ke saath jayega; contract (URLs/JSON) wahi rahega.
Chalana: python3 backend/app.py  (port 8765)
"""
import json, sys, os
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from warroom_service import warroom_data
from db_store import Store

def _waiting_approvals():
    s = Store()
    try:
        rows = s.db.execute("SELECT id, agent, action_type, description, tier, status, predicted FROM actions WHERE status LIKE 'WAITING%' ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally: s.close()

class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path == "/health": return self._send(200, {"status": "ok", "service": "DryFruit Growth OS"})
        if self.path == "/api/warroom": return self._send(200, warroom_data())
        if self.path == "/api/connectors/status":
            from connectors.config import status_all
            return self._send(200, {"connectors": status_all(),
                                    "setup_guide": "CONNECTORS_SETUP.md"})
        if self.path == "/api/approvals":
            # Approvals DB ki actions table se — agents ne jo asal proposals file kiye, wahi.
            return self._send(200, {"approvals": _waiting_approvals()})
        if self.path == "/api/action-plan":
            from action_planner import build_plan
            s = Store()
            try: return self._send(200, {"plan": build_plan(s)})
            finally: s.close()
        if self.path == "/api/season-pack":
            from season_planner import build_season_pack
            s = Store()
            try: return self._send(200, build_season_pack(s))
            finally: s.close()
        return self._send(404, {"error": "not found"})
    def do_POST(self):
        parts = self.path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "approvals"] and parts[3] in ("approve", "reject"):
            aid = int(parts[2]); new_status = "APPROVED_EXECUTING" if parts[3] == "approve" else "REJECTED"
            s = Store()
            try:
                cur = s.db.execute("UPDATE actions SET status=? WHERE id=? AND status LIKE 'WAITING%'", (new_status, aid))
                s.db.commit()
                if cur.rowcount == 0: return self._send(404, {"error": "approval nahi mila ya pehle faisla ho chuka"})
            finally: s.close()
            return self._send(200, {"id": aid, "status": new_status,
                                    "note": "Faisla DB me record — execution connectors ke through hoga, result 7/14 din me maapa jayega"})
        if self.path == "/api/cycle/run":
            from agents.governance import GovernanceAgent
            s = Store()
            try: report = GovernanceAgent(s).daily_cycle()
            finally: s.close()
            return self._send(200, report)
        return self._send(404, {"error": "not found"})
    def log_message(self, *a): pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    print(f"Growth OS backend chal raha hai: http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), H).serve_forever()
