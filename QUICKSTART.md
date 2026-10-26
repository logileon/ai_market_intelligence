# Quick start — English Edition

1. Extract the ZIP and open the `ai-market-intelligence` folder.
2. Follow README.md to install dependencies and start the Streamlit dashboard.
3. Use **Overview** for dated market indicators and the latest English-language articles.
4. Open **Crack spreads & refining** to select WTI or Brent, inspect gasoline/ULSD/3:2:1 cracks and compare seasonal patterns.
5. Use **EIA balances & forecasts** to compare historical vintages with a chronological time axis.
6. Open **Balance scenarios** to apply supply/demand shocks to a fully forecast quarter and inspect implied stock changes.
7. Use **News & export** for article search, publisher links and Excel downloads. News filters apply to news; the Excel price and crack sheets contain full snapshots.
8. Check **Sources & data quality** before drawing conclusions from an old observation or a partially unavailable source.

All dashboard labels, explanatory text and documentation are English. NewsAPI requests English articles. Cyrillic source articles are excluded from the English snapshot; the previous bilingual version is retained separately. The saved market data was collected on 24 October 2026 and has not been refreshed during translation.

No API key is included. Configure NEWSAPI_KEY as described in README.md for future collections. Production use requires an appropriate NewsAPI plan. The project has not been published to a hosting account.

## Intraday prices

The Overview shows WTI and Brent CFD quotes from TradingView. Open **Intraday oil** for charts, candle intervals and market status. The external feed updates while the browser is connected during market hours; it does not wait for GitHub Actions. No additional API key is needed. The EIA/FRED daily spot archive and crack calculations remain separate. Use **Reconnect quote feed** or the source links if a widget is unavailable.
