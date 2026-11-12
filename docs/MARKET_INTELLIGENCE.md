# Market Intelligence dashboards

The current application has two dashboard areas:

1. **Controller Finance Dashboard** — a fully populated `DEMO_SYNTHETIC` twelve-month illustrative finance dashboard, generated from the repository's fictional Source Ledger sample extracts, combined with live exception/action-register signals from the current database. It is not customer actuals or a reconciled financial statement.
2. **Market Intelligence** — the seven-tile public reference dashboard uses FRED/EIA and World Bank Pink Sheet feeds for Brent, the Federal Reserve broad USD index, Gold and Silver. Direct Dow/S&P/Nasdaq/VIX feeds remain unavailable until data-display rights are confirmed. The separate equity search/history and metals explorer routes continue to use Alpha Vantage.

No database migration is required. The market dashboard's successful public feed responses are cached in application-process memory; failure responses are suppressed for 15 minutes and a previous successful response can be served as stale for up to seven days. This cache resets when the Render process restarts. See [`FINANCE_AND_MARKET_DATA.md`](FINANCE_AND_MARKET_DATA.md) for data lineage, source attribution, cadence and limitations.

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

- `GET /api/v1/controller/dashboard` — synthetic finance demonstration series plus live exception/action register.
- `GET /api/v1/market/dashboard` — public Brent, broad USD, Gold and Silver tile payload; no Alpha Vantage key required.
- `GET /api/v1/market/search?q=<company-or-ticker>` — provider symbol search.
- `GET /api/v1/market/equity?symbol=<provider-symbol>` — recent daily OHLCV series for one listing.
- `GET /api/v1/market/metals` — gold, silver, copper and aluminum series, with per-series errors where available.

The `/market/dashboard` endpoint does not require `MARKET_DATA_API_KEY`. The `/market/search`, `/market/equity` and `/market/metals` Alpha Vantage endpoints return HTTP 503 when that key is missing. Invalid symbols return a validation error or provider-backed not-found result; provider throttling on the Alpha Vantage endpoints is returned as HTTP 429.

## Controller Intelligence calculations

The Controller finance view reads `GET /api/v1/controller/dashboard`. Financial amounts come from the static reproducible DEMO fixture in `app/data/demo_finance.json`; live exception alerts, active exception count, unresolved root-cause count and open actions are queried from the database. The dashboard explicitly labels the fictional company and synthetic assumptions. Do not use these values as customer actuals, audited figures or management reporting.

The original Exception/Overview page continues to show the live current exception/action register, and does not reinterpret exception impact as P&L or cash flow.

## Deployment

1. Apply the changed files from the patch at the repository root.
2. Run `python -m compileall -q app tests` and `pytest -q`.
3. Run the frontend JavaScript syntax checks described in the change-set instructions.
4. Push the changes to the branch connected to Render.
5. `MARKET_DATA_API_KEY` is optional for the seven-tile public market dashboard; it is still required for the separate Alpha Vantage equity search/history and metals detail endpoints.
6. Sign in to the application. Open **Controller Dashboard** to see the labelled synthetic financial example plus live register signals. Open **Market Intelligence** for public reference tiles and source dates.

No database schema changes, migrations, or writes to ERP systems are part of this change.
