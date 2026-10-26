from datetime import datetime, timezone
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from market.collect import SERIES
from market.storage import ROOT, read_tables
from market.export import excel_bytes
from market.steo_ui import render_steo
from market.analysis import analyze
from market.desk_ui import render_refining, render_scenarios, render_quality
from market.refining import crack_series
from market.intraday import render_intraday, render_quote_strip

st.set_page_config(page_title="Oil Market Intelligence", page_icon="🛢️", layout="wide")
profile = json.loads((ROOT / "config/profile.json").read_text(encoding="utf-8"))
st.caption("OIL MARKET INTELLIGENCE · RESEARCH DESK")
st.title("Oil Market Intelligence")
st.markdown("Crude oil, refining and trade flows — from market evidence to transparent scenarios.")
news, prices, runs = read_tables()
if not news.empty:
    english_content = ~(news.title.fillna("") + " " + news.summary.fillna("") + " " + news.source.fillna("")).str.contains(r"[\u0400-\u04ff]", regex=True)
    news = news.loc[english_content].copy()
# Reclassify the saved archive so detailed filters work without a network refresh.
if not news.empty:
    tags = pd.DataFrame([analyze(r.title, r.summary or "") for r in news.itertuples()], index=news.index)
    news[["topics", "regions", "signal", "evidence"]] = tags[["topics", "regions", "signal", "evidence"]]

with st.sidebar:
    st.header("About the analyst")
    st.write(profile["name"])
    st.caption(profile["role"])
    st.write(profile["about"])
    for label, key in [("Contact", "contact_url"), ("GitHub", "github_url")]:
        if profile.get(key, "").startswith("https://"): st.link_button(label, profile[key])
    st.divider()
    st.header("News filters")
    query = st.text_input("Search headlines and excerpts", placeholder="Brent, refinery, diesel…")
    source_filter = st.multiselect("Sources", sorted(news.source.unique()))
    topic_filter = st.multiselect("Topics", sorted(set(t for x in news.topics for t in x.split("; "))))
    region_filter = st.multiselect("Regions", sorted(set(t for x in news.regions for t in x.split("; "))))
    days = st.selectbox("News lookback (days)", [7, 30, 90, 365, "All history"], index=1)
    st.caption("English-language edition. All timestamps are UTC. These filters apply to news; price lookbacks are selected separately.")
    if st.button("Reload saved data"): st.rerun()
    st.caption("Data collection runs via update_data.py / GitHub Actions. Dashboard visitors read the saved snapshot.")

filtered = news.copy()
if query:
    filtered = filtered[(filtered.title + " " + filtered.summary.fillna("")).str.contains(query, case=False, regex=False, na=False)]
if source_filter: filtered = filtered[filtered.source.isin(source_filter)]
for column, selected in [("topics", topic_filter), ("regions", region_filter)]:
    if selected: filtered = filtered[filtered[column].map(lambda x: bool(set(x.split("; ")) & set(selected)))]
filtered["effective_date"] = pd.to_datetime(filtered.published_at.fillna(filtered.fetched_at), utc=True, errors="coerce")
if isinstance(days, int):
    filtered = filtered[filtered.effective_date >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)]

if runs.empty:
    st.info("The archive is empty. Run python update_data.py locally or Run workflow in GitHub Actions. The dashboard also supports an empty database.")
else:
    st.caption(f"Latest collection attempt: {runs.iloc[0].started_at} · Archive: {len(news)} articles")
    errors = runs.drop_duplicates("source")
    if (errors.status == "error").any(): st.warning("Some sources are unavailable. Saved history remains accessible; see Sources & data quality for details.")

k1, k2, k3 = st.columns(3)
k1.metric("Articles in selection", len(filtered))
k2.metric("Sources in selection", filtered.source.nunique())
k3.metric("Risk mentions", int(filtered.signal.isin(["Risk mention", "Mixed mentions"]).sum()))
overview, intraday_tab, price_tab, steo_tab, scenario_tab, feed_tab, method_tab, source_tab = st.tabs(["Overview", "Intraday oil", "Crack spreads & refining", "EIA balances & forecasts", "Balance scenarios", "News & export", "Methodology", "Sources & data quality"])

with intraday_tab:
    render_intraday()

with steo_tab:
    render_steo()

with scenario_tab:
    render_scenarios()

