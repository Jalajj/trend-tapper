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

The GitHub Actions workflow (.github/workflows/update-trends.yml) runs
this script daily at 9am UTC to refresh the data.
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
        "Why {TOPIC} is the biggest shift happening in marketing right now",
        "How to get started with {TOPIC} before your competitors do",
        "The 3 pitfalls nobody talks about when implementing {TOPIC}",
        "Why most marketing teams fail with {TOPIC}",
        "{TOPIC}: Overrated or the real deal? Here is my take after testing it",
    ],
    "ai-tools": [
        "The 3 AI tools that replaced my entire tech stack this week",
        "Testing {TOPIC}: does it actually save time or just add complexity?",
        "How we cut costs 40% by adopting {TOPIC}",
        "The hidden gotcha nobody mentions about {TOPIC}",
        "Why {TOPIC} is the tool you should try this week (or skip)",
    ],
    "content": [
        "How {TOPIC} changed our entire content strategy in 7 days",
        "The {TOPIC} content playbook: 3 tactics that actually work in 2025",
        "Stop creating content like it is 2020. Try these {TOPIC} approaches instead",
        "Why {TOPIC} content flops for most teams (and how to fix it)",
        "{TOPIC}: content in 60 seconds - the TLDR for busy creators",
    ],
    "ads": [
        "How {TOPIC} boosted our ROAS by 3x in one week",
        "The {TOPIC} ad strategy that broke our ad account (and how we recovered)",
        "Why {TOPIC} gets banned in most ad accounts (and how to use it legally)",
        "{TOPIC}: the ad hack nobody is talking about in 2025",
        "We spent 100 on {TOPIC} and 1000 on lessons. Here is what happened",
    ],
    "automation": [
        "Building my first {TOPIC} automation: 3 mistakes I made (and fixed)",
        "How {TOPIC} replaced 2 hours of daily manual work",
        "The {TOPIC} setup guide: from zero to automated in 2 hours",
        "Why {TOPIC} automation fails (and how to make it stick)",
        "{TOPIC}: the no-code stack that actually works in 2025",
    ],
    "analytics": [
        "How {TOPIC} gave us 3 insights our dashboard has been hiding",
        "The {TOPIC} metric 90% of teams track wrong",
        "Why {TOPIC} is the analytics blind spot killing your decisions",
        "{TOPIC}: the 3 reports you should auto-email to your team",
        "How we caught a 20% revenue leak with {TOPIC} analytics",
    ],
    "agency": [
        "How {TOPIC} changed how we bill clients at our agency",
        "The {TOPIC} conversation that won us a 6-figure retainer",
        "Why {TOPIC} is the best sales tool in our agency toolkit",
        "How we use {TOPIC} to fire bad clients automatically",
        "{TOPIC} for agencies: stop doing X, start doing Y",
    ],
    "growth": [
        "How {TOPIC} went from experiment to 40% of our revenue",
        "The {TOPIC} growth framework: 3 compounding steps",
        "Why {TOPIC} is a growth trap (and when it is the real deal)",
        "{TOPIC}: the metric 90% of growth teams ignore",
        "A/B testing {TOPIC} without slowing down shipping",
    ],
    "crm": [
        "How {TOPIC} helped us recover 15 inactive accounts this month",
        "The {TOPIC} CRM field we added that increased close rate by 25%",
        "Why {TOPIC} in your CRM is worth more than lead lists",
        "{TOPIC}: the CRM automation that qualifies leads before you call",
        "How {TOPIC} predicts which leads will churn (before they do)",
    ],
    "ecommerce": [
        "How {TOPIC} lifted our product page conversions by 31%",
        "The {TOPIC} ecomm checklist: 3 things before you launch",
        "Why {TOPIC} flops on mobile (and how to fix it for good)",
        "{TOPIC}: the one tactic that scales from 100 to 10k orders/day",
        "Running {TOPIC} on a 50 product catalog: here is what works",
    ],
}

