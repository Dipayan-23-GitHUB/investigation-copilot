# Current HTML → API migration map

The unmodified file under `frontend_reference/investigation_copilot.html` is preserved for comparison. The next step is to replace its embedded constants with API calls without redesigning the UI at the same time.

| UI element | API endpoint | Notes |
|---|---|---|
| Sidebar role/modules future selector | `GET /api/v1/catalog/modules` | Returns all 12 Source Ledger modules |
| KPI cards | `GET /api/v1/overview` | Server-owned values; show `data_quality_note` and avoid overstating demo KPIs |
| Priority exceptions table | `GET /api/v1/exceptions` or `GET /api/v1/overview` | Search UI can pass `search`, `priority`, `status`, `limit`, `offset` |
| Recurring root causes | `GET /api/v1/controls` | Future version should group repeat investigations by validated root-cause/control key, not simply static copy |
| Upload Extract | `POST /api/v1/ingestions` | `FormData`: module_key, file, header_row=5; show status/warnings, then refresh data-source list |
| Evidence panel | `GET /api/v1/exceptions/{id}/evidence` | Render source references and distinguish illustrative evidence from ingested records |
| Investigation panel | `GET /api/v1/investigations/{id}` | Render finding, hypotheses, evidence, calculation and controls |
| Copilot chat | `POST /api/v1/copilot/chat` | Backend only; never call Groq directly from browser |
| Action queue | `GET /api/v1/actions` | Use `POST /api/v1/actions` and `PATCH /api/v1/actions/{id}` for persistence |
| Control library | `GET /api/v1/controls` | Control status/recurrence values remain demo fixtures until derived from validated history |
| Refresh data | re-fetch overview/exceptions/actions/controls | Future version can include ingestion timestamps and job status |

## Suggested frontend stack

Use **Next.js App Router + React + TypeScript + Tailwind CSS + shadcn/ui**. Keep the visual layout close to the current prototype; build typed components for the sidebar, KPI cards, exception table, evidence cards, hypotheses, chat, action queue and control library. Use a typed API client layer, server-side environment variable `INTERNAL_API_BASE_URL`, loading/error/empty states, and a query cache (TanStack Query is a reasonable option if most screens are client-interactive).

Do not ship Groq keys, database URLs, or long-lived ERP credentials to the browser. Browser-to-Next server/API calls should authenticate users; backend authorization must enforce both role and tenant scope.
