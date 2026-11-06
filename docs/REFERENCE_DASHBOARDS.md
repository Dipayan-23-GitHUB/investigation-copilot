# Reference-led finance and market dashboards

## Controller Finance Dashboard

The UI follows the supplied finance dashboard reference: six headline finance KPIs, revenue and profitability trends, revenue mix, expense breakdown, cash flow, expense categories, budget vs actual, account balances, profitability summary and recent controller alerts.

Only the current exception and action registers are presently API-connected. Revenue, gross profit, net profit, operating expense, operating cash flow, net margin, budget, cash balances and account balances remain explicitly marked **Not connected** until their source extracts are mapped and reconciled. The existing exception register is not a substitute for a general ledger or P&L. No finance metric is populated with invented or sample values.

## Global Market Dashboard

The dashboard contains U.S. index, gold, silver, Brent crude, U.S. Dollar Index, market mood and VIX tiles. Values are displayed only when returned by the configured provider. The market mood is an internal heuristic derived from the latest VIX close: below 15 Calm; 15 to below 20 Balanced; 20 to below 30 Cautious; 30 or above Defensive. It is not a provider consensus signal or investment recommendation.

The current Alpha Vantage adapter supports daily gold/silver history and daily Brent reference data. Alpha Vantage documents the Dow Jones (`DJI`), S&P 500 (`SPX`), Nasdaq Composite (`COMP`) and VIX index data endpoints as premium endpoints. DXY is not provided by the current adapter; its tile remains unavailable until a licensed DXY feed is connected. See https://www.alphavantage.co/documentation/.

Market data is cached server-side by series for six hours. It is end-of-day / reference data, not a live trading terminal. Provider quotas and licensing apply.

## Apply and validate

1. Copy the patch files to the repository root, preserving their folder paths.
2. Run `python -m compileall -q app tests`.
3. Run `pytest -q`.
4. Validate the inline JavaScript with `node --check` after extracting the script block if Node.js is installed.
5. Commit and push to the Render-connected branch.
6. Confirm `MARKET_DATA_API_KEY` is configured in the Render web service.

No database migrations or schema changes are introduced by this dashboard update.