CATEGORY_KEYWORDS = {
    "ai-marketing": ["marketing", "ai marketing", "artificial intelligence", "automation", "agent", "ai ", "gpt", "llm", "model", "saas", "startup"],
    "ai-tools": ["ai tool", "ai tools", "chatgpt", "llm", "claude", "midjourney", "cursor", "ai agent", "gpt", "model", "ai ", "tool"],
    "content": ["content", "social media", "linkedin", "tiktok", "youtube", "video", "copywriting", "creator", "blog", "newsletter"],
    "ads": ["advertising", "facebook ads", "google ads", "ppc", "tiktok ads", "programmatic", "conversion", "roas"],
    "automation": ["automation", "workflow", "no-code", "zapier", "integrat", "api", "automate"],
    "analytics": ["analytics", "data", "attribut", "metric", "dashboard", "kpi", "tracking"],
    "agency": ["agency", "client", "pricing", "freelancer", "retainer", "contract"],
    "growth": ["growth", "retention", "acquisition", "funnel", "lead gen", "churn"],
    "crm": ["crm", "salesforce", "hubspot", "apollo", "lever", "pipeline", "prospect"],
    "ecommerce": ["ecommerce", "shopify", "amazon", "shop", "product", "cart", "checkout"],
}


def clean_topic(title):
    """Extract a clean, readable topic from a trend title."""
    # Remove common HN prefixes
    title = re.sub(r'^Show HN:\s*', '', title)
    title = re.sub(r'^Launch HN:\s*', '', title)
    title = re.sub(r'^Ask HN:\s*', '', title)
    title = re.sub(r'^\[Hiring\]\s*', '', title)
    title = re.sub(r'^Product Hunt: ', '', title, flags=re.IGNORECASE)

    # Strip URL fragments at the end
    title = re.sub(r'\s+https?://\S+', '', title)

    # If title has a colon, and the part after the colon is a question or explanation, extract the main subject
    if ":" in title:
        colon_idx = title.index(":")
        after = title[colon_idx+1:].strip()
        # If the part after colon is a question, long explanation, or has "what" / "how" — keep just the main title
        if (after.endswith("?") or len(after) > 30 or after.startswith(("What ", "How ", "Why "))):
            title = title[:colon_idx].strip()

    # If title is a question, extract the noun phrase
    if title.strip().endswith("?"):
        # Strip question words to get the core subject
        for q in ["How accurate have", "What are the", "Why is", "How did", "Why did",
                   "What is", "How to", "Is ", "Are "]:
            if title.startswith(q):
                title = title[len(q):].strip()
        title = title.rstrip("?").strip()
        # Take just the key noun phrase (first 4-5 words)
        words = title.split()
        if len(words) > 5:
            # Keep first 5 words as the topic
            title = " ".join(words[:5])

    # Truncate long titles
    if len(title) > 50:
        words = title.split()
        for cut in range(5, len(words) + 1):
            short = " ".join(words[:cut])
            if len(short) <= 48:
                title = short
                break

    title = title.rstrip(".").strip()
    return title


def generate_angles_for_category(cat, title):
    """Generate 5 category-specific post angles for a trend title."""
    templates = ANGLE_TEMPLATES.get(cat, ANGLE_TEMPLATES["ai-marketing"])
    topic = clean_topic(title)

    angles = []
    for tmpl in templates[:5]:
        result = tmpl.replace("{TOPIC}", topic)
        angles.append(result)
    return angles


def categorize(text):
    """Return all categories a trend is relevant to."""
    text_lower = text.lower()
    cats = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            cats.append(cat)
    # If no specific match, assign to both ai-marketing and ai-tools (high overlap)
    if not cats:
        return ["ai-marketing", "ai-tools"]
    return cats


def assign_badges(title):
    """Assign hot/warm/cool/new badges.
    All trends from today are 'hot' (they're literally trending right now).
    """
    badges = ["hot", "new"]
    return badges


