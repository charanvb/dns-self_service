variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "europe-west4"
}

variable "environment" {
  type        = string
  default     = "dev"
}

# Reusing the existing GitHub Actions deploy SA as the Cloud Run runtime identity too
# (no separate least-privilege runtime SA for now, per user decision).
variable "runtime_service_account_email" {
  type    = string
  default = "ul-fs-t-902550-svc01@ul-fs-t-902550-prj.iam.gserviceaccount.com"
}

# Secrets whose containers already exist (created manually via Console) and
# must be imported into state before the first `terraform apply` — see README.
# Remaining secrets are declared here too; Terraform creates their containers.
variable "secret_ids" {
  type = list(string)
  default = [
    "db-connection-string",
    "micetro-api-username",
    "micetro-api-password",
    "logic-app-webhook-url",
    "azure-automation-backup-webhook-url",
    "azure-automation-backup-callback-secret",
    "app-auth-signing-key",
  ]
}
