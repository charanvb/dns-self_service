# DNS Self-Service Automation Platform

Enterprise DNS self-service portal (Micetro-backed today, provider-abstracted for future GCP Cloud DNS migration).

## Repository layout

- `ui/` — Cloud Run web application (requestor/approver/admin UI)
- `functions/` — Cloud Run Functions grouped by business capability (zones, records, requests, approvals, execution, notifications, inventory sync)
- `shared/` — code shared across functions/UI (database, auth, models, policy engine, DNS provider abstraction, notifications)
- `terraform/` — infrastructure as code (`modules/` + per-environment `environments/dev|test|prod`)
- `tests/` — unit/integration/security tests
- `docs/` — architecture and operational docs

## Status

Phase 1 in progress: repo scaffold, Terraform bootstrap (Artifact Registry, Secret Manager containers, runtime IAM), CI/CD skeleton.
No application code yet — see `docs/` for the phased implementation plan.

## Local development

All testing and deployment happens through GitHub Actions — there is no supported local run/test workflow
(the app depends on an internal-network Azure PostgreSQL instance only reachable from GCP via VPC egress).
