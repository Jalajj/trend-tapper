#!/usr/bin/env python3
"""
Fetches live marketing/AI trends from multiple free sources and generates
a trends database for Trend Tapper.

Sources:
1. Google Trends RSS (marketing keywords)
2. Hacker News top stories (tech/marketing)
3. Reddit r/marketing + r/digital_marketing hot posts

Output: static/data/trends.json — consumed by index.html
"""

import json
import os
import re
from datetime import datetime, timezone

try:
    import feedparser
except ImportError:
    os.system("pip install feedparser -q")
    import feedparser

try:
    import requests
except ImportError:
    os.system("pip install requests -q")
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    os.system("pip install beautifulsoup4 -q")
    from bs4 import BeautifulSoup

CATEGORIES = {
    "ai-marketing": ["marketing", "ai marketing", "machine learning", "artificial intelligence", "automation"],
    "ai-tools": ["ai tools", "chatgpt", "gpt", "llm", "claude", "midjourney", "cursor ai"],
    "content": ["content marketing", "social media", "linkedin", "tiktok", "youtube", "video content"],
    "ads": ["advertising", "facebook ads", "google ads", "ppc", "tiktok ads", "programmatic"],
    "growth": ["growth hacking", "conversion", "retention", "growth marketing", "user acquisition"],
    "agency": ["agency operations", "client retention", "pricing", "freelancer", "outsourcing"],
}

def fetch_google_trends():
    """Fetch trending searches from Google Trends RSS."""
    trends = []
    try:
        # Google Trends RSS for various countries — "trending searches"
        feeds = [
            "https://trends.google.com/trends/trending/rss?geo=US&category=0",
        ]
        for url in feeds:
            d = feedparser.parse(url)
            for entry in d.entries[:30]:
                title = entry.title
                # Filter for marketing-relevant
                keywords = ["marketing", "ai", "tool", "content", "social", "advertis", "growth", "agency", "digital", "data", "automation", "llm", "chatgpt", "seo", "email"]
                if any(kw.lower() in title.lower() for kw in keywords):
                    trends.append({
                        "title": title,
                        "desc": getattr(entry, 'description', '')[:200] or "Trending search term on Google.",
                        "source_url": entry.link,
                        "source_name": "Google Trends",
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    })
    except Exception as e:
        print(f"Google Trends: {e}")
    return trends[:10]

def fetch_hn_stories():
    """Fetch top stories from Hacker News."""
    trends = []
    try:
        # Get top stories
        r = requests.get("https://hnrss.org/frontpage", timeout=15)
        d = feedparser.parse(r.text)
        for entry in d.entries[:40]:
            title = entry.title
            # Filter for AI/marketing relevant
            keywords = ["ai", "llm", "gpt", "machine learning", "startup", "saas",
                       "automation", "no-code", "tool", "marketing", "data",
                       "api", "model", "agent"]
            if any(kw.lower() in title.lower() for kw in keywords):
                desc = entry.get("content", [{}])[0].get("value", "") or entry.get("summary", "")
                # Clean HTML from summary
                desc = BeautifulSoup(desc, "html.parser").get_text()[:200] if desc else "AI/tech innovation discussed on Hacker News."
                trends.append({
                    "title": title,
                    "desc": desc or "Tech innovation discussed on Hacker News.",
                    "source_url": entry.link,
                    "source_name": "Hacker News",
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                })
    except Exception as e:
        print(f"HN: {e}")
    return trends[:10]

