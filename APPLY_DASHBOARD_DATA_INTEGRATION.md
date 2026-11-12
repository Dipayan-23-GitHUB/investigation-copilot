# Apply Finance and Market Dashboard Data Integration

This is an incremental patch for the existing Investigation Copilot repository and its already-integrated reference dashboard UI. It does not replace the project and does not add or modify database tables.

## Included changes

- `GET /api/v1/controller/dashboard`: twelve-month, clearly labelled `DEMO_SYNTHETIC` finance payload plus live exception/action register signals.
- Reproducible demo data generator using the repository's fictional Source Ledger workbooks; generated JSON fixture is included so Render does not need to run the script at startup.
- `GET /api/v1/market/dashboard`: public reference dashboard data using one combined FRED CSV request for Brent and the Federal Reserve Broad USD Index, plus one World Bank Pink Sheet XLSX for monthly Gold and Silver data.
- Market cache: FRED 6 hours, World Bank 24 hours, failed refresh suppression 15 minutes, and stale successful data may be served for up to 7 days with a visible stale flag. Cache is per process and resets on restart.
- Frontend wiring for finance filters, KPIs, trends, category breakdowns, budget/actual, cash-flow, account summaries and current exception alerts.
- Tests and updated data-source documentation.

## Important data boundaries

The finance values are synthetic examples for fictional Meridian Bicycle Co. They use a few amounts from bundled sample workbooks as scale anchors. The workbooks do not include a complete authoritative Chart of Accounts, reconciled statements or customer actuals. Budget, categories, later months, cash-flow classification, forecast and balance-sheet summary are illustrative assumptions. The dashboard labels all of this as DEMO and must not be used for actual management reporting, audit, tax, statutory, credit or external reporting.

Brent and the Federal Reserve broad trade-weighted USD index are daily reference observations. The dollar index is not ICE DXY. Gold and Silver are monthly World Bank Pink Sheet averages, not daily spot quotes. Dow, S&P 500, Nasdaq Composite and VIX remain unavailable until an authorized index-display source is connected; no ETF proxy or unofficial scrape is used. Market Mood is not calculated without a licensed VIX observation.

## Apply and verify

From the repository root:

```bash
unzip -o Investigation_Copilot_Dashboard_Data_Integration_Patch.zip -d .
python scripts/build_demo_finance_data.py
python -m compileall -q app scripts tests
pytest -q
```

If tests pass:

```bash
git add README.md APPLY_DASHBOARD_DATA_INTEGRATION.md app/main.py app/routers/controller.py app/routers/market.py app/services/controller_finance.py app/services/public_market_dashboard.py app/data/demo_finance.json docs/FINANCE_AND_MARKET_DATA.md docs/MARKET_INTELLIGENCE.md frontend_reference/investigation_copilot.html scripts/build_demo_finance_data.py tests/test_controller_dashboard.py tests/test_public_market_dashboard.py
git commit -m "Connect finance demo and public market dashboard data"
git push origin main
```

Render should deploy automatically when the push reaches its connected branch. No database migration or environment variable is required for the seven-tile public market dashboard. `MARKET_DATA_API_KEY` remains optional for the separate Alpha Vantage equity search/history and metals detail endpoints.
