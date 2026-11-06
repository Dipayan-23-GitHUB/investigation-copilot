# Apply Controller and Market Intelligence dashboards

This change set is built from the user-provided `investigation-copilot-main(1).zip` repository archive. It adds two dashboard pages and three authenticated market-data endpoints. It does not change database tables or migrations.

## Files changed / added

- `app/config.py` — adds `MARKET_DATA_API_KEY` setting.
- `app/main.py` — includes the market router under the existing authenticated API router.
- `app/routers/market.py` — adds market search, equity history and metals endpoints.
- `app/services/market_data.py` — Alpha Vantage adapter, provider error handling and in-process cache.
- `frontend_reference/investigation_copilot.html` — Controller Intelligence and Market Intelligence pages, visualizations, selectors and charts.
- `.env.example` — documents the optional market-data key.
- `README.md` — adds endpoint/configuration notes.
- `docs/MARKET_INTELLIGENCE.md` — data coverage, limitations, quota and deployment guide.
- `tests/test_market_data.py` — tests missing-key handling, equity parsing/cache, metal parsing and symbol validation.
- `tests/conftest.py` — creates the ignored SQLite test-data directory automatically on clean checkouts.

## Test results in the working package

- `python -m compileall -q app tests`: passed.
- `pytest -q`: 12 passed from a clean checkout; `tests/conftest.py` now creates the ignored test-data directory automatically.
- Both inline frontend JavaScript blocks: passed `node --check`.
- HTML structure check: both navigation targets exist, no duplicate element IDs.
- Controller dashboard function smoke test: passed with mixed currencies, exception counts and currency-separated exposure bars.
- Browser interaction test: not completed; Chromium launch is blocked by the current execution environment policy.
- Market endpoints registered as `/api/v1/market/search`, `/api/v1/market/equity`, and `/api/v1/market/metals`.

These tests mock the external market provider. Live Alpha Vantage access still needs a valid key in Render.

## Deployment

1. Back up / commit the current GitHub branch first.
2. Apply the patch ZIP at the repository root, preserving folders.
3. Run `python -m compileall -q app tests` and `pytest -q` if Python is available locally. The test results above were run against this same working package.
4. Commit and push to the branch connected to Render.
5. In Render, add `MARKET_DATA_API_KEY` to the **web service** environment. Get a key at <https://www.alphavantage.co/support/#api-key>. Keep it private.
6. Wait for Render to deploy, then sign in to Investigation Copilot.
7. Open **Controller Dashboard**. It should display the current exception/action register.
8. Open **Market Intelligence**. Search a ticker or select the metals tab. If the key is not present, provider calls return a clear HTTP 503 configuration message; no fake prices are rendered.

## Market-data limitations

Alpha Vantage's free offering is currently advertised as 25 API requests/day. Backend cache TTLs: equity search/price history 6 hours; gold/silver daily history 6 hours; copper/aluminum monthly series 24 hours. These are per-process in-memory caches. Provider data coverage and symbol formats vary by listing.

Stocks use daily end-of-day OHLCV history, not real-time prices. Gold/silver use historical daily observations. Copper/aluminum use monthly global price series. This is an informational dashboard, not an execution terminal or approved accounting valuation source. Check provider terms and market-data licensing before distributing externally or using the data commercially.

## No database operations

This change set adds no database migration, does not seed or delete data, and does not make ERP writeback calls.
