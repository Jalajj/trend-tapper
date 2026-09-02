#!/usr/bin/env python3
"""
Fetches live marketing/AI trends from multiple free sources and generates
category-specific post angles for each trend.

Sources:
1. Hacker News API (top + newest stories with AI/tech keywords)
2. Product Hunt RSS feed
3. Reddit hot posts from marketing subreddits

Output: static/data/trends.json — each trend appears with angles for
ALL relevant categories it could apply to.
"""

import json
import os
import re
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

# Category-specific angle templates
# Each trend gets a DIFFERENT set of 5 angles per category it's relevant to
ANGLE_TEMPLATES = {
    "ai-marketing": [
        "Why {TITLE} is the biggest shift happening in marketing right now",
        "How to get started with {TITLE} before your competitors do",
        "The 3 pitfalls nobody talks about when implementing {TITLE}",
        "Why most marketing teams fail with {TITLE}",
        "{TITLE}: Overrated or the real deal? Here's my take after testing it",
    ],
    "ai-tools": [
        "The 3 AI tools that replaced my entire tech stack this week",
        "Testing {TITLE}: does it actually save time or just add complexity?",
        "How we cut costs 40% by adopting {TITLE}",
        "The hidden gotcha nobody mentions about {TITLE}",
        "Why {TITLE} is the tool you should try this week (or skip)",
    ],
    "content": [
        "How {TITLE} changed our entire content strategy in 7 days",
        "The {TITLE} content playbook: 3 tactics that actually work in 2025",
        "Stop creating content like it is 2020. Try these {TITLE} approaches instead",
        "Why {TITLE} content flops for most teams (and how to fix it)",
        "{TITLE}: content in 60 seconds — the TLDR for busy creators",
    ],
    "ads": [
        "How {TITLE} boosted our ROAS by 3x in one week",
        "The {TITLE} ad strategy that broke our ad account (and how we recovered)",
        "Why {TITLE} gets banned in most ad accounts (and how to use it legally)",
        "{TITLE}: the ad hack nobody is talking about in 2025",
        "We spent 100 on {TITLE} and 1000 on lessons. Here is what happened",
    ],
    "automation": [
        "Building my first {TITLE} automation: 3 mistakes I made (and fixed)",
        "How {TITLE} replaced 2 hours of daily manual work",
        "The {TITLE} setup guide: from zero to automated in 2 hours",
        "Why {TITLE} automation fails (and how to make it stick)",
        "{TITLE}: the no-code stack that actually works in 2025",
    ],
    "analytics": [
        "How {TITLE} gave us 3 insights our dashboard has been hiding",
        "The {TITLE} metric 90% of teams track wrong",
        "Why {TITLE} is the analytics blind spot killing your decisions",
        "{TITLE}: the 3 reports you should auto-email to your team",
        "How we caught a 20% revenue leak with {TITLE} analytics",
    ],
    "agency": [
        "How {TITLE} changed how we bill clients at our agency",
        "The {TITLE} conversation that won us a 6-figure retainer",
        "Why {TITLE} is the best sales tool in our agency toolkit",
        "How we use {TITLE} to fire bad clients automatically",
        "{TITLE} for agencies: stop doing X, start doing Y",
    ],
    "growth": [
        "How {TITLE} went from experiment to 40% of our revenue",
        "The {TITLE} growth framework: 3 compounding steps",
        "Why {TITLE} is a growth trap (and when it is the real deal)",
        "{TITLE}: the metric 90% of growth teams ignore",
        "A/B testing {TITLE} without slowing down shipping",
    ],
    "crm": [
        "How {TITLE} helped us recover 15 inactive accounts this month",
        "The {TITLE} CRM field we added that increased close rate by 25%",
        "Why {TITLE} in your CRM is worth more than lead lists",
        "{TITLE}: the CRM automation that qualifies leads before you call",
        "How {TITLE} predicts which leads will churn (before they do)",
    ],
    "ecommerce": [
        "How {TITLE} lifted our product page conversions by 31%",
        "The {TITLE} ecomm checklist: 3 things before you launch",
        "Why {TITLE} flops on mobile (and how to fix it for good)",
        "{TITLE}: the one tactic that scales from 100 to 10k orders/day",
        "Running {TITLE} on a 50 product catalog: here is what works"],
}

CATEGORY_KEYWORDS = {
    "ai-marketing": ["marketing", "ai marketing", "artificial intelligence", "automation", "agent"],
    "ai-tools": ["ai tool", "ai tools", "chatgpt", "llm", "claude", "midjourney", "cursor", "ai agent", "gpt", "model"],
    "content": ["content", "social media", "linkedin", "tiktok", "youtube", "video", "copywriting", "creator", "blog", "newsletter", "seo", "seo"],
    "ads": ["advertising", "facebook ads", "google ads", "ppc", "tiktok ads", "programmatic", "conversion", "roas"],
    "automation": ["automation", "workflow", "no-code", "zapier", "make", "integrat", "api", "automate"],
    "analytics": ["analytics", "data", "attribut", "metric", "dashboard", "bi ", "kpi", "tracking"],
    "agency": ["agency", "client", "pricing", "freelancer", "retainer", "contract", "outsourcing"],
    "growth": ["growth", "conversion", "retention", "acquisition", "funnel", "lead gen", "churn"],
    "crm": ["crm", "salesforce", "hubspot", "apollo", "lever", "pipeline", "prospect"],
    "ecommerce": ["ecommerce", "shopify", "amazon", "shop", "product", "cart", "checkout"],
}

def categorize(text):
    """Return all categories a trend is relevant to."""
    text_lower = text.lower()
    cats = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            cats.append(cat)
    return cats if cats else ["ai-marketing"]

