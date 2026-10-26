"""Fetch RSS metadata and FRED CSV; never fetch full news articles."""
import calendar
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from io import StringIO
import json
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import feedparser
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .analysis import analyze, relevant
from .storage import ROOT, DB, initialize, connect, save_news, log_run

SERIES = {
    "DCOILBRENTEU": {"name": "Brent", "unit": "USD/bbl"},
    "DCOILWTICO": {"name": "WTI", "unit": "USD/bbl"},
    "DGASUSGULF": {"name": "US Gulf Coast conventional gasoline", "unit": "USD/gal"},
    "DGASNYH": {"name": "New York Harbor gasoline", "unit": "USD/gal"},
    "DHOILNYH": {"name": "New York Harbor No. 2 heating oil", "unit": "USD/gal"},
    "DDFUELUSGULF": {"name": "US Gulf Coast ULSD", "unit": "USD/gal"},
}
MAX_BYTES = 5_000_000

class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style"): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def clean(value):
    parser = TextOnly(); parser.feed(str(value))
    return re.sub(r"\s+", " ", unescape(" ".join(parser.parts))).strip()

def canonical_url(url):
    p = urlsplit(url)
    if p.scheme.lower() not in ("https", "http") or not p.netloc: return ""
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid")]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", urlencode(sorted(query)), ""))

def get_bytes(url):
    with requests.Session() as session:
        session.headers["User-Agent"] = "OilMarketPortfolio/1.0 (RSS metadata reader)"
        session.mount("https://", HTTPAdapter(max_retries=Retry(total=1, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])))
        with session.get(url, timeout=(8, 20), stream=True) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES: raise ValueError("Response exceeds 5 MB")
                chunks.append(chunk)
            return b"".join(chunks)

def parse_feed(body, source, now):
    feed = feedparser.parse(body)
    if not feed.entries:
        raise ValueError("RSS/Atom contains no entries (or endpoint returned HTML)")
    rows = []
    for entry in feed.entries[:150]:
        title = clean(entry.get("title", ""))[:400]
        summary = clean(entry.get("summary", ""))[:350]
        url = canonical_url(entry.get("link", ""))
        if not title or not url or re.search(r"[\u0400-\u04ff]", title + " " + summary) or not relevant(title + " " + summary): continue
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published = None
        if parsed:
            try:
                dt = datetime.fromtimestamp(calendar.timegm(parsed), timezone.utc)
                if dt <= datetime.fromisoformat(now) + timedelta(days=1): published = dt.isoformat()
            except (ValueError, OverflowError, TypeError): pass
        rows.append(dict(id=sha256(url.encode()).hexdigest(), title=title, summary=summary, url=url,
                         source=source, published_at=published, fetched_at=now, **analyze(title, summary)))
    return rows

def fetch_feed(source, now):
    try:
        rows = parse_feed(get_bytes(source["url"]), source["name"], now)
        return source["name"], rows, None
    except Exception as exc:
        return source["name"], [], f"{type(exc).__name__}: {exc}"

def parse_prices(body, series):
    frame = pd.read_csv(StringIO(body.decode("utf-8-sig")))
    if series not in frame or len(frame.columns) != 2: raise ValueError("Unexpected FRED CSV schema")
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna().drop_duplicates("date", keep="last")
    frame = frame[frame["date"] <= pd.Timestamp.now(tz="UTC")]
    if frame.empty: raise ValueError("No valid price observations")
    return [(d.strftime("%Y-%m-%d"), float(v), series, f"https://fred.stlouisfed.org/series/{series}") for d, v in frame.itertuples(index=False, name=None)]

def fetch_price(series):
    try:
        start = (datetime.now(timezone.utc) - timedelta(days=365*5)).date().isoformat()
        rows = parse_prices(get_bytes(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={start}"), series)
        return series, rows, None
    except Exception as exc:
        return series, [], f"{type(exc).__name__}: {exc}"

def update(path=DB):
    initialize(path)
    now = datetime.now(timezone.utc).isoformat()
    sources = [s for s in json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8")) if s.get("enabled", True)]
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for name, rows, error in pool.map(lambda s: fetch_feed(s, now), sources):
            added = save_news(rows, path) if not error else 0
            result = dict(source=name, status="error" if error else "ok", items=added,
                          detail=error or f"Relevant entries: {len(rows)}; new: {added}")
            log_run(now, **result, path=path); results.append(result)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for series, rows, error in pool.map(fetch_price, SERIES):
            if not error:
                with connect(path) as con:
                    con.executemany("INSERT OR REPLACE INTO prices VALUES (?,?,?,?)", rows)
            result = dict(source=f"FRED / EIA {series}", status="error" if error else "ok", items=len(rows),
                          detail=error or f"{SERIES[series]['name']}; {SERIES[series]['unit']}")
            log_run(now, **result, path=path); results.append(result)
    from .newsapi import fetch_newsapi
    import os
    name, rows, error = fetch_newsapi(now)
    added = save_news(rows, path) if not error else 0
    result = dict(source=name, status="error" if error else "ok" if os.getenv("NEWSAPI_KEY") else "skipped",
                  items=added, detail=error or (f"Metadata rows: {len(rows)}; new: {added}; English only; max 100 per run, 7-day window" if os.getenv("NEWSAPI_KEY") else "NEWSAPI_KEY not configured; RSS remains active"))
    log_run(now, **result, path=path); results.append(result)
    return results
