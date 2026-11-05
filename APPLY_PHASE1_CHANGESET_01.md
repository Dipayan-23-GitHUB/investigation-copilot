# Apply Phase 1 — Change Set 01

This is a small security-hardening patch against the uploaded deployed baseline.

## Files changed
- `app/main.py`
- `tests/test_api.py`
- `README.md`
- `docs/PHASE1_CHANGESET_01_AUTH_HARDENING.md`

## Apply
1. Back up your current GitHub working copy or commit any uncommitted changes.
2. Extract the patch ZIP into the repository root, preserving folders and allowing these files to be replaced.
3. Inspect the changes with `git diff`.
4. Run:

   ```powershell
   python -m pytest -q
   python -m compileall -q app tests
   ```

5. Commit and push the changes to the branch connected to Render.
6. Wait for Render to finish deploying, then check `/health/ready` and sign in to the application using the configured API access key.

## Required Render settings
- `APP_ENV=production`
- `API_ACCESS_KEY` set to a strong secret in Render Environment.

Do not paste the secret into source code, this chat, screenshots, or GitHub. Do not remove the existing production key to test the missing-key behavior; the automated tests cover that case safely.

## Expected behavior
- With a configured key: the normal sign-in flow continues to work.
- With the key missing in production: protected API requests and `/ui/session` return HTTP 503 instead of silently allowing access.
- In local development/testing: existing no-key behavior remains available.

This change does not add enterprise user accounts, RBAC, or tenant isolation.
