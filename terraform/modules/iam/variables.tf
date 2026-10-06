variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "environment" {
  type        = string
  description = "Environment name (dev/test/prod)"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names"
  default     = "dns-self-service"
}
