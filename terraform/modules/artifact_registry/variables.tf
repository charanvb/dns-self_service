variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "location" {
  type        = string
  description = "Artifact Registry location"
}

variable "repository_id" {
  type        = string
  description = "Repository ID"
}

variable "description" {
  type        = string
  default     = "Container images"
}

variable "untagged_ttl_days" {
  type        = number
  description = "Delete untagged images older than this many days"
  default     = 14
}
