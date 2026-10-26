# Oil Market Intelligence — English Edition

An English-language research dashboard for crude oil, refined products and global liquid fuels balances. Built with Streamlit, SQLite, Plotly, RSS, FRED and archived EIA Short-Term Energy Outlook workbooks.

English edition prepared on **26 October 2026**. The included market snapshot was collected on **24 October 2026**; this translation does not refresh market data. All timestamps are UTC, dates use YYYY-MM-DD, prices use USD/bbl or USD/gal and flow rates use million b/d.

## Intraday oil monitor (26 October 2026)

The Overview now includes a WTI/Brent quote strip, and the new **Intraday oil** tab displays two interactive charts. Sources: TradingView widgets, TVC:USOIL (WTI CFD) and TVC:UKOIL (Brent CFD), quoted in USD/bbl.

Quotes are loaded directly in the visitor's browser and update as the provider sends new prices during market hours. There is no extra API key or scheduled collection needed for this display. Choose 1-minute, 5-minute, 15-minute or 1-hour candles and either side-by-side or single-chart layout. Candle interval sets bar aggregation, not the update frequency. **Reconnect quote feed** reloads the embedded components.

These are CFD indicators rather than EIA physical spot assessments or a specified exchange futures contract. Provider-controlled delay and availability can change; check the market status indicator in the chart. Closed markets retain the last available price. Provider attribution is preserved. Intraday values are not scraped, stored, exported or mixed into the EIA/FRED crack calculations.

