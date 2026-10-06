variable "project_id" {
  type = string
}

variable "location" {
  type = string
}

variable "job_name" {
  type = string
}

variable "image" {
  type        = string
  description = "Initial placeholder image; actual image is deployed out-of-band by CI, Terraform ignores changes to it"
}

variable "service_account_email" {
  type = string
}

variable "timeout" {
  type    = string
  default = "600s"
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