def fetch_reddit():
    """Fetch hot posts from marketing subreddits."""
    trends = []
    try:
        subs = ["marketing", "digital_marketing", "content_marketing", "growthhacking"]
        for sub in subs:
            url = f"https://r.jina.ai/https://reddit.com/r/{sub}/hot.json?limit=10"
            r = requests.get(url, headers={"User-Agent": "TrendTapper/1.0"}, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            for post in data.get("data", {}).get("children", [])[:7]:
                p = post["data"]
                title = p.get("title", "")
                if len(title) > 15 and not title.startswith("["):
                    trends.append({
                        "title": title,
                        "desc": p.get("selftext", "")[:200] or "Discussion on r/" + sub + ".",
                        "source_url": "https://reddit.com" + p.get("permalink", ""),
                        "source_name": f"r/{sub}",
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    })
    except Exception as e:
        print(f"Reddit: {e}")
    return trends[:10]

def categorize_trend(title, desc):
    """Assign a category to a trend based on keywords."""
    text = (title + " " + desc).lower()
    scores = {}
    for cat, keywords in CATEGORIES.items():
        count = sum(1 for kw in keywords if kw in text)
        scores[cat] = count
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "ai-marketing"

def generate_angles(title, category):
    """Generate 5 post angles for a trend using templates."""
    # Base angle templates by category
    angle_templates = {
        "ai-marketing": [
            "Why {TITLE} is the biggest shift in marketing right now",
            "How to get started with {TITLE} (without a massive budget)",
            "The 3 pitfalls nobody talks about with {TITLE}",
            "Why most companies fail at {TITLE}",
            "{TITLE}: Overrated or the real deal?",
        ],
        "ai-tools": [
            "The 3 AI tools that replaced my entire stack",
            "Testing {TITLE}: does it actually save time?",
            "How we cut costs 40% with {TITLE}",
            "The hidden gotcha nobody mentions about {TITLE}",
            "Why {TITLE} is the tool you should try this week",
        ],
        "content": [
            "How {TITLE} changed our content strategy",
            "The {TITLE} playbook: 3 tactics that work in 2025",
            "Stop creating content like it's 2020. Try {TITLE}",
            "Why {TITLE} flops for most teams (and how to fix it)",
            "{TITLE} in 60 seconds: the TL;DR",
        ],
        "ads": [
            "How {TITLE} boosted our ROAS by 3x",
            "The {TITLE} strategy that broke our ad account",
            "Why {TITLE} is banned in most ad accounts (and how to use it legally)",
            "{TITLE}: the ad hack nobody's talking about",
            "How we spent $100 on {TITLE} and what happened",
        ],
        "growth": [
            "How {TITLE} went from experiment to 40% of our revenue",
            "The {TITLE} framework: 3 steps that compound",
            "Why {TITLE} is a growth trap (and when it's not)",
            "{TITLE}: the metric 90% of teams ignore",
            "How to A/B test {TITLE} without losing sleep",
        ],
        "agency": [
            "How {TITLE} changed how we bill clients",
            "The {TITLE} conversation that won us a 6-figure retainer",
            "Why {TITLE} is the best sales tool in your agency",
            "How we use {TITLE} to fire bad clients",
            "{TITLE} for agencies: stop doing X, start doing Y",
        ],
    }

    templates = angle_templates.get(category, angle_templates["ai-marketing"])
    angles = [t.replace("{TITLE}", title) for t in templates[:5]]
    return angles

def assign_badges(title, date):
    """Assign hot/warm/new badges based on recency and relevance."""
    badges = []
    today = datetime.now(timezone.utc).date()
    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
        days_old = (today - d).days
        if days_old <= 3:
            badges.append("new")
        elif days_old <= 7:
            badges.append("warm")
    except:
        pass
    # Hot = high signal keywords
    hot_words = ["breakthrough", "launch", "new", "ai", "automation", "agent", "llm", "40%", "3x", "break", "shut down"]
    if any(w in title.lower() for w in hot_words):
        badges.append("hot")
    else:
        badges.append("warm")
    return badges if badges else ["warm"]

def main():
    print("Fetching live trends...")

    gt = fetch_google_trends()
    print(f"  Google Trends: {len(gt)}")

    hn = fetch_hn_stories()
    print(f"  Hacker News: {len(hn)}")

    rd = fetch_reddit()
    print(f"  Reddit: {len(rd)}")

    all_trends = gt + hn + rd
    print(f"Total raw: {len(all_trends)}")

    # Deduplicate by title
    seen = set()
    unique = []
    for t in all_trends:
        key = t["title"].lower()[:50]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    print(f"After dedup: {len(unique)}")

    # Categorize + enrich
    categorized = {}
    for t in unique:
        cat = categorize_trend(t["title"], t["desc"])
        badges = assign_badges(t["title"], t.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")))
        t["category"] = cat
        t["badges"] = badges
        t["angles"] = generate_angles(t["title"], cat)
        categorized.setdefault(cat, []).append(t)

    # Sort each category by date + relevance, take top 10
    for cat in categorized:
        categorized[cat] = sorted(categorized[cat], key=lambda x: x.get("date", ""), reverse=True)[:10]

    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trends": categorized,
    }

    os.makedirs("static/data", exist_ok=True)
    with open("static/data/trends.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nCategories: {list(categorized.keys())}")
    for cat, items in categorized.items():
        print(f"  {cat}: {len(items)} trends")
    print("\nOutput: static/data/trends.json")

if __name__ == "__main__":
    main()
