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

## Local test users (Phase 3 — local auth only, replaced by CIH/SSO later)

Seeded by migration `0002_add_local_test_users`. All 6 share the same test password `Test@12345`.

| Username | Role |
|---|---|
| `requestor1`, `requestor2` | REQUESTOR |
| `zoneadmin1`, `zoneadmin2` | ZONE_ADMIN |
| `cloudopsadmin1`, `cloudopsadmin2` | CLOUDOPS_ADMIN |

Login via `POST /auth/login {"username": "...", "password": "Test@12345"}` on the UI service — sets an
httpOnly session cookie. `GET /auth/me` returns the current user; `POST /auth/logout` clears the cookie.

