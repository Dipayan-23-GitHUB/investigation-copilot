# Applying the Investigation Copilot frontend integration patch

These files connect the included HTML UI to the included FastAPI backend. The UI is served on the same Render service at `/`.

## Files in this patch

- `app/main.py` — serves the HTML UI and implements a short-lived signed HttpOnly UI session cookie that accepts the shared API key without placing that key in browser JavaScript. Existing API clients may keep sending `X-API-Key`.
- `frontend_reference/investigation_copilot.html` — API-backed Overview, Exceptions, investigation details/evidence, controls, action listing/creation, data-source listing/file ingestion, plus connector catalog and a non-persistent connection setup preview.
- `tests/test_api.py` — includes a test for the frontend and cookie-based UI session.
- `README.md` and `docs/FRONTEND_DEPLOYMENT.md` — explain the integration and limitations.

## Apply to your existing repository

1. Extract this patch into the **root of your existing cloned GitHub repository**, keeping folder paths and allowing it to overwrite matching files.
2. Review the changes with `git status` and `git diff`.
3. Run `pytest -q` from the repository root. The test suite should report six passing tests.
4. Commit and push the changes. Render should redeploy automatically if auto-deploy is enabled.
5. Open `https://YOUR-RENDER-SERVICE.onrender.com/`, sign in using the value stored in Render's `API_ACCESS_KEY` environment variable, and test Overview, Exceptions, an investigation, file upload and actions.

PowerShell commands to commit/push (run in the repository root):

```powershell
git status
git add app/main.py frontend_reference/investigation_copilot.html README.md docs/FRONTEND_DEPLOYMENT.md tests/test_api.py
git commit -m "Connect Investigation Copilot frontend to API"
git push origin main
```

If your default branch is not `main`, use that branch name instead.

## Security and completeness notes

The UI session exchanges the shared key for a signed, 12-hour HttpOnly cookie. This is an interim staging/demo mechanism, not enterprise user authentication. Replace it with OIDC/OAuth2 and tenant-aware authorization before processing customer data. Keep `API_ACCESS_KEY`, `DATABASE_URL` and `GROQ_API_KEY` in Render's Environment settings, never in the repository.

Overview, exception data, investigation details/evidence, controls, actions (list/create), upload ingestion, data-source listing, and connector catalog are wired to existing API routes. The connection setup preview intentionally does **not** submit or persist connection credentials or test an ERP connection because secure credential vaulting and direct connector adapters are not implemented. The AI chat uses the backend's Groq endpoint; it requires a valid `GROQ_API_KEY` and available configured model.
