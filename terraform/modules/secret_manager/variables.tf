variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "secret_ids" {
  type        = list(string)
  description = "Secret Manager secret IDs to declare (containers only, no values)"
}

variable "accessor_members" {
  type        = list(string)
  description = "IAM members (e.g. serviceAccount:...) granted secretAccessor on every secret in secret_ids"
  default     = []
}
