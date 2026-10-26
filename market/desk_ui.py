"""Research desk views: refining economics, conditional balances, data quality."""
import pandas as pd
import plotly.express as px
import streamlit as st
from .collect import SERIES
from .refining import crack_series, CRACKS, scenario_balance, chronology
from .steo import read_steo, aggregate


def render_refining(prices):
    st.subheader("Refining economics · indicative spot crack spreads")
    st.caption("Products: conventional gasoline and ULSD, US Gulf Coast. Crude: WTI Cushing or Brent Europe. Location bases differ; values are USD per barrel of crude input.")
    c1, c2 = st.columns(2)
    crude = c1.selectbox("Crude benchmark", ["DCOILWTICO", "DCOILBRENTEU"], format_func=lambda x: SERIES[x]["name"])
    days = c2.selectbox("Crack spread lookback (days)", [90, 365, 730, 1825], index=1)
    all_cracks = crack_series(prices, crude)
    visible = all_cracks[all_cracks.date >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)]
    if visible.empty:
        st.info("No matched observations in this period. Refresh FRED data; missing prices are not forward-filled.")
    for col, name in zip(st.columns(3), CRACKS):
        item = visible[visible.spread == name].sort_values("date")
        if item.empty:
            col.metric(name, "No data")
            continue
        last = item.iloc[-1]
        previous = item.iloc[-2].value if len(item) > 1 else None
        col.metric(name, f"{last.value:.2f}", delta=f"{last.value-previous:+.2f} vs previous observation" if previous is not None else None, delta_color="off")
        col.caption(f"USD/bbl · {last.date:%Y-%m-%d}")
        age = (pd.Timestamp.now(tz="UTC").normalize() - last.date.normalize()).days
        if age > 10:
            col.warning(f"Last observation: {age} days ago")
    if not visible.empty:
        chart = px.line(visible.sort_values("date"), x="date", y="value", color="spread", labels={"date":"Date", "value":"USD/bbl", "spread":"Crack spread"})
        chart.add_hline(y=0, line_dash="dot")
        st.plotly_chart(chart, use_container_width=True)
        st.download_button("Download crack spreads (CSV)", visible.to_csv(index=False).encode("utf-8-sig"), file_name="crack-spreads.csv", mime="text/csv")
        st.markdown("**Seasonality & historical context**")
        name = st.selectbox("Spread for seasonal comparison", list(CRACKS), index=2)
        history = all_cracks[all_cracks.spread == name].copy()
        history["year"] = history.date.dt.year
        history["month"] = history.date.dt.month
        current_year = pd.Timestamp.now(tz="UTC").year
        past = history[(history.year < current_year) & (history.year >= current_year-5)]
        monthly = past.groupby(["year", "month"], as_index=False).value.mean()
        baseline = monthly.groupby("month").value.agg(["min", "median", "max", "count"]).reset_index()
        this_year = history[history.year == current_year].groupby("month").value.mean().rename("Current year")
        table = baseline.rename(columns={"month":"Month", "min":"Minimum", "median":"Median", "max":"Maximum", "count":"Years in baseline"})
        table = table.merge(this_year, left_on="Month", right_index=True, how="outer").sort_values("Month")
        if not table.empty:
            lines = table.melt(id_vars="Month", value_vars=["Minimum", "Median", "Maximum", "Current year"], var_name="Series", value_name="USD/bbl")
            st.plotly_chart(px.line(lines, x="Month", y="USD/bbl", color="Series", markers=True), use_container_width=True)
            st.dataframe(table, hide_index=True, use_container_width=True)
        st.caption("Baseline: available monthly averages from the previous five calendar years, excluding the current year. The current partial month averages available days. Coverage can differ by month; the historical range is not a forecast interval.")
    with st.expander("Formulas & interpretation", expanded=True):
        st.markdown("""- Gasoline crack: **42 × gasoline (USD/gal) − crude (USD/bbl)**.
- ULSD crack: **42 × ULSD (USD/gal) − crude (USD/bbl)**.
- 3:2:1: **42 × (2 × gasoline + ULSD) / 3 − crude**.

Only dates shared by the underlying series are used. Missing prices are not forward-filled. These are calculated open-data indicators, not exchange-traded futures cracks or the published Gulf Coast LLS 3:2:1 assessment. Conventional gasoline differs from RBOB. No. 2 heating oil is not substituted for ULSD.

A crack spread measures product basket value less crude input cost. Energy, hydrogen, own-use fuel, losses, actual yields, crude quality, freight, maintenance and fixed costs are excluded. A positive crack spread does not guarantee positive refinery profit.""")
        st.link_button("EIA crack spread methodology", "https://www.eia.gov/todayinenergy/detail.php?id=1630")
    with st.expander("Crude benchmarks & underlying prices"):
        if prices.empty:
            st.info("No price observations have been collected yet.")
            return
        pf = prices.copy()
        pf["date"] = pd.to_datetime(pf.date, utc=True)
        pf = pf[pf.date >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)].sort_values("date")
        oil = pf[pf.series.isin(["DCOILWTICO", "DCOILBRENTEU"])].copy()
        if not oil.empty:
            oil["Benchmark"] = oil.series.map(lambda c: SERIES[c]["name"])
            st.plotly_chart(px.line(oil, x="date", y="value", color="Benchmark", labels={"date":"Date", "value":"USD/bbl"}), use_container_width=True)
            wide = oil.pivot(index="date", columns="series", values="value")
            if {"DCOILWTICO", "DCOILBRENTEU"}.issubset(wide.columns):
                spread = (wide.DCOILBRENTEU-wide.DCOILWTICO).dropna().rename("Brent − WTI")
                st.plotly_chart(px.line(spread, labels={"value":"USD/bbl", "date":"Date"}), use_container_width=True)
        st.dataframe(pf, hide_index=True, use_container_width=True)


