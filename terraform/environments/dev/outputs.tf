output "artifact_registry_url" {
  value = module.artifact_registry.repository_url
}

output "runtime_service_account_email" {
  value = module.iam.runtime_service_account_email
}

output "secret_ids" {
  value = module.secret_manager.secret_ids
}