def assign_badges(title):
    """Assign hot/warm/cool/new badges."""
    badges = []
    hot_words = ["launch", "new", "breakthrough", "40%", "3x", "break", "shut down",
                 "catching", "demand", "caught", "raises", "funding", "raises",
                 "bust", "scandal", "ban", "banned", "shut", "collapse"]
    if any(w in title.lower() for w in hot_words):
        badges.append("hot")
    else:
        badges.append("warm")
    badges.append("new")
    return badges

def fetch_hn_top():
    """Fetch from Hacker News API — top + newest stories."""
    trends = []
    try:
        # Get top stories
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
        top_ids = r.json()[:150]

        # Also get newest
        r2 = requests.get("https://hacker-news.firebaseio.com/v0/newstories.json", timeout=15)
        new_ids = r2.json()[:150]

        all_ids = list(dict.fromkeys(top_ids + new_ids))  # dedupe, preserve order

        ai_keywords = ["ai", "ml", "llm", "gpt", "machine learning", "automation",
                      "agent", "model", "open-source", "saas", "startup", "tool",
                      "launch", "data", "api", "no-code", "cursor"]
        count = 0
        for item_id in all_ids:
            if count >= 15: break
            try:
                item = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=10
                ).json()
                title = item.get("title", "")
                url = item.get("url", "")
                text = (item.get("text") or "").lower()

                # Check title + url for AI keywords
                combined = (title + " " + url + " " + text)[:500]
                if any(kw in combined.lower() for kw in ai_keywords) and len(title) > 10:
                    trends.append({
                        "title": title,
                        "desc": url or text[:200] or "HN story",
                        "source_url": f"https://news.ycombinator.com/item?id={item_id}",
                        "source_name": "Hacker News",
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    })
                    count += 1
            except:
                pass
    except Exception as e:
        print(f"HN API: {e}")
    return trends

def fetch_product_hunt():
    """Fetch from Product Hunt RSS."""
    trends = []
    try:
        r = requests.get("https://www.producthunt.com/feed", timeout=15,
                         headers={"User-Agent": "Mozilla/5.0 (TrendTapper)"})
        d = feedparser.parse(r.text)
        for e in d.entries[:30]:
            title = e.title
            # Filter for relevant
            kws = ["ai", "marketing", "automation", "content", "social", "growth",
                   "seo", "seo", "tool", "launch", "saas", "agent", "chatbot"]
            if any(kw in title.lower() for kw in kws) and len(title) > 8:
                desc = e.get("summary", "")
                desc = BeautifulSoup(desc, "html.parser").get_text()[:200] if desc else ""
                trends.append({
                    "title": title,
                    "desc": desc or "Featured on Product Hunt today",
                    "source_url": e.link,
                    "source_name": "Product Hunt",
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                })
    except Exception as e:
        print(f"Product Hunt: {e}")
    return trends[:10]

def fetch_reddit():
    """Fetch from Reddit marketing subreddits."""
    trends = []
    subs = ["marketing", "digital_marketing", "growthhacking", "content_marketing"]
    for sub in subs:
        try:
            r = requests.get(
                f"https://reddit.com/r/{sub}/hot.json?limit=10", timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (TrendTapper)"}
            )
            if r.status_code != 200:
                continue
            data = r.json()
            for post in data.get("data", {}).get("children", []):
                p = post["data"]
                title = p.get("title", "")
                # Filter out low-quality
                if len(title) > 15 and not title.startswith(("[", "Weekly", "Megathread", "Show:")):
                    trends.append({
                        "title": title,
                        "desc": p.get("selftext", "")[:200] or f"Popular discussion on r/{sub}",
                        "source_url": f"https://reddit.com/{p.get('permalink', '')}",
                        "source_name": f"r/{sub}",
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    })
                if len(trends) >= 30:
                    break
        except Exception as e:
            print(f"  r/{sub}: {e}")
    return trends[:12]

def main():
    print("Fetching live trends...")

    hn = fetch_hn_top()
    print(f"  Hacker News: {len(hn)} relevant stories")

    ph = fetch_product_hunt()
    print(f"  Product Hunt: {len(ph)} tools")

    rd = fetch_reddit()
    print(f"  Reddit: {len(rd)} discussions")

    all_trends = hn + ph + rd
    print(f"Raw total: {len(all_trends)}")

    # Deduplicate by title (keep first occurrence)
    seen = set()
    unique = []
    for t in all_trends:
        key = t["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    print(f"After dedup: {len(unique)}")

    # Categorize each trend and generate category-specific angles
    categorized = {}
    for t in unique:
        text = t["title"] + " " + t["desc"]
        cats = categorize(text)
        badges = assign_badges(t["title"])
        t["badges"] = badges

        # Generate angles for EACH relevant category
        t["category_angles"] = {}
        for cat in cats:
            templates = ANGLE_TEMPLATES.get(cat, ANGLE_TEMPLATES["ai-marketing"])
            t["category_angles"][cat] = [a.replace("{TITLE}", t["title"]) for a in templates[:5]]

        # Also store the primary category + its angles for the default view
        t["primary_category"] = cats[0]
        t["angles"] = t["category_angles"][cats[0]]

        for cat in cats:
            categorized.setdefault(cat, []).append(t)

    # Limit per category, sort by date
    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trends": {},
    }

    for cat, items in categorized.items():
        # Sort by date desc, then by number of categories (more relevant = higher)
        items = sorted(items, key=lambda x: (x.get("date",""), -len(x["category_angles"])), reverse=True)[:10]
        output["trends"][cat] = items
        print(f"  {cat}: {len(items)} trends")

    os.makedirs("static/data", exist_ok=True)
    with open("static/data/trends.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved: static/data/trends.json")

if __name__ == "__main__":
    main()
