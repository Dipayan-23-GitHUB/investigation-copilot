# Apply the Finance Dashboard data connection

This patch is based on the currently deployed Reference Dashboards version of Investigation Copilot.

## Files included

- `app/catalog.py` — adds the `finance-reporting` upload module.
- `app/main.py` — adds the authenticated `GET /api/v1/finance/dashboard` endpoint.
- `app/services/finance_dashboard.py` — calculates KPI and chart data from the latest uploaded normalized finance pack.
- `frontend_reference/investigation_copilot.html` — replaces static placeholders with API-backed KPI cards, chart panels and filters.
- `sample_data/Finance_Dashboard_Upload_Template.xlsx` — workbook template with the four required sheets.
- `docs/FINANCE_DASHBOARD_DATA.md` — sheet schemas and calculation rules.
- `tests/test_finance_dashboard.py` and update to `tests/test_api.py` — regression tests and catalog count.
- `README.md`, `docs/FRONTEND_INTEGRATION.md` — usage and endpoint documentation.

## Apply

1. Extract this ZIP into the repository root, preserving folders and overwriting the listed files.
2. Run `python -m compileall -q app tests`.
3. Run `pytest -q`.
4. Commit and push to the branch connected to Render.
5. Wait for Render to show the deployment as Live.
6. Download `sample_data/Finance_Dashboard_Upload_Template.xlsx` from the repository (or use the supplied standalone template), fill it with approved/reconciled finance report rows, then in Investigation Copilot choose **Upload extract** and use module key `finance-reporting`.
7. Refresh the Finance Dashboard.

## Database and data safety

- No new database tables or migrations are introduced; the existing `ingestions`, `source_sheets` and `source_rows` tables are reused.
- The dashboard reads only the latest uploaded full-period finance pack. Upload a full refreshed reporting snapshot, not a delta-only workbook.
- It does not derive revenue/profit from exception exposure, and it does not classify raw GL accounts or bank transactions by guessing.
- Currencies remain separate; there is no automatic FX conversion.
- Net profit and net margin require all six P&L line types for the selected period/currency. Include an explicit zero row for a line type with no postings.
- The included test workbook contains synthetic test values only. Do not upload fictional samples as actual financial performance.
