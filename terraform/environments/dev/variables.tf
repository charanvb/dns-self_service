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
