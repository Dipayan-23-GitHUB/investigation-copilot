# Market Intelligence dashboards

This change adds two dashboard areas to the existing single-page HTML application:

1. **Controller Intelligence** — visual summaries of the current exception register and action queue.
2. **Market Intelligence** — global equity search/history and reference metal-price history.

No database migration is required. Market observations are fetched from an external provider and cached in process memory; they are not stored in PostgreSQL and do not modify manufacturing-finance records.

## Alpha Vantage configuration

Create a free API key at <https://www.alphavantage.co/support/#api-key>, then add it to the Render **web service** environment:

```text
MARKET_DATA_API_KEY=<your-private-alpha-vantage-key>
```

Keep the key server-side. Do not put it in HTML, JavaScript, a URL shared with users, GitHub, or screenshots. Redeploy the web service after saving the variable.

The free Alpha Vantage service is currently advertised at 25 API requests per day. The backend caches equity searches and daily stock histories for six hours, gold/silver daily histories for six hours, and copper/aluminum monthly data for 24 hours. The cache is per application process and is cleared by process restarts. Avoid repeated refresh clicks: they can still use the cached provider payload, but cache misses consume quota.

Provider documentation: <https://www.alphavantage.co/documentation/>
Free-tier support and quota: <https://www.alphavantage.co/support/>

## Data coverage and interpretation

| Dashboard data | Provider function | Frequency used here | Important boundary |
|---|---|---|---|
| Global stock / ETF / instrument search | `SYMBOL_SEARCH` | Search result | Listing availability depends on provider coverage and ticker syntax |
| Global equity history | `TIME_SERIES_DAILY` | Daily OHLCV, compact 100-row window | End-of-day history, not a real-time/intraday quote |
| Gold | `GOLD_SILVER_HISTORY` | Daily | Historical observations, not a live spot quote |
| Silver | `GOLD_SILVER_HISTORY` | Daily | Historical observations, not a live spot quote |
| Copper | `COPPER` | Monthly | Global price series sourced from IMF data retrieved from FRED |
| Aluminum | `ALUMINUM` | Monthly | Global price series sourced from IMF data retrieved from FRED |

The Alpha Vantage documentation describes its default free stock quote data as updated at the end of the trading day; real-time and 15-minute delayed US equity data are premium entitlements. This implementation intentionally uses `TIME_SERIES_DAILY` and does not claim real-time equity prices.

The copper and aluminum feeds are monthly reference series and must not be presented as exchange-traded intraday futures quotes. The metals page marks the data interval and observation date. Precious-metal historical series should not be described as the provider's live spot API.

## API endpoints

All endpoints are protected by the application's existing `/api/v1` authentication dependency:

- `GET /api/v1/market/search?q=<company-or-ticker>` — provider symbol search.
- `GET /api/v1/market/equity?symbol=<provider-symbol>` — recent daily OHLCV series for one listing.
- `GET /api/v1/market/metals` — gold, silver, copper and aluminum series, with per-series errors where available.

If `MARKET_DATA_API_KEY` is missing, these endpoints return HTTP 503 with a configuration message. Invalid symbols return a validation error or a provider-backed not-found result. Provider throttling is returned as HTTP 429.

## Controller Intelligence calculations

Controller charts are computed in the browser from the existing API responses for exceptions, controls and actions. They summarize the current register:

- active exposure and unfavorable exposure;
- exception exposure by priority, grouped by currency;
- exception counts by status;
- confirmed/unresolved root causes and evidence completeness;
- action counts by status;
- largest active exceptions, linked to the existing investigation workspace.

The dashboard does not create synthetic monthly trends, plant/supplier/material groupings, or financial calculations that are not present in the current records. It labels the current-register basis and suppresses single-currency KPI totals when records contain multiple currencies. The existing exception register still contains seeded demonstration cases until deterministic rules link ingested source rows to new exceptions.

## Deployment

1. Apply the changed files from the patch at the repository root.
2. Run `python -m compileall -q app tests` and `pytest -q`.
3. Run the frontend JavaScript syntax checks described in the change-set instructions.
4. Push the changes to the branch connected to Render.
5. Add `MARKET_DATA_API_KEY` to the Render **web service** environment and redeploy.
6. Sign in to the application. Open **Controller Dashboard** to see current-register visualizations. Open **Market Intelligence** to search equities or load the metal tab.

No database schema changes, migrations, or writes to ERP systems are part of this change.
