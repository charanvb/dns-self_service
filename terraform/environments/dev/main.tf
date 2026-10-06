module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  location      = var.region
  repository_id = "dns-self-service"
  description   = "DNS Self-Service Automation Platform container images"
}

module "secret_manager" {
  source = "../../modules/secret_manager"

  project_id = var.project_id
  secret_ids = var.secret_ids
  accessor_members = [
    "serviceAccount:${var.runtime_service_account_email}",
  ]
}
