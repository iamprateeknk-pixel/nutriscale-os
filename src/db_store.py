"""Database Layer (G2 fix) — agents ki yaaddasht ab permanent hai.
SQLite file-based store: knowledge, action audit + results, rank-probe history.
Production me yahi schema Postgres par jayega — interface wahi rahega.
"""
import sqlite3, json, os, time

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "growth_os.db")

class Store:
    def __init__(self, path: str = DEFAULT_PATH):
        if path != ":memory:": os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path); self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge (id INTEGER PRIMARY KEY, lesson TEXT, source TEXT, reliability REAL, agent TEXT, applied INT DEFAULT 0, success INT DEFAULT 0, ts REAL);
        CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY, agent TEXT, action_type TEXT, description TEXT, tier TEXT, status TEXT, predicted TEXT, result_pct REAL, ts REAL);
        CREATE TABLE IF NOT EXISTS rank_history (id INTEGER PRIMARY KEY, sku TEXT, keyword TEXT, rank INT, ctr REAL, cvr REAL, ts REAL);
        CREATE TABLE IF NOT EXISTS rule_stats (key TEXT PRIMARY KEY, confidence REAL, wins INT, losses INT, enabled INT);
        CREATE TABLE IF NOT EXISTS products (sku TEXT PRIMARY KEY, name TEXT, platform TEXT, price REAL, cost REAL, rating REAL, reviews INT, source TEXT);
        CREATE TABLE IF NOT EXISTS orders (id TEXT, platform TEXT, sku TEXT, amount REAL, qty INT, ts REAL, PRIMARY KEY(id, platform));
        CREATE TABLE IF NOT EXISTS campaigns (name TEXT PRIMARY KEY, platform TEXT, spend REAL, sales REAL, clicks INT, impressions INT, source TEXT);
        CREATE TABLE IF NOT EXISTS search_terms (term TEXT, campaign TEXT, spend REAL, sales REAL, clicks INT, purchases INT, source TEXT);
        CREATE TABLE IF NOT EXISTS inventory (sku TEXT, location TEXT, qty INT, source TEXT, PRIMARY KEY(sku, location));
        """); self.db.commit()

    # ---------- Sync data (connectors/CSV se aaya asal data) ----------
    def upsert_product(self, sku, name, platform, price, cost=0, rating=0, reviews=0, source=""):
        self.db.execute("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?)",
                        (sku, name, platform, price, cost, rating, reviews, source)); self.db.commit()
    def add_order(self, oid, platform, sku, amount, qty=1, ts=None):
        self.db.execute("INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?)",
                        (oid, platform, sku, amount, qty, ts or time.time())); self.db.commit()
    def upsert_campaign(self, name, platform, spend, sales, clicks=0, impressions=0, source=""):
        self.db.execute("INSERT OR REPLACE INTO campaigns VALUES (?,?,?,?,?,?,?)",
                        (name, platform, spend, sales, clicks, impressions, source)); self.db.commit()
    def add_search_term(self, term, campaign, spend, sales, clicks=0, purchases=0, source=""):
        self.db.execute("INSERT INTO search_terms VALUES (?,?,?,?,?,?,?)",
                        (term, campaign, spend, sales, clicks, purchases, source)); self.db.commit()
    def set_inventory(self, sku, location, qty, source=""):
        self.db.execute("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?)",
                        (sku, location, qty, source)); self.db.commit()
    def has_real_data(self) -> bool:
        n = self.db.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]
        o = self.db.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
        c = self.db.execute("SELECT COUNT(*) c FROM campaigns").fetchone()["c"]
        return (n + o + c) > 0
    def totals(self) -> dict:
        o = self.db.execute("SELECT COALESCE(SUM(amount),0) s FROM orders").fetchone()["s"]
        camp = self.db.execute("SELECT COALESCE(SUM(spend),0) sp, COALESCE(SUM(sales),0) sa FROM campaigns").fetchone()
        return {"order_sales": round(o, 2), "ad_spend": round(camp["sp"], 2), "paid_sales": round(camp["sa"], 2)}
    def all_products(self): return [dict(r) for r in self.db.execute("SELECT * FROM products")]
    def all_campaigns(self): return [dict(r) for r in self.db.execute("SELECT * FROM campaigns")]
    def all_inventory(self): return [dict(r) for r in self.db.execute("SELECT * FROM inventory")]
    def waste_terms(self, min_spend=200): return [dict(r) for r in self.db.execute(
        "SELECT * FROM search_terms WHERE spend>=? AND purchases=0 ORDER BY spend DESC", (min_spend,))]

    # Knowledge (V3 ki seekh, ab hamesha ke liye)
    def add_knowledge(self, lesson, source, reliability, agent):
        self.db.execute("INSERT INTO knowledge (lesson,source,reliability,agent,ts) VALUES (?,?,?,?,?)",
                        (lesson, source, reliability, agent, time.time())); self.db.commit()
    def knowledge_for(self, agent):
        return [dict(r) for r in self.db.execute("SELECT * FROM knowledge WHERE agent=? ORDER BY reliability DESC", (agent,))]

    # Actions — har faisla aur uska asal result (seekhne ka khana)
    def log_action(self, agent, action_type, description, tier, status, predicted=""):
        cur = self.db.execute("INSERT INTO actions (agent,action_type,description,tier,status,predicted,ts) VALUES (?,?,?,?,?,?,?)",
                              (agent, action_type, description, tier, status, predicted, time.time())); self.db.commit()
        return cur.lastrowid
    def record_result(self, action_id, result_pct):
        self.db.execute("UPDATE actions SET result_pct=? WHERE id=?", (result_pct, action_id)); self.db.commit()
    def action_success_rate(self, agent):
        rows = self.db.execute("SELECT result_pct FROM actions WHERE agent=? AND result_pct IS NOT NULL", (agent,)).fetchall()
        if not rows: return None
        return round(sum(1 for r in rows if r["result_pct"] > 0) / len(rows) * 100, 1)

    # Rank Probe history (algorithm ko ulta samajhne ka data)
    def log_rank(self, sku, keyword, rank, ctr, cvr):
        self.db.execute("INSERT INTO rank_history (sku,keyword,rank,ctr,cvr,ts) VALUES (?,?,?,?,?,?)",
                        (sku, keyword, rank, ctr, cvr, time.time())); self.db.commit()
    def rank_series(self, keyword):
        return [dict(r) for r in self.db.execute("SELECT * FROM rank_history WHERE keyword=? ORDER BY ts", (keyword,))]

    # Rule confidence persistence (OutcomeLearner ka saathi)
    def save_rule(self, key, confidence, wins, losses, enabled):
        self.db.execute("INSERT OR REPLACE INTO rule_stats VALUES (?,?,?,?,?)", (key, confidence, wins, losses, int(enabled))); self.db.commit()
    def load_rules(self):
        return {r["key"]: dict(r) for r in self.db.execute("SELECT * FROM rule_stats")}
    def close(self): self.db.close()
