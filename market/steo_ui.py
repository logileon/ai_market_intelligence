"""Read-only STEO dashboard; network refreshes run through CLI/Actions."""
import pandas as pd
import plotly.express as px
import streamlit as st
from .storage import ROOT
from .refining import chronology
from .steo import read_steo, aggregate, compare, series_meta, SPECS

def render_steo():
    st.subheader("EIA STEO: liquid fuels balances & forecasts")
    vintages, values = read_steo()
    if vintages.empty:
        st.info("No STEO vintages are loaded. Run python update_steo.py or the Update market data workflow.")
        return
    labels = {}
    for row in vintages.itertuples():
        suffix = f" · file {row.sha256[:8]}" if (vintages.release_month == row.release_month).sum() > 1 else ""
        labels[row.vintage_id] = f"{row.release_month} (released {row.released_at}){suffix}"
    col1, col2, col3 = st.columns([2,2,1])
    ids = vintages.sort_values(["release_month", "retrieved_at"]).vintage_id.tolist()
    current = col1.selectbox("STEO vintage", ids, format_func=labels.get, index=len(ids)-1, key="steo_current")
    baselines = [x for x in ids if x != current]
    baseline = col2.selectbox("Comparison vintage", baselines, format_func=labels.get, index=len(baselines)-1, key="steo_baseline") if baselines else None
    frequency = col3.selectbox("STEO frequency", ["Month","Quarter","Year"], index=1, key="steo_frequency")
    meta = vintages.set_index("vintage_id").loc[current]
    st.caption(f"Vintage {meta.release_month} · forecast completed {meta.completed_at} · common historical cutoff in the EIA workbook: {meta.historical_cutoff}. "
               "History / estimate does not mean final actual data: EIA can revise historical periods.")
    if (pd.Timestamp.now().to_period("M") - pd.Period(vintages.release_month.max(), freq="M")).n > 1:
        st.warning(f"Latest saved vintage: {vintages.release_month.max()}. Check the STEO refresh in GitHub Actions.")
    available = values[values.vintage_id == current]
    years = sorted(available.period.str[:4].unique())
    selected_years = st.multiselect("Years shown on STEO charts", years,
        default=[y for y in years if int(y) >= int(meta.release_month[:4])], key="steo_years")
    all_agg = aggregate(values, frequency)
    visible = all_agg[(all_agg.vintage_id == current)&(all_agg.period.str[:4].isin(selected_years))]
    annual = aggregate(values, "Year")
    forecast_years = sorted(annual[(annual.vintage_id == current)&(annual.forecast_months > 0)].period.unique())
    if forecast_years:
        preferred = str(int(meta.release_month[:4])+1)
        headline_year = st.selectbox("Headline indicator year", forecast_years,
            index=forecast_years.index(preferred) if preferred in forecast_years else 0, key="steo_headline_year")
        st.markdown(f"**{headline_year} averages from the selected EIA vintage**")
        for codes in [["papr_world","patc_world","balance"],["BREPUUS","WTIPUUS"]]:
            for col, code in zip(st.columns(len(codes)), codes):
                item = annual[(annual.vintage_id == current)&(annual.series == code)&(annual.period == headline_year)]
                old = annual[(annual.vintage_id == baseline)&(annual.series == code)&(annual.period == headline_year)]
                name, unit, _ = series_meta(code)
                val = item.iloc[0].value if not item.empty else None
                delta = val-old.iloc[0].value if pd.notna(val) and not old.empty and pd.notna(old.iloc[0].value) else None
                col.metric(name, "No data" if pd.isna(val) else f"{val:,.2f}",
                    delta=f"{delta:+.2f} vs {vintages.set_index('vintage_id').loc[baseline].release_month}" if delta is not None else None,
                    delta_color="off")
                col.caption(f"{unit} · {item.iloc[0].status}" if not item.empty else unit)
    st.markdown("**World liquid fuels supply & demand**")
    st.caption("EIA coverage is petroleum and other liquid fuels: crude oil, other liquids including biofuels, and refinery processing gains. This scope is broader than crude oil production.")
    demand_supply = visible[visible.series.isin(["papr_world","patc_world"])].copy()
    if not demand_supply.empty:
        demand_supply["Indicator"] = demand_supply.series.map(lambda c: series_meta(c)[0])
        st.plotly_chart(chronology(px.line(demand_supply, x="period", y="value", color="Indicator", line_dash="status",
            markers=True, labels={"period":"Period","value":"million b/d","status":"Period type"},
            line_dash_map={"EIA forecast":"dash","History / estimate":"solid","History + forecast":"dot","Incomplete period":"dot"}), visible.period), use_container_width=True)
        balance = visible[visible.series == "balance"].copy()
        balance["Sign"] = balance.value.map(lambda v: "Stock build (+)" if v >= 0 else "Stock draw (−)")
        st.plotly_chart(chronology(px.bar(balance,x="period",y="value",color="Sign",
            color_discrete_map={"Stock build (+)":"#4DD6BB","Stock draw (−)":"#FF9676"},
            hover_data=["status"],labels={"period":"Period","value":"Supply minus demand, million b/d"}), balance.period), use_container_width=True)
    else:
        st.info("Select years to display the balance.")
    st.caption("Balance = supply minus demand. It represents implied world stock changes and balancing items rather than observed commercial stocks. "
               "The EIA t3_stchange_world series uses the opposite sign: positive means a stock draw. Ingestion checks the sign reconciliation.")
    st.markdown("**Price & demand forecasts**")
    metric_options = [c for c in SPECS if c not in ("papr_world","patc_world","t3_stchange_world")] + ["patc_world","papr_world","balance","t3_stchange_world"]
    metric = st.selectbox("STEO indicator", metric_options, format_func=lambda c: series_meta(c)[0],
        index=metric_options.index("BREPUUS"), key="steo_metric")
    name, unit, _ = series_meta(metric)
    plotted = all_agg[(all_agg.vintage_id.isin([current,baseline]))&(all_agg.series == metric)&(all_agg.period.str[:4].isin(selected_years))].copy()
    if not plotted.empty:
        plotted["Vintage"] = plotted.vintage_id.map(labels)
        st.plotly_chart(chronology(px.line(plotted,x="period",y="value",color="Vintage",line_dash="status",markers=True,
            labels={"period":"Period","value":unit,"status":"Period type"},title=name), plotted.period), use_container_width=True)
    if baseline:
        st.markdown("**Revision to the selected indicator**")
        delta = compare(all_agg,current,baseline,metric)
        delta = delta[delta.period.str[:4].isin(selected_years)]
        scope = st.radio("Comparison scope",["All selected periods","Forecast periods in both vintages only"], horizontal=True,key="steo_comparison_scope")
        if scope == "Forecast periods in both vintages only":
            delta = delta[(delta.status_current == "EIA forecast")&(delta.status_baseline == "EIA forecast")]
        st.caption(f"Change = selected vintage minus comparison vintage; unit: {unit}. Missing periods stay blank. "
                   "Revisions to history / estimates are distinguished from forecast revisions.")
        if not delta.empty:
            st.plotly_chart(chronology(px.bar(delta,x="period",y="delta",labels={"period":"Period","delta":f"Revision, {unit}"}), delta.period),use_container_width=True)
            table = delta.rename(columns={"period":"Period","value_current":"Selected vintage","value_baseline":"Comparison vintage",
                "delta":"Absolute change","delta_pct":"Δ, %","status_current":"Type: selected","status_baseline":"Type: comparison"})
            st.dataframe(table,hide_index=True,use_container_width=True)
            st.download_button("Download STEO comparison (CSV)",table.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"steo-{metric.replace('$','')}-{meta.release_month}-comparison.csv",mime="text/csv")
        else:
            st.info("No common forecast periods match the selection.")
        st.markdown("**Forecast evolution for a single period**")
        targets = sorted(all_agg[(all_agg.series == metric)&(all_agg.period.str[:4].isin(selected_years))].period.unique())
        if targets:
            target = st.selectbox("Target period",targets,index=len(targets)-1,key="steo_target")
            evolution = all_agg[(all_agg.series == metric)&(all_agg.period == target)].merge(
                vintages[["vintage_id","release_month","released_at","retrieved_at"]],on="vintage_id",validate="many_to_one")
            evolution = evolution.sort_values(["release_month","retrieved_at"])
            evolution["Vintage"] = evolution.vintage_id.map(labels)
            st.plotly_chart(chronology(px.line(evolution,x="Vintage",y="value",markers=True,hover_data=["status"],
                labels={"value":unit},title=f"{name}: {target} across all saved vintages"), evolution["Vintage"]),use_container_width=True)
    with st.expander("STEO methodology, sources & updates"):
        st.markdown("""Monthly values are loaded from original archived EIA XLSX workbooks. Quarterly and annual supply, demand and balance averages are weighted by calendar days. Prices use arithmetic averages of monthly values. Incomplete quarters or years are not calculated; missing values are not replaced with zero.

The forecast boundary comes from Dates / Last Historical Month in each vintage. Periods spanning history and forecast are labelled History + forecast. The common EIA cutoff is approximate: individual historical series may contain estimates.

Refresh using **python update_steo.py** locally or **Update market data → Run workflow** on GitHub. The existing workflow checks the archive alongside the regular data collection. New vintages are added while earlier editions are retained. The latest workbook is rechecked: a revised EIA file is stored as a separate checksum-verified version. Earlier intact editions are cached.

STEO prices are EIA monthly averages, distinct from daily FRED observations. Product forecasts refer to the named US markets; retail and wholesale prices differ. US distillate fuel demand has a broader scope than road diesel.""")
        st.link_button("Official EIA STEO archive","https://www.eia.gov/outlooks/steo/outlook.php")
        st.dataframe(vintages[["release_month","released_at","completed_at","historical_cutoff","retrieved_at","sha256","source_url"]],hide_index=True,use_container_width=True)
        raw_path = ROOT/"data"/meta.raw_path
        if raw_path.is_file():
            st.download_button("Download original EIA workbook for selected vintage",raw_path.read_bytes(),
                file_name=raw_path.name,mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        exported = values.merge(vintages[["vintage_id","release_month","released_at","source_url","sha256"]],on="vintage_id",validate="many_to_one")
        st.download_button("Download all saved STEO data (CSV)",exported.to_csv(index=False).encode("utf-8-sig"),
            file_name="steo-all-vintages.csv",mime="text/csv")