def fetch_hn():
    """Fetch from Hacker News API — top + newest stories."""
    trends = []
    try:
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
        top_ids = r.json()[:150]
        r2 = requests.get("https://hacker-news.firebaseio.com/v0/newstories.json", timeout=15)
        new_ids = r2.json()[:150]
        all_ids = list(dict.fromkeys(top_ids + new_ids))

        ai_keywords = ["ai", "ml", "llm", "gpt", "machine learning", "automation",
                      "agent", "model", "open-source", "saas", "startup", "tool",
                      "launch", "data", "api", "no-code", "cursor"]
        count = 0
        for item_id in all_ids:
            if count >= 15:
                break
            try:
                item = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=10
                ).json()
                title = item.get("title", "")
                url = item.get("url", "")
                # Check if relevant to AI/marketing
                combined = (title + " " + url)[:500]
                if any(kw in combined.lower() for kw in ai_keywords) and len(title) > 10:
                    trends.append({
                        "title": title,
                        "desc": url or item.get("text", "")[:200] or "HN story discussion",
                        "source_url": f"https://news.ycombinator.com/item?id={item_id}",
                        "source_name": "Hacker News",
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    })
                    count += 1
            except Exception:
                pass
    except Exception as e:
        print(f"  HN API: {e}")
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
            kws = ["ai", "marketing", "automation", "content", "social", "growth",
                   "seo", "tool", "launch", "saas", "agent", "chatbot"]
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
        print(f"  Product Hunt: {e}")
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


def fetch_marketing_blogs():
    """Fetch from marketing blog RSS feeds."""
    trends = []
    feeds = {
        "https://ahrefs.com/blog/rss/": "Ahrefs Blog",
        "https://backlinko.co/feed": "Backlinko",
        "https://neilpatel.com/blog/feed/": "Neil Patel",
        "https://blog.hubspot.com/marketing/rss": "HubSpot Marketing",
        "https://www.semrush.com/blog/feed/": "SEMrush",
        "https://blog.ahrefs.com/rss/": "Ahrefs",
        "https://convert.com/blog/feed/": "Convert.com",
    }
    for url, name in feeds.items():
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (TrendTapper)"})
            d = feedparser.parse(r.text)
            for e in d.entries[:8]:
                title = e.title
                # Filter for actionable content
                skip_words = ["weekly", "roundup", "best of", "top tools", "deals", "giveaway"]
                if len(title) > 15 and not any(sw in title.lower() for sw in skip_words):
                    desc = BeautifulSoup(e.get("summary", ""), "html.parser").get_text()[:200] if e.get("summary") else ""
                    trends.append({
                        "title": title,
                        "desc": desc or f"Latest post from {name}",
                        "source_url": e.link,
                        "source_name": name,
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    })
        except Exception:
            pass
    return trends[:15]


def main():
    print("Fetching live trends...")

    hn = fetch_hn()
    print(f"  Hacker News: {len(hn)} relevant stories")

    ph = fetch_product_hunt()
    print(f"  Product Hunt: {len(ph)} tools")

    rd = fetch_reddit()
    print(f"  Reddit: {len(rd)} discussions")

    mb = fetch_marketing_blogs()
    print(f"  Marketing blogs: {len(mb)} articles")

    all_trends = hn + ph + rd + mb
    print(f"Raw total: {len(all_trends)}")

    # Deduplicate by title
    seen = set()
    unique = []
    for t in all_trends:
        key = t["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    print(f"After dedup: {len(unique)}")

    # Categorize and generate category-specific angles
    categorized = {}
    for t in unique:
        text = t["title"] + " " + t["desc"]
        cats = categorize(text)
        badges = assign_badges(t["title"])
        t["badges"] = badges

        # Generate DIFFERENT angles for EACH relevant category
        t["category_angles"] = {}
        for cat in cats:
            t["category_angles"][cat] = generate_angles_for_category(cat, t["title"])

        # Default angles from primary (first) category
        t["primary_category"] = cats[0]
        t["angles"] = t["category_angles"][cats[0]]

        # Add to each relevant category's list
        for cat in cats:
            categorized.setdefault(cat, []).append(t)

    # Build output
    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trends": {},
    }

    for cat, items in categorized.items():
        # Sort by date desc, prioritize multi-category trends
        items = sorted(items, key=lambda x: (x.get("date", ""), -len(x["category_angles"])), reverse=True)[:10]
        output["trends"][cat] = items
        print(f"  {cat}: {len(items)} trends")

    os.makedirs("static/data", exist_ok=True)
    with open("static/data/trends.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved: static/data/trends.json")


if __name__ == "__main__":
    main()