If an embedded chart is blocked, allow the TradingView scripts/frames or follow the direct instrument link. See the [TradingView widget data FAQ](https://www.tradingview.com/widget-docs/faq/data/).

## Features

- **Overview:** an intraday CFD quote strip plus dated EIA Brent and WTI observations, an indicative 3:2:1 crack, news activity charts and a rules-based digest with publication timestamps.
- **Crack spreads & refining:** gasoline, ULSD and 3:2:1 spot cracks; WTI/Brent selection; seasonal comparisons; underlying prices and Brent–WTI.
- **EIA balances & forecasts:** world liquid fuels supply, demand and implied balances; regional and product indicators; seven original EIA vintages; revisions and forecast evolution.
- **Balance scenarios:** supply and demand shocks applied to a fully forecast quarter, implied stock changes and a sensitivity matrix.
- **News & export:** English-language headlines and excerpts, detailed topic and region filters, source links and Excel downloads.
- **Sources & data quality:** last observation dates, data age, missing publication dates and collection failures.

All time axes are chronological, including positive and negative balance bars. News tags are recomputed from the saved archive. Topic groups include gasoline, diesel/gasoil, jet fuel, fuel oil/bunkers, LPG/petrochemicals, refinery maintenance, OPEC+, inventories/SPR, sanctions and logistics.

The analysis is transparent and rules-based. It does not use a generative LLM. EIA forecasts are identified as EIA forecasts; the scenario tool is a conditional calculation rather than a separate price forecast.

## Local setup

Install Python 3.11 and open PowerShell in this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://localhost:8501. The saved snapshot can be browsed without a network refresh. On macOS/Linux, use `python3` and `.venv/bin/python`.

Refresh and test:

```powershell
.\.venv\Scripts\python.exe update_data.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## NewsAPI setup

The English edition queries NewsAPI Everything with `language=en`. It uses a seven-day search window, one bounded request and up to 100 results per run. Coverage is not exhaustive, especially on busy news days. RSS remains active independently.

No API key is included in the archive, database or source code. Set **NEWSAPI_KEY** in the collector's environment:

```powershell
$env:NEWSAPI_KEY = '<your API key>'
.\.venv\Scripts\python.exe update_data.py
Remove-Item Env:NEWSAPI_KEY
```

For GitHub Actions, create a repository secret named `NEWSAPI_KEY` under Settings → Secrets and variables → Actions. The supplied workflow passes it to the collector. Dashboard visitors read the saved database; they do not trigger API calls.

Without a key, NewsAPI is marked `skipped`. Network, authentication and quota failures are logged without disclosing the key; saved history is retained. URLs are normalised and deduplicated. Syndicated articles with different URLs may remain duplicated. Cyrillic source content is excluded from this English edition rather than presented as an unverified translation. The earlier bilingual archive is unchanged.

The [NewsAPI Developer plan](https://newsapi.org/pricing) is restricted to development and testing, with publication delays and request limits. Production and staging, including internal use, require an appropriate plan. The supplied key's plan has not been verified. Publisher rights still apply to headlines and excerpts.

## Refining methodology

EIA is the primary source for the daily prices distributed by FRED. Products are US Gulf Coast conventional gasoline (`DGASUSGULF`) and ULSD (`DDFUELUSGULF`). Crude inputs are WTI Cushing (`DCOILWTICO`) or Brent Europe (`DCOILBRENTEU`).

- Gasoline crack = 42 × gasoline price − crude price.
- ULSD crack = 42 × ULSD price − crude price.
- 3:2:1 crack = 42 × (2 × gasoline price + ULSD price) / 3 − crude price.

Product prices are USD/gal, crude prices are USD/bbl and the result is USD per barrel of crude input. Calculations use matched dates only, with no forward filling. Location and quality differences are not adjusted.

These are indicative open-data spot cracks, not exchange-traded futures cracks, a published Gulf Coast LLS 3:2:1 assessment or net refinery profit. Conventional gasoline differs from RBOB. No. 2 heating oil is not used as a substitute for ULSD. Energy, hydrogen, own-use fuel, losses, freight, maintenance, actual refinery yields and fixed costs are excluded.

Seasonality compares the current year's monthly averages with available monthly averages from the preceding five calendar years. The current year is excluded from the baseline. A partial current month uses available days. Historical minima and maxima are not forecast intervals; the table reports the number of years available for each month.

[EIA crack spread methodology](https://www.eia.gov/todayinenergy/detail.php?id=1630) · [FRED gasoline series](https://fred.stlouisfed.org/series/DGASUSGULF).

## Balances and scenarios

Supply minus demand is positive for an implied stock build and negative for a draw. This is a balancing quantity, not observed commercial inventories. The EIA stock-change series uses the opposite sign; ingestion reconciles the two conventions.

Flow averages are weighted by calendar days. Price averages use arithmetic monthly means. Incomplete periods remain unavailable; missing observations are not replaced by zero. See STEO_GUIDE.md for details.

The scenario tool uses complete forecast quarters only:

`implied stock change = (supply + supply shock − demand − demand shock) × calendar days`

Shocks are constant throughout the selected quarter. The tool does not estimate scenario probabilities, price responses, elasticities or an OPEC+ reaction.

## Downloads

- Excel: selected news, all saved prices, crack spreads for both WTI and Brent, collection log and methodology notes.
- Crack CSV: selected crude benchmark and lookback.
- Scenario CSV: selected vintage, quarter, baseline, shocks, balance and implied stock change.
- STEO CSV and original EIA workbooks: available within the EIA tab.

## Publication

The project runs as a Python/Streamlit application. Store it in your own GitHub repository and select `app.py` in Streamlit Community Cloud. Add the collector's NewsAPI secret in GitHub Actions if required. The supplied workflow retains the previous twice-daily schedule; preparing this English archive does not activate a new automation.

Edit `config/profile.json` to add the analyst's name and contact links. A neutral project title is included until you customise it. Review data usage rights and the relevant NewsAPI plan before production use. The project has not been published to your GitHub or Streamlit account.

## Limitations

Dictionary classification can produce false matches and omissions. Risk mentions do not indicate price direction or event probability; news volume does not measure a physical shortage. Region tags can refer to a mention rather than the location of an event. There are no licensed Argus/Platts assessments, live Russian exchange prices or universal global diesel index. The market scope is oil, liquid fuels and refining; standalone gas/LNG datasets are not included.
