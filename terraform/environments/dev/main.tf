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

module "db_migrate_job" {
  source = "../../modules/cloud_run_job"

  project_id             = var.project_id
  location               = var.region
  job_name               = "dns-self-service-db-migrate"
  image                  = "us-docker.pkg.dev/cloudrun/container/job:latest" # placeholder, replaced by CI
  service_account_email  = var.runtime_service_account_email
  vpc_network            = var.vpc_network
  vpc_subnetwork         = var.vpc_subnetwork
  secret_env_vars = [
    { name = "DATABASE_URL", secret_id = "db-connection-string" },
  ]

  depends_on = [module.secret_manager]
}
