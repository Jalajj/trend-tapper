from fetch_trends import clean_topic

tests = [
    ("How to Start a Franchise Business (2026 Guide)", "Start a Franchise Business"),
    ("How accurate have Ed Zitron's AI skeptic predictions been?", "Ed Zitron's AI skeptic predictions"),
    ("Launch HN: Nori Robotics (YC S26) - A low-cost humanoid robot for development", "Nori Robotics (YC S26) - A low-cost humanoid robot for development"),
    ("Show HN: Weedout - Safari extension that hides YouTube AI-labeled videos", "Weedout - Safari extension that hides YouTube AI-labeled videos"),
    ("My local model setup on an M4 Pro Mac Mini", "My local model setup on an M4 Pro Mac Mini"),
    ("The ChatGPT/Codex app bundles a full copy of LibreOffice", "ChatGPT/Codex app bundles a full copy of LibreOffice"),
    ("Google Search Is Becoming AI Search: What This Means for Your Brand", "Google Search Is Becoming AI Search"),
    ("Paid Media Forecasting: How to Predict Ad Performance (Without Getting It Wrong)", "Paid Media Forecasting"),
    ("The efficient frontier of LLM inference", "Efficient frontier of LLM inference"),
    ("Inside ChatGPT's Source Preferences: What Query Fanouts Reveal About AI Discoverability", "Inside ChatGPT's Source Preferences"),
    ("Enterprise SEO: What it is & how to build a winning strategy", "Enterprise SEO"),
    ("How to use AI tools for competitor analysis in 2026", "AI tools for competitor analysis in 2026"),
    ("Best PPC Companies of 2026", "Best PPC Companies of 2026"),
    ("The Practical Guide to Google Analytics 4", "Practical Guide to Google Analytics 4"),
    ("The 3 AI tools that replaced my entire tech stack this week", "3 AI tools that replaced my entire tech stack this week"),
    ("Cosmic Agent Plugins", "Cosmic Agent Plugins"),
    ("How bicycle coaster brakes work (2018)", "Bicycle coaster brakes work"),
    ("Mayor says 'large chunks' of Wellington council Deloitte report written by AI", "Mayor says 'large chunks' of Wellington council Deloitte report written by AI"),
    ("A/B testing SEO tactics: 15 experiments that worked", "A/B testing SEO tactics: 15 experiments that worked"),
]

all_pass = True
for title, expected in tests:
    result = clean_topic(title)
    status = "OK" if result == expected else "FAIL"
    if result != expected:
        all_pass = False
    print(f"  [{status}] {title[:55]}")
    print(f"         -> {result}")
    if result != expected:
        print(f"         (expected: {expected})")
    print()

print("ALL PASS" if all_pass else "SOME FAILED")
