# Finance and Market Dashboard Data Integration

## Controller Finance Dashboard — DEMO mode

The Controller dashboard endpoint is `GET /api/v1/controller/dashboard`. It returns a reproducible 12-month fictional dataset for **Meridian Bicycle Co. (Plant 100 — SFO)** covering July 2025 through June 2026. The JSON fixture is `app/data/demo_finance.json`; rebuild it with:

```bash
python scripts/build_demo_finance_data.py
```

The fixture builder reads the repository's fictional Source Ledger sample extracts:

- `sample_data/02-corporate-controller-sample-extract.xlsx` — BSEG debit/credit magnitudes used as scale anchors for three demo account roles.
- `sample_data/05-fpa-sample-extract.xlsx` — COEP July 2025 actual and plan cost-element totals retained as provenance checks only.
- `sample_data/06-treasury-sample-extract.xlsx` — reconciled USD statement movement retained as provenance only; no formal cash-flow classification is inferred from it.

The sample files do not contain an authoritative customer Chart of Accounts or complete, reconciled monthly statements. Consequently, account-role assignments, remaining months, budget, categories, cash flow, forecast and balances are deterministic **synthetic assumptions**. The API and UI mark the data `DEMO_SYNTHETIC` and state that it is not company actuals, a reconciled P&L, a trial balance, or suitable for management/statutory/audit/tax/external reporting. This is the agreed demonstration data mode until actual finance extracts are available.

The Controller endpoint combines the static demonstration financial fixture with the live exception/action register counts and current exception alerts from the existing database. It does not turn exception amounts into revenue, profit or cash flow. Monthly date filters include any month overlapping the selected date range; figures are not prorated by day. Entity filtering is limited to entities present in the fixture. There are no schema changes or migrations for this demo implementation.

## Market Intelligence — public reference mode

The dashboard endpoint `GET /api/v1/market/dashboard` uses the following public reference series and does not consume the Alpha Vantage quota:

| Dashboard tile | Source | Cadence / interpretation |
|---|---|---|
| Brent Crude | U.S. EIA series `DCOILBRENTEU`, distributed by FRED | Daily spot observation, USD per barrel |
| U.S. Dollar · Broad Index | Federal Reserve series `DTWEXBGS`, distributed by FRED | Daily broad trade-weighted dollar index; **not ICE DXY** |
| Gold | World Bank Commodity Markets Pink Sheet, Monthly Prices | Monthly average, USD per troy ounce (as published) |
| Silver | World Bank Commodity Markets Pink Sheet, Monthly Prices | Monthly average, USD per troy ounce (as published) |
| Dow Jones, S&P 500, Nasdaq Composite | Not connected | Requires confirmed index data display rights / licensed provider |
| VIX | Not connected | Requires authorized CBOE/VIX display data |
| Market Mood | Not calculated | Depends on a connected, authorized VIX series |

FRED's graph CSV download format is used for one combined request containing both daily series. World Bank's monthly historical XLSX is discovered from its Commodity Markets page and parsed from the Pink Sheet workbook. The World Bank is attributed as the source of Gold and Silver monthly observations. See [World Bank Commodity Markets](https://www.worldbank.org/en/research/commodity-markets), [Pink Sheet monthly data](https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx), and [FRED CSV downloads](https://fred.stlouisfed.org/help/data/downloading/using-the-download-data-link/).

The adapter deliberately does not scrape unofficial finance websites or substitute ETFs for index values. Index and VIX cards remain unavailable until the owner/provider's terms authorize dashboard display. The USD card is renamed Broad Index so it is not misrepresented as DXY.

### Refresh and failure behavior

- FRED combined series: cache for 6 hours (one request covers Brent and broad USD).
- World Bank workbook: cache for 24 hours (one download covers Gold and Silver).
- Failed refresh: negative-cache for 15 minutes to prevent repeated rapid requests.
- Previously successful response: may be shown as stale for up to 7 days, with `stale=true`; the dashboard includes source/date metadata.
- Cache is in application-process memory and resets on a Render process restart. It is not yet persisted to PostgreSQL.
- Values are observations, not real-time quotes, futures settlement prices, purchase prices or accounting valuation inputs.

The older equity search/history and metals detail endpoints remain available through the Alpha Vantage adapter and still require `MARKET_DATA_API_KEY`; the seven-tile public reference dashboard endpoint does not require that key.

## Verification

The integration adds automated tests for Controller dashboard output/filtering, World Bank multi-row month/year header parsing, market feed shape, negative caching and stale-cache behavior. Run:

```bash
python -m compileall -q app scripts tests
pytest -q
```
