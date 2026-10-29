# Investigation Copilot API — foundation v0.1

This repository starts moving the Meridian Investigation Copilot from a static HTML demo toward an API-backed product. It contains a FastAPI service, relational persistence, a Source Ledger catalog for all 12 role workbooks, Excel/CSV/JSON ingestion, exception/action/control APIs, and an optional Groq-backed evidence-constrained chat endpoint.

**Important scope and truthfulness notes**

- The Source Ledger says the attached spreadsheets use real-world SAP/Oracle-style field structures populated with fictional, illustrative Meridian Bicycle Co. values. They are not live customer data.
- The three existing demo investigations (`case1`, `case2`, `case3`) are seeded example cases from the HTML prototype. They are stored separately from uploaded sample workbook rows because the workbook rows do not all use the same material IDs/values as those three cases.
- File ingestion and read APIs work. Automated root-cause rules over newly uploaded workbooks, customer-specific ERP connections, multi-tenant identity/RBAC, and frontend API wiring are the next implementation steps. This is a production-oriented starter, **not yet safe for real customer financial data**.
- The names in The Source Ledger are mostly tables, views, files, and documents, not necessarily direct HTTP endpoints. Use customer-approved SAP released APIs/OData/CDS, Oracle Fusion REST/reporting interfaces, or approved exports after checking the customer's actual ERP version and permissions.

## Recommended stack

- **Frontend:** Next.js App Router + React + TypeScript + Tailwind CSS + shadcn/ui. Migrate the existing HTML one page/component at a time. Official docs: https://nextjs.org/docs/app
- **Backend:** FastAPI + Pydantic, SQLAlchemy 2.x, PostgreSQL (via psycopg 3), Alembic migrations.
- **Ingestion:** `openpyxl` for XLSX, Python `csv` and `json` for CSV/JSON; background task queue (Celery/RQ + Redis) after files/jobs become larger.
- **AI:** Groq API called only by backend. Default model is `openai/gpt-oss-20b`, configurable by `GROQ_MODEL`; verify current model availability in your own Groq project before deployment. Keep calculations and joins deterministic; ask the model to explain only evidence served by the API. Groq docs: https://console.groq.com/docs/models and https://console.groq.com/docs/structured-outputs
- **Auth/security (required before production):** enterprise OIDC/OAuth2, server-side authorization, tenant-scoped DB access, secrets manager, TLS, audit logs, retention policy, malware/zip-bomb checks, and customer-specific data governance.
- **Deployment:** Docker; managed PostgreSQL; object storage for raw files; monitoring/error reporting. Don't store API keys in the browser or in source control.

## Project structure

```text
app/
  catalog.py                 Source Ledger workbook/object mapping for 12 roles
  config.py                  environment settings
  db.py                      SQLAlchemy engine/session
  models.py                  ingestions, sheets/rows, exceptions, actions, controls
  seed.py                    illustrative prototype cases + action/control rows
  main.py                    API routes + Groq evidence-constrained chat
  services/ingestion.py      XLSX/CSV/JSON parsing and mapping validation
tests/                       API smoke tests
sample_data/                 copies of the 12 supplied sample workbooks
frontend_reference/          current static HTML reference
```

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --env-file .env
```

Open:

- Swagger API explorer: http://127.0.0.1:8000/docs
- Readiness: http://127.0.0.1:8000/health/ready
- Catalog: http://127.0.0.1:8000/api/v1/catalog/modules
- Overview: http://127.0.0.1:8000/api/v1/overview

If `API_ACCESS_KEY` is set, supply it as the `X-API-Key` header on API requests. This shared-key feature is for local/staging protection only; it is not a replacement for production identity and role-based authorization.

## API inventory

| Area | Endpoint | Purpose |
|---|---|---|
| Health | `GET /health/live`, `GET /health/ready` | Liveness/readiness |
| Catalog | `GET /api/v1/catalog/modules` | 12 role modules, workbook sheets, object names, keys and expected columns |
| Catalog | `GET /api/v1/catalog/modules/{module_key}` | Single module mapping plus source objects |
| Catalog | `GET /api/v1/catalog/source-objects?module_key=&confidence=` | Expanded source catalog for all mapped objects, with confidence and adapter status |
| Catalog | `GET /api/v1/catalog/source-objects/{source_key}` | One named Source Ledger object |
| Connectors | `GET /api/v1/connectors/catalog` | Available/planned adapter inventory; does not claim ERP connections are active |
| Dashboard | `GET /api/v1/overview` | KPI summary and priority exception list |
| Exceptions | `GET /api/v1/exceptions` | Search/filter/sort the current exception register |
| Exceptions | `GET /api/v1/exceptions/{id}` | Exception details |
| Investigation | `GET /api/v1/exceptions/{id}/evidence` | Evidence references currently attached to an exception |
| Investigation | `GET /api/v1/investigations/{id}` | Finding, hypotheses, evidence, calculation and controls |
| Investigation | `POST /api/v1/investigations/{id}/run` | Returns seeded demo investigation; otherwise explicitly refuses unconfigured analysis |
| Copilot | `POST /api/v1/copilot/chat` | Groq response constrained to supplied evidence and schema |
| Ingestion | `POST /api/v1/ingestions` | Upload XLSX/CSV/JSON with module key and header row (default row 5) |
| Ingestion | `GET /api/v1/ingestions/{id}` | Ingestion status/warnings/counts |
| Data | `GET /api/v1/data-sources` | Imported workbook versions |
| Data | `GET /api/v1/data-sources/{id}/sheets` | Sheet/object map and headers |
| Data | `GET /api/v1/data-sources/{id}/rows` | Paginated rows from a given sheet |
| Data | `GET /api/v1/modules/{key}/records` | Records from the latest upload for a role module |
| Actions | `GET /api/v1/actions` | Remediation action queue |
| Actions | `POST /api/v1/actions` | Create corrective/preventive/investigation action |
| Actions | `PATCH /api/v1/actions/{id}` | Update action owner/status/due date |
| Controls | `GET /api/v1/controls` | Control library and recurrence/exposure metadata |

Interactive OpenAPI docs describe parameters and response examples after startup.

## Upload a Source Ledger workbook

Swagger is easiest: select `POST /api/v1/ingestions`, set `module_key` to `plant-controller`, `header_row` to `5`, and upload `03-plant-controller-sample-extract.xlsx`.

Equivalent curl:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ingestions \\
  -F 'module_key=plant-controller' \\
  -F 'header_row=5' \\
  -F 'file=@sample_data/03-plant-controller-sample-extract.xlsx'
```

