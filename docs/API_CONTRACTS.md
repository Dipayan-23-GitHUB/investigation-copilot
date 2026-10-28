# API contracts (v1)

Base path: `/api/v1`. Swagger UI is generated at `/docs` during development.

## Read operations

### `GET /catalog/modules`
Returns the twelve Source Ledger roles, workbook/tabs, canonical source objects, header rows, expected columns, primary keys and join keys.

### `GET /catalog/source-objects?module_key=&confidence=` / `GET /catalog/source-objects/{source_key}`
Expanded Source Ledger object registry including confidence, purpose, expected fields and adapter status. A table/document/platform is not necessarily a callable API endpoint.

### `GET /overview`
Returns `{kpis, priority_exceptions, data_quality_note}`. KPIs are calculated from the API exception register. A single uploaded file alone is not enough to infer a prior-period delta; the current seeded `change_vs_prior_close` is expressly illustrative.

### `GET /exceptions?search=&status=&priority=&limit=&offset=`
Filter exception register. `impact_amount` is a magnitude and `direction` distinguishes unfavorable/favorable/exposure.

### `GET /exceptions/{id}`
Exception + attached investigation payload.

### `GET /exceptions/{id}/evidence` and `GET /investigations/{id}`
Evidence, hypotheses, calculations, proposed controls, and a `human_validation_required` flag.

### `GET /data-sources` / `GET /data-sources/{id}/sheets` / `GET /data-sources/{id}/rows?sheet_name=...`
Query ingested files, mapped sheet metadata and stored source rows. Row queries are paginated, max 500 per request.

### `GET /modules/{module_key}/records?sheet_name=&limit=&offset=`
Convenience route for the latest workbook ingested under a module. It does not merge records across separate uploads.

### `GET /actions` / `GET /controls`
Return action queue and control library.

## Write operations

### `POST /ingestions` (`multipart/form-data`)
Fields: `module_key` (required), `file` (required; `.xlsx`, `.csv`, `.json`), `header_row` (default 5). File size defaults to 25MB. Identical file/module uploads are deduplicated by SHA-256. XLSX rows above `header_row` are treated as metadata and skipped.

### `POST /actions`
Example:

```json
{
  "title": "Validate supplier price condition",
  "owner": "Procurement",
  "status": "open",
  "due_date": "2026-11-06",
  "action_type": "investigation",
  "exception_id": "case1"
}
```

### `PATCH /actions/{id}`
Supports updating title, owner, status, due_date or action_type.

### `POST /investigations/{id}/run`
Currently returns the seeded demo result for case1/case2/case3. For other exceptions it returns HTTP 409 until source mapping and deterministic rules exist. This is intentional—it must not invent root causes for unconfigured records.

### `POST /copilot/chat`
Request:

```json
{
  "exception_id": "case1",
  "message": "What proves the variance amount?",
  "conversation_history": []
}
```
The backend passes only the selected exception/investigation context to Groq, requests a structured response, and filters returned evidence IDs against the server's actual evidence IDs. It returns HTTP 503 if `GROQ_API_KEY` is not configured. It never executes ERP writes.

## Error semantics

- `400/422`: malformed upload or invalid payload.
- `401`: invalid `X-API-Key` when optional shared-key mode is enabled.
- `404`: unknown record or module.
- `409`: attempted investigation for which no rule is configured.
- `413`: file exceeds configured upload limit.
- `502/504`: external Groq failure/timeout.
- `503`: Groq not configured or readiness failure.
