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
