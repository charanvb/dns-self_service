resource "google_cloud_run_v2_job" "this" {
  name     = var.job_name
  project  = var.project_id
  location = var.location

  template {
    template {
      containers {
        image = var.image

        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.value.name
            value = env.value.value
          }
        }

        dynamic "env" {
          for_each = var.secret_env_vars
          content {
            name = env.value.name
            value_source {
              secret_key_ref {
                secret  = env.value.secret_id
                version = "latest"
              }
            }
          }
        }
      }

      service_account = var.service_account_email
      max_retries      = 1
      timeout          = var.timeout

      dynamic "vpc_access" {
        for_each = var.vpc_network != null ? [1] : []
        content {
          network_interfaces {
            network    = var.vpc_network
            subnetwork = var.vpc_subnetwork
          }
          egress = "PRIVATE_RANGES_ONLY"
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image]
  }
}
