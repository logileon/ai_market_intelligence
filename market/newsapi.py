"""NewsAPI metadata ingestion; secret is sent only in a request header."""
import os
import re
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import requests
from .analysis import analyze, relevant
from .collect import canonical_url, clean

ENDPOINT = "https://newsapi.org/v2/everything"

def parse_articles(payload, now):
    if payload.get("status") != "ok":
        raise ValueError("NewsAPI rejected request")
    rows = []
    for item in payload.get("articles", []):
        title = clean(item.get("title") or "")[:400]
        summary = clean(item.get("description") or "")[:350]
        url = canonical_url(item.get("url") or "")
        if not title or title == "[Removed]" or not url or re.search(r"[\u0400-\u04ff]", title + " " + summary) or not relevant(title + " " + summary):
            continue
        published = None
        try:
            dt = datetime.fromisoformat(item.get("publishedAt", "").replace("Z", "+00:00"))
            if dt.tzinfo and dt <= datetime.fromisoformat(now) + timedelta(days=1):
                published = dt.astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, AttributeError):
            pass
        publisher = clean((item.get("source") or {}).get("name") or "Unknown")[:100]
        rows.append(dict(id=sha256(url.encode()).hexdigest(), title=title, summary=summary,
                         url=url, source=f"NewsAPI / {publisher}", published_at=published,
                         fetched_at=now, **analyze(title, summary)))
    return rows

def fetch_newsapi(now, key=None):
    key = key or os.getenv("NEWSAPI_KEY", "").strip()
    if not key:
        return "NewsAPI", [], None
    try:
        start = (datetime.fromisoformat(now) - timedelta(days=7)).date().isoformat()
        rows = []
        for language, query in [("en", '("crude oil" OR refinery OR diesel OR gasoline OR OPEC)')]:
            response = requests.get(ENDPOINT, headers={"X-Api-Key": key},
                params=dict(q=query, language=language, sortBy="publishedAt", pageSize=100, page=1,
                            searchIn="title,description", **{"from": start}), timeout=(8, 25))
            if response.status_code != 200:
                return "NewsAPI", [], f"HTTP {response.status_code}; check the NewsAPI key, quota and plan"
            rows.extend(parse_articles(response.json(), now))
        return "NewsAPI", rows, None
    except Exception:
        return "NewsAPI", [], "NewsAPI: network or response error; saved history preserved"
