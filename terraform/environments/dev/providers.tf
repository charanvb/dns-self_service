terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Bucket/prefix supplied at `terraform init` time via -backend-config,
  # using the TF_STATE_BUCKET / TF_STATE_PREFIX GitHub Actions variables.
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
