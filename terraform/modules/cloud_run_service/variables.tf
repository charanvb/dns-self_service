variable "project_id" {
  type = string
}

variable "location" {
  type = string
}

variable "service_name" {
  type = string
}

variable "image" {
  type        = string
  description = "Initial placeholder image; actual image is deployed out-of-band by CI, Terraform ignores changes to it"
}

variable "container_port" {
  type    = number
  default = 8080
}

variable "service_account_email" {
  type = string
}

variable "allow_unauthenticated" {
  type        = bool
  default     = false
  description = "True for the public-facing UI; false for internal backend capabilities"
}

variable "env_vars" {
  type    = list(object({ name = string, value = string }))
  default = []
}

variable "secret_env_vars" {
  type    = list(object({ name = string, secret_id = string }))
  default = []
}

variable "vpc_network" {
  type    = string
  default = null
}

variable "vpc_subnetwork" {
  type    = string
  default = null
}
