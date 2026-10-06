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

module "inventory_sync_job" {
  source = "../../modules/cloud_run_job"

  project_id            = var.project_id
  location              = var.region
  job_name              = "dns-self-service-inventory-sync"
  image                 = "us-docker.pkg.dev/cloudrun/container/job:latest" # placeholder, replaced by CI
  service_account_email = var.runtime_service_account_email
  vpc_network           = var.vpc_network
  vpc_subnetwork        = var.vpc_subnetwork
  vpc_egress            = "ALL_TRAFFIC" # Micetro is only reachable via the corporate/Azure network path
  timeout               = "3600s"
  env_vars = [
    { name = "MICETRO_API_URL", value = "https://ssportal-qa.unilever.com/mmws/api/v2" },
    # Scoped to a small subset for the first test run — raise/remove once verified.
    { name = "SYNC_MAX_ZONES", value = "50" },
    { name = "SYNC_PAGE_SIZE", value = "200" },
  ]
  secret_env_vars = [
    { name = "DATABASE_URL", secret_id = "db-connection-string" },
    { name = "MICETRO_API_USERNAME", secret_id = "micetro-api-username" },
    { name = "MICETRO_API_PASSWORD", secret_id = "micetro-api-password" },
  ]

  depends_on = [module.secret_manager]
}

module "ui_service" {
  source = "../../modules/cloud_run_service"

  project_id             = var.project_id
  location               = var.region
  service_name           = "dns-self-service-ui"
  image                  = "us-docker.pkg.dev/cloudrun/container/hello:latest" # placeholder, replaced by CI
  service_account_email  = var.runtime_service_account_email
  allow_unauthenticated  = true
  vpc_network            = var.vpc_network
  vpc_subnetwork         = var.vpc_subnetwork
  vpc_egress             = "ALL_TRAFFIC" # UI now calls Micetro live (request wizard) — same reachability fix as inventory-sync
  env_vars = [
    { name = "MICETRO_API_URL", value = "https://ssportal-qa.unilever.com/mmws/api/v2" },
  ]
  secret_env_vars = [
    { name = "DATABASE_URL", secret_id = "db-connection-string" },
    { name = "APP_AUTH_SIGNING_KEY", secret_id = "app-auth-signing-key" },
    { name = "MICETRO_API_USERNAME", secret_id = "micetro-api-username" },
    { name = "MICETRO_API_PASSWORD", secret_id = "micetro-api-password" },
  ]

  depends_on = [module.secret_manager]
}