with overview:
    render_quote_strip()
    st.subheader("Daily spot reference | EIA / FRED")
    pulse = st.columns(3)
    for col, code in zip(pulse[:2], ["DCOILBRENTEU", "DCOILWTICO"]):
        rows = prices[prices.series == code].sort_values("date")
        if not rows.empty:
            row = rows.iloc[-1]
            col.metric(SERIES[code]["name"], f"{row.value:.2f} USD/bbl")
            col.caption(f"Observation date: {row.date} · EIA/FRED")
    cracks = crack_series(prices)
    rows = cracks[cracks.spread == "3:2:1"].sort_values("date")
    if not rows.empty:
        row = rows.iloc[-1]
        pulse[2].metric("Indicative 3:2:1 / WTI", f"{row.value:.2f} USD/bbl")
        pulse[2].caption(f"Observation date: {row.date:%Y-%m-%d} · US Gulf products")
    st.caption("Open data with publication delays. Observation dates may differ; check freshness under Sources & data quality.")
    st.subheader("News radar")
    st.caption("Article counts measure source attention, not physical market volumes. Articles can carry multiple topic tags.")
    if filtered.empty:
        st.info("No articles match the selection. Adjust the filters or refresh the archive.")
    else:
        daily = filtered.groupby(filtered.effective_date.dt.strftime("%Y-%m-%d")).size().rename("Articles").reset_index()
        st.plotly_chart(px.bar(daily, x="effective_date", y="Articles", labels={"effective_date": "Date (UTC)"}, color_discrete_sequence=["#4DD6BB"]), use_container_width=True)
        left, right = st.columns(2)
        with left:
            counts = filtered.topics.str.split("; ").explode().value_counts().rename_axis("Topic").reset_index(name="Articles")
            st.plotly_chart(px.bar(counts, x="Articles", y="Topic", orientation="h"), use_container_width=True)
        with right:
            counts = filtered.signal.value_counts().rename_axis("Signal").reset_index(name="Articles")
            st.plotly_chart(px.bar(counts, x="Articles", y="Signal", orientation="h"), use_container_width=True)
        st.subheader("Rules-based news digest")
        st.write(f"Selection: {len(filtered)} articles from {filtered.source.nunique()} sources. Most frequent topic: {filtered.topics.str.split('; ').explode().value_counts().index[0]}.")
        st.caption("This digest describes the selected articles. Verify interpretations against the original sources.")
        for row in filtered.sort_values("effective_date", ascending=False).head(5).itertuples():
            st.text(row.title)
            publication = pd.to_datetime(row.published_at, utc=True, errors="coerce")
            date_label = publication.strftime("%Y-%m-%d %H:%M UTC") if pd.notna(publication) else "Publication date unavailable"
            st.caption(f"{date_label} · {row.source} · {row.topics}")
            st.caption(f"{row.signal} · Matched terms: {row.evidence or 'none'}")
            st.link_button("Read original article", row.url)

with price_tab:
    render_refining(prices)

with feed_tab:
    st.subheader("Archive & search")
    st.caption("Search is literal. If the publication date is missing, filters use the first collection timestamp.")
    export_news = filtered.drop(columns=["effective_date"])
    st.download_button("Download Excel: news, prices, cracks & collection log", excel_bytes(export_news, prices, runs), file_name="oil-market-intelligence.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.dataframe(export_news[["published_at", "title", "source", "topics", "regions", "signal", "evidence", "url"]], hide_index=True, use_container_width=True,
        column_config={"url": st.column_config.LinkColumn("Source")})
    page = st.number_input("Excerpt page (10 articles per page)", min_value=1, max_value=max(1, (len(filtered)+9)//10), value=1)
    for row in filtered.iloc[(page-1)*10:page*10].itertuples():
        with st.expander(f"{row.source} · {row.title}"):
            st.text(row.summary or "No excerpt was provided by the source.")
            st.caption(f"{row.published_at or 'Publication date unavailable'} · {row.topics} · {row.regions}")
            st.link_button("Open article", row.url)

with method_tab:
    st.subheader("How the dashboard works")
    st.markdown("""1. Collect RSS/Atom metadata, open FRED price series and optional NewsAPI metadata via NEWSAPI_KEY.
2. Clean HTML, filter for sector relevance, normalise URLs and deduplicate by URL.
3. Store headlines, short excerpts, source links and collection timestamps in SQLite.
4. Apply transparent dictionary rules for topics, regions, risk mentions and matched terms.
5. Display charts, search and Excel exports. Refresh the saved archive through GitHub Actions.

**Interpretation:** classification uses heuristic NLP, without a generative LLM. Negation, context, irony and price impact are not modelled. A risk mention is a dictionary match, not a price forecast. A region tag can describe a reference in the text rather than the event location. Syndicated stories with different URLs can remain as duplicates.

**Research workflow:** sector analysis, Python, ETL, SQL, data quality checks, visualisation, automation and reproducible calculations.

**Coverage:** the dashboard has no licensed Argus/Platts assessments, Russian exchange prices, universal global diesel index or live inventories. No. 2 heating oil is a distinct product and is not substituted for ULSD. For research purposes; not investment advice.
""")

with source_tab:
    st.info("Intraday oil uses official TradingView display widgets (TVC:USOIL / TVC:UKOIL CFDs). The feed loads in each visitor's browser independently of the saved EIA/FRED snapshot and the GitHub collection schedule. Intraday quotes are excluded from exports and crack spread inputs.")
    render_quality(news, prices, runs)
    st.subheader("Data provenance & collection log")
    st.dataframe(pd.DataFrame(json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8"))), hide_index=True, use_container_width=True)
    for code, meta in SERIES.items():
        st.link_button(f"{meta['name']} · {code} · {meta['unit']}", f"https://fred.stlouisfed.org/series/{code}")
    st.caption("EIA is the primary price source; FRED distributes the series. News remains the property of publishers. Only headlines, short excerpts and links are stored; full articles are not downloaded.")
    st.dataframe(runs, hide_index=True, use_container_width=True)
    st.caption("items: new articles for RSS/NewsAPI; validated observations for FRED. Source failures are logged and saved history is retained.")
