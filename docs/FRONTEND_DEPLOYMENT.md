# Frontend deployment and API integration

The existing static HTML prototype is now served by FastAPI at `/` from `frontend_reference/investigation_copilot.html`. It uses same-origin requests to the `/api/v1/*` routes, so a separate CORS configuration is not needed for this UI.

## Browser sign-in

The page requests the overview API. If the API is protected with `API_ACCESS_KEY`, the page asks the operator to enter that key and exchanges it through `POST /ui/session` for a 12-hour signed `HttpOnly`, `Secure` (in production), `SameSite=Strict` cookie. The actual API key is never written to localStorage or sessionStorage and is not embedded in JavaScript. The backend API-key dependency accepts either the existing `X-API-Key` header (PowerShell and API clients) or the signed UI cookie (same-origin website).

This is an interim shared-key/staging login, not multi-user enterprise authentication. Before handling customer financial data, replace it with OIDC/OAuth2 identity, user/tenant authorization, and audit logging. Do not share the API access key with customers.

## Connected UI sections

- Overview KPIs and priority exceptions: `GET /api/v1/overview`
- Exceptions queue and filtering: `GET /api/v1/exceptions`
- Control cards: `GET /api/v1/controls`
- Investigation detail/evidence/hypotheses/controls: `GET /api/v1/investigations/{exception_id}`
- Investigation chat: `POST /api/v1/copilot/chat` (requires `GROQ_API_KEY` and a model available to the configured Groq project)

The upload workflow, action creation/update, data-source page and ERP connectors still need end-to-end wiring/validation; this integration intentionally does not claim those paths are complete.

## Render

Deploy the backend from the repository root as before. The frontend file must be included in the deployed repository at `frontend_reference/investigation_copilot.html`. Keep `API_ACCESS_KEY` and `DATABASE_URL` only in Render Environment, never in HTML or Git. If `AUTO_CREATE_DB=true` was temporarily enabled to initialize the demo database, switch to migrations (`alembic upgrade head`) as part of a deliberate deployment process before treating the service as production-ready.
