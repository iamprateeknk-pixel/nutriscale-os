"""A14 Learning Governor — Learning Sources Registry.
Which source, how trusted, for which agent. Crawled daily at 6 am.
Fee/policy sources come first — a wrong fee = wrong profit = every decision wrong.
"""

SOURCES = [
    # Official — highest trust
    {"name": "Amazon Seller University", "type": "official", "reliability": 1.0, "agents": ["A04", "A06", "A09"], "watch": "policy, fees, FBA, listing rules"},
    {"name": "Amazon Ads Academy / Ads Blog", "type": "official", "reliability": 1.0, "agents": ["A06", "A03"], "watch": "naye ad features, bidding, targeting"},
    {"name": "Flipkart Seller Learning Center", "type": "official", "reliability": 1.0, "agents": ["A04", "A06", "A09"], "watch": "Flipkart policy, fees, Assured rules"},
    {"name": "Unicommerce Docs/Help", "type": "official", "reliability": 1.0, "agents": ["A13"], "watch": "API changes, new features"},
    # Practitioner — for tactics
    {"name": "Helium 10 Blog/Podcast", "type": "practitioner", "reliability": 0.8, "agents": ["A03", "A06"], "watch": "keyword/ads tactics, case studies"},
    {"name": "Jungle Scout / SellerApp Blog", "type": "practitioner", "reliability": 0.75, "agents": ["A01", "A03"], "watch": "category data, launch strategies"},
    {"name": "Indian Seller YouTube (top channels)", "type": "practitioner", "reliability": 0.6, "agents": ["A01", "A04", "A06"], "watch": "India-specific tricks, Seller Central hindi walkthrough"},
    # Community — ground truth, but verify before adopting
    {"name": "Seller Forums / Reddit / FB Groups", "type": "community", "reliability": 0.45, "agents": ["A01", "A08"], "watch": "other sellers' mistakes, account health issues"},
    # News — the big picture
    {"name": "Ecommerce News (ET Retail, Inc42)", "type": "news", "reliability": 0.7, "agents": ["A01", "A02"], "watch": "category trend, competitor brands ke moves"},
]

def sources_for_agent(agent_id: str) -> list:
    return [s for s in SOURCES if agent_id in s["agents"]]

def daily_crawl_plan() -> list:
    """The 6 am crawl — official first (fee/policy), then the rest."""
    order = {"official": 0, "practitioner": 1, "news": 2, "community": 3}
    return sorted(SOURCES, key=lambda s: order[s["type"]])
