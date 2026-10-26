# Validation — English Edition

English localisation prepared on **26 October 2026**. The market snapshot remains dated **24 October 2026**. No new live market requests were made during translation.

## Scope

The interface, chart labels, topic/region/signal names, status messages, scenario explanations, source descriptions, profile, exports and documentation are English. Dates use YYYY-MM-DD and UTC. Price and flow units use USD/bbl, USD/gal, million b/d and million barrels.

NewsAPI now requests `language=en` with one bounded request per collection run. Cyrillic source content is excluded by the collectors and the dashboard. The English copy contains **257 articles** from the earlier snapshot; **86 Cyrillic articles** were omitted. The previous bilingual project remains unchanged. Headlines and excerpts were not machine-translated or represented as publisher-supplied English translations.

The snapshot retains **8,299 daily price observations**, **12,096 STEO monthly observations** and **seven original EIA workbooks** from April–October 2026. The price snapshot ends on 2026-10-20. STEO workbooks are preserved byte-for-byte. SQLite integrity_check returned `ok` after localisation.

## Automated checks

**Result: 27 tests passed in 50.285 seconds (OK).**

The original 24 regression tests cover ingestion, URL deduplication, history retention under source failure, formula-safe Excel export, original workbook provenance, checksum verification, balance reconciliation, day-weighted aggregation, incomplete periods, vintage comparison, crack spread units/yields, missing dates, secret handling and scenario signs. Streamlit AppTest exercises empty and populated data, search, vintage/frequency selection, WTI/Brent switching and scenario controls.

Additional English edition checks scan interface code and documentation, inspect persisted news and Excel text, and verify rejection of Cyrillic source content. The collection request test confirms one English-language NewsAPI request per run.

## Verification limits

The earlier local browser preview could not start because Windows rejected the listening socket (WinError 10013). This edition is checked with Streamlit AppTest; browser layout has not been visually verified. No new browser preview is claimed.

The project has not been published to the user's GitHub or Streamlit account. GitHub Actions was configured but not executed in the user's account. No API key is included. Configure NEWSAPI_KEY for future updates and use a NewsAPI plan appropriate for production. Successful requests made on 24 October do not verify the account's production entitlement.
