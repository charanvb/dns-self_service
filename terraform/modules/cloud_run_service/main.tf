resource "google_cloud_run_v2_service" "this" {
  name     = var.service_name
  project  = var.project_id
  location = var.location
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = var.service_account_email

    containers {
      image = var.image

      ports {
        container_port = var.container_port
      }

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

    dynamic "vpc_access" {
      for_each = var.vpc_network != null ? [1] : []
      content {
        network_interfaces {
          network    = var.vpc_network
          subnetwork = var.vpc_subnetwork
        }
        egress = var.vpc_egress
      }
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      # IAP is enabled via Console (Security tab) and stored as a service
      # annotation — not declared here, so without this Terraform would
      # strip it back out on every apply.
      annotations,
      template[0].containers[0].image,
    ]
  }
}

# No Terraform-managed public/allUsers invoker binding — org policy
# (Domain Restricted Sharing) blocks it. Access is via Identity-Aware Proxy,
# enabled once through the Console (Cloud Run service -> Security tab),
# which grants the IAP service agent run.invoker automatically.
