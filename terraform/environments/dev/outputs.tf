output "artifact_registry_url" {
  value = module.artifact_registry.repository_url
}

output "secret_ids" {
  value = module.secret_manager.secret_ids
}