The importer reads all workbook tabs, stores each tab's headers and data rows, maps recognized sheet names to the Source Ledger object catalog, and returns warnings for missing tabs/columns. Metadata rows above the header row are skipped. Uploads with the same tenant, module and SHA-256 are deduplicated. To load all 12 fictional examples into the local database, run `python scripts/load_sample_data.py`.

## Module keys (12 Source Ledger roles)

`cfo`, `corporate-controller`, `plant-controller`, `cost-accounting`, `fpa`, `treasury`, `tax`, `internal-audit`, `risk-management`, `investor-relations`, `accounts-payable`, `ar-credit`.

The catalog preserves the PDF's naming and structure, including SAP/Oracle object names, expected header row, expected columns, primary keys and candidate join keys. Check the returned `warnings` and inspect the customer's own schema before making rules depend on it. SAP releases and customer customizations can change which underlying tables or released APIs should be used.

## Groq configuration

Set these only in backend environment variables:

```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

The endpoint uses structured JSON output and checks model-provided evidence IDs against IDs already present in the server's investigation object. The model does not have database credentials or direct write tools. API calls fail clearly if no key is configured. In production, add request budgeting, retries with limits, rate limits, PII/data minimization, prompt/version tracking, latency monitoring, and model-evaluation tests. The response is advice, not a financial posting or ERP action.

## Current limitations to close before production

1. In production set `AUTO_CREATE_DB=false` and run `alembic upgrade head` during deployment; keep `create_all` only for local development/test.
2. Add OIDC/JWT auth, RBAC and **server-derived** tenant scope on every query. Do not trust `X-Tenant-ID` supplied by a browser as authorization.
3. Move raw uploaded files to private object storage; add deletion/retention controls and audit log events. Current upload rows are stored in the DB for the prototype.
4. Add async ingestion jobs and file safety controls (malware scan, compression bomb limits, column/row quotas).
5. Implement client-specific normalization, primary-key validation, currency/period validation, duplicate handling and reconciliations.
6. Implement deterministic exception rules that derive exceptions from uploaded rows; currently seeded exceptions and uploaded workbooks are separate by design.
7. Implement real SAP/Oracle adapters using approved released interfaces; the connector catalog only describes the planned options.
8. Wire the HTML UI to these endpoints (currently the HTML is preserved under `frontend_reference` as an unmodified reference); then migrate to Next.js/React.
9. Add tenant isolation tests, integration tests, rate limiting, secrets management, audit trail, structured logging, metrics, backups and incident/restore drills.

## Test

```bash
pytest -q
# Database migrations (from repo root):
alembic upgrade head
```

The test suite checks catalog coverage, seeded demo API responses, a real sample workbook upload/read, and action create/update.

## Browser UI (initial API integration)

The current HTML UI is served from the same FastAPI service at `/`. It requests dashboard KPIs, priority exceptions, the exception queue, controls, and investigation detail from the deployed API. If `API_ACCESS_KEY` is set, the UI exchanges the key for a short-lived signed `HttpOnly` cookie; the key is not embedded in browser JavaScript or stored in browser storage. See `docs/FRONTEND_DEPLOYMENT.md` for deployment notes and known remaining work.

This shared-key UI login is an interim staging/demo mechanism. Do not use it as multi-user enterprise authentication or expose the shared key to customers. Production requires OIDC/OAuth2 identity, tenant-scoped authorization and audit logging.
