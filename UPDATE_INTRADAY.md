# Install the intraday oil update

This package updates the existing English dashboard. It contains code, tests and documentation only. It has no `data/` folder, API key or dependency changes.

## GitHub Desktop (recommended)

1. Select the local repository used by your deployed Streamlit app.
2. Use **Fetch origin** and **Pull origin** if offered, so the local copy includes recent data commits.
3. Extract `Oil-Market-Intelligence-Intraday-Update.zip` into a temporary folder.
4. Copy its contents into the repository folder containing `app.py`. Merge the `market/` and `tests/` folders and replace matching files. Do not copy an extra enclosing folder into the repository.
5. In GitHub Desktop, inspect Changes. The feature uses `app.py` and `market/intraday.py`; the package also includes regression tests, the earlier AppTest timeout fix and documentation. There should be no database change from this patch.
6. Commit with a message such as `Add intraday WTI and Brent quotes`, then **Push origin**.
7. Streamlit should update from the configured branch. Open the app, check the quote strip under Overview and the new **Intraday oil** tab. If the app retains the old version, use **Reboot** in Streamlit.

## GitHub website alternative

Upload `market/intraday.py` into the existing `market` directory first. Then replace the root `app.py`. This order ensures the new module exists before the application imports it. Upload the included tests and documentation to their corresponding paths. Run a new **Update market data** workflow after committing the tests.

## What changes

- WTI and Brent CFD quote strip on Overview.
- Separate intraday tab with side-by-side charts or a single instrument.
- 1-minute, 5-minute, 15-minute and 1-hour candles; UTC chart timezone.
- Reconnect button and direct source links.
- Automatic browser feed updates from official TradingView widgets; no extra API key.

## Source and boundaries

TradingView symbols: **TVC:USOIL** and **TVC:UKOIL**. These are CFD market indicators in USD/bbl, distinct from EIA spot assessments and from an individual exchange futures contract. The provider controls feed availability and any delay. Check the market status/delay indicator in the chart; prices need not change when the market is closed.

Intraday data is display-only: it is not stored in SQLite, included in Excel or used in the EIA/FRED crack spreads. Provider attribution is preserved. Your existing NewsAPI configuration and GitHub data collection remain separate.

If the widget is blank, allow TradingView scripts/frames, use **Reconnect quote feed**, or follow the direct instrument links. This package has not been uploaded to your GitHub or deployed to your Streamlit account.

Validation: 29 automated tests passed locally. WTI and Brent charts and the two-symbol ticker were separately loaded in the browser with live provider data. End-to-end browser rendering inside the deployed Streamlit page remains to be verified after installation.
