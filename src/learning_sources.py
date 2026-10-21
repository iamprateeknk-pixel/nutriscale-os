"""A14 Learning Governor — Learning Sources Registry.
Kaunsa source, kitna bharosa, kis agent ke liye. Roz subah 6 baje crawl.
Fee/policy wale sources sabse upar — galat fee = galat profit = galat har faisla.
"""

SOURCES = [
    # Official — bharosa sabse zyada
    {"name": "Amazon Seller University", "type": "official", "reliability": 1.0, "agents": ["A04", "A06", "A09"], "watch": "policy, fees, FBA, listing rules"},
    {"name": "Amazon Ads Academy / Ads Blog", "type": "official", "reliability": 1.0, "agents": ["A06", "A03"], "watch": "naye ad features, bidding, targeting"},
    {"name": "Flipkart Seller Learning Center", "type": "official", "reliability": 1.0, "agents": ["A04", "A06", "A09"], "watch": "Flipkart policy, fees, Assured rules"},
    {"name": "Unicommerce Docs/Help", "type": "official", "reliability": 1.0, "agents": ["A13"], "watch": "API changes, naye features"},
    # Practitioner — tactics ke liye
    {"name": "Helium 10 Blog/Podcast", "type": "practitioner", "reliability": 0.8, "agents": ["A03", "A06"], "watch": "keyword/ads tactics, case studies"},
    {"name": "Jungle Scout / SellerApp Blog", "type": "practitioner", "reliability": 0.75, "agents": ["A01", "A03"], "watch": "category data, launch strategies"},
    {"name": "Indian Seller YouTube (top channels)", "type": "practitioner", "reliability": 0.6, "agents": ["A01", "A04", "A06"], "watch": "India-specific tricks, Seller Central hindi walkthrough"},
    # Community — zameeni sach, lekin verify karke apnao
    {"name": "Seller Forums / Reddit / FB Groups", "type": "community", "reliability": 0.45, "agents": ["A01", "A08"], "watch": "dusro ki galtiyan, account health issues"},
    # News — badi tasveer
    {"name": "Ecommerce News (ET Retail, Inc42)", "type": "news", "reliability": 0.7, "agents": ["A01", "A02"], "watch": "category trend, competitor brands ke moves"},
]

def sources_for_agent(agent_id: str) -> list:
    return [s for s in SOURCES if agent_id in s["agents"]]

def daily_crawl_plan() -> list:
    """Subah 6 baje ka crawl — official pehle (fee/policy), phir baaki."""
    order = {"official": 0, "practitioner": 1, "news": 2, "community": 3}
    return sorted(SOURCES, key=lambda s: order[s["type"]])
