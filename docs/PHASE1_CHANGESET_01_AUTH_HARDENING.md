# Phase 1 — Stabilization change set 01

## Production authentication fails closed

### Problem
The deployed baseline allowed protected API requests when `API_ACCESS_KEY` was empty. The browser session endpoint also returned an unauthenticated success response in that state. This meant a missing production secret could silently disable the shared-key gate.

### Change
- When `APP_ENV=production` and `API_ACCESS_KEY` is empty, protected API routes return HTTP 503 with a configuration message.
- The `/ui/session` endpoint also returns HTTP 503 in that configuration; it no longer issues an unauthenticated browser session.
- Non-production environments retain the existing no-key behavior so local development and automated tests remain convenient.
- Existing shared-key header and signed HttpOnly cookie behavior is otherwise unchanged.

### Validation
- `python -m pytest -q`: 8 passed.
- `python -m compileall -q app tests`: passed.

### Render configuration
Confirm these environment variables in Render before deployment:
- `APP_ENV=production`
- `API_ACCESS_KEY` = a strong secret value stored in Render Environment (not in source control or browser code).

### Scope limitation
This change closes the missing-key bypass only. The shared API key is still an interim single-secret access mechanism. It does not provide individual user identity, role-based access, or enforced tenant isolation. Do not treat this patch as a production security certification or use it to justify loading real customer financial data.
