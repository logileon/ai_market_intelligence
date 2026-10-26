# EIA STEO guide

## Select a vintage

Open **EIA balances & forecasts**. Vintages are listed chronologically; the newest saved edition is selected initially. Choose a comparison vintage and a monthly, quarterly or annual frequency. Use the year filter to limit the charts.

The included archive contains original April–October 2026 EIA workbooks, normalised observations, source-sheet/cell references and SHA-256 checksums. Original workbooks are preserved byte-for-byte.

## Interpret the balance

The liquid fuels scope is broader than crude oil. It includes petroleum and other liquid fuels, including biofuels and refinery processing gains.

**Balance = supply − demand.** Positive means an implied stock build; negative means a draw. It includes balancing items and is not a direct observation of commercial inventories. EIA's `t3_stchange_world` row uses the opposite sign; the importer checks reconciliation within the source rounding tolerance.

## Distinguish history and forecasts

The forecast boundary is taken from **Dates / Last Historical Month** in each workbook. Labels are:

- **History / estimate:** historical side of the common cutoff; subject to revision.
- **EIA forecast:** all months in the displayed period are forecast months.
- **History + forecast:** the period spans both sides of the cutoff.
- **Incomplete period:** insufficient monthly coverage; no quarterly or annual value is computed.

The common cutoff is approximate because individual historical series may contain estimates.

## Aggregation

Supply, demand and balance flows are weighted by calendar days. Prices use simple arithmetic averages of monthly values. A complete quarter requires three distinct months; a complete year requires twelve. Missing observations remain blank.

## Compare revisions

Select an indicator and compare the selected vintage with the comparison vintage. Change is **selected minus comparison**, in the indicator's original unit. Percentage change is unavailable when the comparison value is zero. An unmatched period remains blank.

Use **Forecast periods in both vintages only** to focus on revisions to forecasts. Forecast evolution charts track a fixed target period across saved editions, ordered by release month and retrieval timestamp. Separate corrected workbooks can exist for the same release month.

## Refresh

Run `python update_steo.py` locally, or use **Update market data → Run workflow** on GitHub. `update_data.py` refreshes the main market sources and checks STEO. New editions are retained alongside prior editions. The newest workbook is rechecked for corrections; a changed file is stored as a separate checksum-identified vintage. Earlier intact workbooks are cached.

## Export and scenarios

The tab offers comparison CSV, all-vintage CSV and the original workbook for the selected vintage. **Balance scenarios** applies supply and demand shocks to a fully forecast quarter from the selected edition, with calendar-day conversion to implied stock changes. This is a conditional sensitivity calculation, not an independent price model.

[Official EIA STEO archive](https://www.eia.gov/outlooks/steo/outlook.php).
