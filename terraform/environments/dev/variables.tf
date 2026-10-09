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
    "app-auth-signing-key",
  ]
}

# VPC network/subnetwork that has connectivity to the Azure PostgreSQL instance.
# This is a Shared VPC — network/subnet live in the host project
# ul-fs-n-plnetwork-prj, not in this (service) project, so full resource paths
# are required rather than short names.
variable "vpc_network" {
  type    = string
  default = "projects/ul-fs-n-plnetwork-prj/global/networks/ul-fs-n-plvpc-01"
}

variable "vpc_subnetwork" {
  type    = string
  default = "projects/ul-fs-n-plnetwork-prj/regions/europe-west4/subnetworks/gnl-ec-n-subnet-01"
}

