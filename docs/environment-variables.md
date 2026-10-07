# Environment variables / configuration

Runtime config is injected via environment variables; secret values are mounted/read from Secret Manager
(never hard-coded, never committed). See `.env.example` for the full variable list.

## Secret Manager secrets (values set out-of-band, Terraform only manages the containers)

| Secret ID | Purpose |
|---|---|
| `db-connection-string` | PostgreSQL connection string (uses the Azure-internal IP, not a hostname — DNS resolution from GCP doesn't work for it) |
| `micetro-api-username` | Micetro QA API user |
| `micetro-api-password` | Micetro QA API password |
| `logic-app-webhook-url` | Azure Logic App notification trigger URL |
| `azure-automation-backup-webhook-url` | Azure Automation runbook webhook (URL itself contains an auth token — treat as fully secret) |
| `azure-automation-backup-callback-secret` | HMAC key used to verify the runbook's completion callback |
| `app-auth-signing-key` | Signing key for local/test auth session tokens (pre-CIH) |

## Non-secret config

| Variable | Purpose |
|---|---|
| `APP_CALLBACK_BASE_URL` | Public base URL of the ui service, used to build the Azure Automation backup callback URL (`{base}/internal/backups/{correlationId}/complete`). Set once the Cloud Run URL is known (`terraform/environments/dev/variables.tf` `app_callback_base_url`). |

**Known open issue (Phase 9 Executor):** `/internal/backups/{correlationId}/complete` is authenticated via
HMAC only (no session cookie), meant to be called by the Azure Automation runbook — but the ui service is
currently behind IAP, which will reject the Azure-originated call before it reaches the app. This needs an
infra decision (e.g. a separate, non-IAP-fronted ingress path for just this endpoint) before the backup
callback can work end-to-end; not yet resolved.

## Local test users (Phase 3 — local auth only, replaced by CIH/SSO later)

Seeded by migration `0002_add_local_test_users`. All 6 share the same test password `Test@12345`.

| Username | Role |
|---|---|
| `requestor1`, `requestor2` | REQUESTOR |
| `zoneadmin1`, `zoneadmin2` | ZONE_ADMIN |
| `cloudopsadmin1`, `cloudopsadmin2` | CLOUDOPS_ADMIN |

Login via `POST /auth/login {"username": "...", "password": "Test@12345"}` on the UI service — sets an
httpOnly session cookie. `GET /auth/me` returns the current user; `POST /auth/logout` clears the cookie.