def render_scenarios():
    st.subheader("Global liquid fuels balance scenario")
    st.caption("Conditional stress test against the selected EIA vintage. Shocks remain constant within the period. Scenario probabilities and price responses are not modelled.")
    vintages, values = read_steo()
    if vintages.empty:
        st.info("Load STEO data to use the scenario tool.")
        return
    ordered = vintages.sort_values(["release_month", "retrieved_at"])
    vid = st.selectbox("Scenario baseline vintage", ordered.vintage_id.tolist(), index=len(ordered)-1,
                       format_func=lambda x: ordered.set_index("vintage_id").loc[x].release_month, key="scenario_vintage")
    frame = aggregate(values, "Quarter")
    frame = frame[(frame.vintage_id == vid) & frame.series.isin(["papr_world", "patc_world"])]
    # Avoid creating a full-quarter forecast from a mixed history/forecast period.
    frame = frame[frame.status == "EIA forecast"].pivot(index="period", columns="series", values="value").dropna()
    if frame.empty:
        st.info("No complete forecast quarters contain both supply and demand.")
        return
    period = st.selectbox("Forecast quarter", sorted(frame.index), key="scenario_period")
    base = frame.loc[period]
    a, b = st.columns(2)
    supply_shock = a.slider("Supply shock (million b/d)", -3.0, 3.0, 0.0, 0.1)
    demand_shock = b.slider("Demand shock (million b/d)", -3.0, 3.0, 0.0, 0.1)
    days = len(pd.date_range(pd.Period(period).start_time, pd.Period(period).end_time, freq="D"))
    balance, barrels = scenario_balance(base.papr_world, base.patc_world, supply_shock, demand_shock, days)
    original = base.papr_world-base.patc_world
    c1, c2, c3 = st.columns(3)
    c1.metric("EIA baseline balance", f"{original:+.2f} million b/d")
    c2.metric("Scenario balance", f"{balance:+.2f} million b/d", f"{balance-original:+.2f} vs baseline", delta_color="off")
    c3.metric("Implied stock change", f"{barrels:+.1f} million barrels")
    st.caption(f"{period}: {days} days. Positive = implied stock build; negative = draw. This is a balancing quantity, not observed commercial stocks. Baseline supply: {base.papr_world:.2f}; demand: {base.patc_world:.2f} million b/d.")
    grid = []
    for demand in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        for supply in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            val, _ = scenario_balance(base.papr_world, base.patc_world, supply, demand, days)
            grid.append({"Demand shock": demand, "Supply shock": supply, "Balance": val})
    matrix = pd.DataFrame(grid).pivot(index="Demand shock", columns="Supply shock", values="Balance")
    st.plotly_chart(px.imshow(matrix, text_auto=".2f", color_continuous_scale="RdBu", color_continuous_midpoint=0,
                             title="Balance sensitivity (million b/d)"), use_container_width=True)
    st.download_button("Download scenario (CSV)", pd.DataFrame([dict(vintage=vid, period=period, days=days,
        supply=base.papr_world, demand=base.patc_world, supply_shock=supply_shock, demand_shock=demand_shock,
        balance=balance, implied_stock_change=barrels)]).to_csv(index=False).encode("utf-8-sig"), file_name="balance-scenario.csv")


def render_quality(news, prices, runs):
    st.subheader("Data quality scorecard")
    st.caption("The dashboard reads a saved snapshot. A successful collection run does not guarantee a recent observation.")
    rows = []
    for code, meta in SERIES.items():
        series = prices[prices.series == code]
        last = pd.to_datetime(series.date, utc=True, errors="coerce").max()
        age = (pd.Timestamp.now(tz="UTC").normalize()-last.normalize()).days if pd.notna(last) else None
        rows.append({"Indicator": meta["name"], "Observations": len(series), "Latest date": str(last.date()) if pd.notna(last) else "No data",
                     "Age (days)": age, "Status": "No data" if age is None else "Check date" if age > 10 else "Available"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    missing = pd.to_datetime(news.published_at, utc=True, errors="coerce").isna().sum()
    st.caption(f"Articles without a publication date: {missing} of {len(news)}. Filters use the collection date as a fallback; the article card still marks the publication date as unavailable.")
    st.info("NewsAPI: English-language search, a 7-day lookback and up to 100 results per run. Coverage is not exhaustive. The Developer plan is for development only and has delays and quotas; production requires an appropriate plan.")
    st.link_button("NewsAPI plans & usage terms", "https://newsapi.org/pricing")
