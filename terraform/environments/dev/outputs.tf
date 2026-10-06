output "artifact_registry_url" {
  value = module.artifact_registry.repository_url
}

output "ui_url" {
  value = module.ui_service.url
}

output "secret_ids" {
  value = module.secret_manager.secret_ids
}
