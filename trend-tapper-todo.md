# Trend Tapper — Fix Plan

## Bugs Found

1. **JS crash (fatal)**: `index.html` line 181 references `document.getElementById("include-news")` but that checkbox doesn't exist in the HTML. `null.checked` throws TypeError → nothing renders. Line 295 same issue.
2. **clean_topic() broken**: Titles like "How to Start a Franchise Business (2026 Guide)" — not a question (no `?`) — but starts with "How to". Stays as-is. Should extract core topic. Colons also not handling well (e.g. "Cosmic Agent Plugins" is fine, but "Paid Media Forecasting: How to Predict..." → should keep "Paid Media Forecasting").
3. **reset-filters button**: `resetBtn.addEventListener` at line 293 — the element with id="reset-filters" only exists inside the `no-results` div (hidden by default), so `resetBtn` is null → TypeError.
4. **No "Include News" checkbox** in the filter row — need to add it (the JS expects it).

## Fix Plan
- Add the missing "include-news" checkbox to the filter row in HTML
- Remove all `include-news` references from JS (or implement the filter)
- Rewrite `clean_topic()` to: strip question-word prefixes even when no trailing `?`, handle colons smarter, handle "(2026 Guide)" suffixes
- Fix `resetBtn` null reference — guard with `if (resetBtn)` or move button outside no-results
- Regenerate trends.json with fixed script
- Push and verify live