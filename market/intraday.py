"""Official TradingView display widgets; no scraping, API key or stored quote data."""
from html import escape
import json
import streamlit as st
import streamlit.components.v1 as components

INSTRUMENTS = {
    "WTI": {"symbol": "TVC:USOIL", "url": "https://www.tradingview.com/symbols/TVC-USOIL/"},
    "Brent": {"symbol": "TVC:UKOIL", "url": "https://www.tradingview.com/symbols/TVC-UKOIL/"},
}
INTERVALS = {"1 minute": "1", "5 minutes": "5", "15 minutes": "15", "1 hour": "60"}
SCRIPTS = {
    "chart": "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js",
    "tickers": "https://s3.tradingview.com/external-embedding/embed-widget-tickers.js",
}


def widget_html(kind, config, link, title, nonce=0):
    """Keep the provider's branding/attribution and fixed public script hosts."""
    script = SCRIPTS[kind]
    settings = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c")
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body{{margin:0;height:100%;background:#0B1422;color:#E8F0F7;font-family:Arial,sans-serif}}
.tradingview-widget-container{{height:100%;width:100%}}
.tradingview-widget-container__widget{{height:calc(100% - 32px);width:100%}}
.tradingview-widget-copyright{{height:32px;line-height:32px;font-size:12px;text-align:center}}
a{{color:#74baff;text-decoration:none}}a:focus-visible{{outline:2px solid #4DD6BB}}</style></head>
<body><div class="tradingview-widget-container" data-reconnect="{int(nonce)}">
<div class="tradingview-widget-container__widget"></div>
<div class="tradingview-widget-copyright"><a href="{escape(link, quote=True)}" rel="noopener nofollow" target="_blank">{escape(title)}</a> by TradingView</div>
<script type="text/javascript" src="{script}" async>{settings}</script>
</div></body></html>'''


def chart_html(benchmark, interval="5", nonce=0):
    instrument = INSTRUMENTS[benchmark]
    if interval not in INTERVALS.values():
        raise ValueError("Unsupported chart interval")
    config = dict(symbol=instrument["symbol"], interval=interval, timezone="Etc/UTC", theme="dark",
                  style="1", locale="en", allow_symbol_change=False, autosize=True, hide_volume=True,
                  hide_top_toolbar=False, hide_side_toolbar=True, hide_legend=False,
                  withdateranges=True, save_image=False, calendar=False,
                  backgroundColor="#0B1422", support_host="https://www.tradingview.com")
    return widget_html("chart", config, instrument["url"], f"{benchmark} CFD chart", nonce)


def ticker_html(nonce=0):
    config = dict(symbols=[dict(proName=meta["symbol"], title=f"{name} CFD | USD/bbl")
                          for name, meta in INSTRUMENTS.items()], colorTheme="dark", isTransparent=False,
                  showSymbolLogo=True, locale="en", width="100%", height="100%")
    return widget_html("tickers", config, "https://www.tradingview.com/markets/futures/quotes-energy/",
                       "Oil market quotes", nonce)


def render_quote_strip():
    st.markdown("**Intraday oil | WTI & Brent CFDs**")
    components.html(ticker_html(st.session_state.get("oil_feed_nonce", 0)), height=150, scrolling=True)
    st.caption("TradingView / TVC CFD quotes, USD/bbl. Updates are supplied directly to your browser during market hours. See Intraday oil for charts and feed details.")


def render_intraday():
    st.subheader("Intraday oil monitor")
    st.caption("WTI and Brent CFD market indicators via official TradingView widgets. Currency: USD per barrel; chart timezone: UTC.")
    c1, c2 = st.columns(2)
    interval_label = c1.selectbox("Candle interval", list(INTERVALS), index=1, key="oil_candle_interval")
    layout = c2.radio("Chart layout", ["Side by side", "Single chart"], horizontal=True, key="oil_chart_layout")
    if st.button("Reconnect quote feed", key="oil_reconnect"):
        st.session_state["oil_feed_nonce"] = st.session_state.get("oil_feed_nonce", 0) + 1
    nonce = st.session_state.get("oil_feed_nonce", 0)
    st.caption("The feed updates automatically as the provider sends new prices. Candle interval controls chart aggregation, not the refresh rate. Closed markets retain the last available price. Check the chart's market status and any delay indicator.")
    if layout == "Single chart":
        selected = st.selectbox("Oil benchmark", list(INSTRUMENTS), key="oil_benchmark")
        st.markdown(f"**{selected} | TVC CFD | USD/bbl**")
        components.html(chart_html(selected, INTERVALS[interval_label], nonce), height=570, scrolling=False)
        st.link_button(f"Open {selected} on TradingView", INSTRUMENTS[selected]["url"])
    else:
        for col, benchmark in zip(st.columns(2), INSTRUMENTS):
            with col:
                st.markdown(f"**{benchmark} | TVC CFD | USD/bbl**")
                components.html(chart_html(benchmark, INTERVALS[interval_label], nonce), height=530, scrolling=False)
                st.link_button(f"Open {benchmark} on TradingView", INSTRUMENTS[benchmark]["url"])
    with st.expander("Source, availability & interpretation", expanded=True):
        st.markdown("""**Source:** TradingView, TVC:USOIL and TVC:UKOIL. These are CFD market indicators, distinct from EIA physical spot assessments and from a specified exchange-traded futures contract. Differences in levels can reflect instrument basis, methodology and timing.

**Updates:** the provider loads current available data when you open the page and sends subsequent updates to the embedded widgets. No additional API key or GitHub Actions run is required for this display. Availability and any delay are controlled by the provider; no fixed latency is guaranteed.

**Use in analysis:** embedded intraday quotes are display-only. They are not stored in SQLite, exported to Excel or used in the EIA/FRED crack spread calculations. A displayed CFD price must not be substituted for an EIA input at a different timestamp.

**If a chart is blank:** allow the TradingView scripts/frames in your browser, reconnect the quote feed, or use the direct source links. An unavailable external feed does not remove the saved EIA/FRED archive. Provider attribution is retained.""")
        st.link_button("TradingView widget data FAQ", "https://www.tradingview.com/widget-docs/faq/data/")
