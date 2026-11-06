# Apply the reference-led dashboards

This patch replaces the simplified exception-only Controller page with the supplied finance-dashboard layout and the Market Intelligence page with the supplied dark market-tile layout.

Files: `frontend_reference/investigation_copilot.html`, `app/services/market_data.py`, `app/routers/market.py`, `tests/test_market_data.py`, and `docs/REFERENCE_DASHBOARDS.md`.

No database migrations are required. The Controller page reads current exceptions/actions for alerts and marks P&L, cash flow, budget and balances as not connected until the underlying finance extracts are mapped. The Market page uses provider-backed daily data; Dow/S&P/Nasdaq/VIX endpoints require Alpha Vantage premium access, and DXY is left unavailable because the current adapter does not provide it.

Apply from the repository root: `unzip -o Investigation_Copilot_Reference_Dashboards_Patch.zip -d .` then run `python -m compileall -q app tests` and `pytest -q`. Review `git diff`, commit, and push to the Render-connected branch.
