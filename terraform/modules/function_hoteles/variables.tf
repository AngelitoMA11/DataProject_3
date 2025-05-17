variable "name" {}

variable "entry_point" {}

variable "env_variables" {
  type = map(string)
}

variable "project_id" {
  description = "ID del proyecto de GCP."
  type        = string
}

variable "region" {
  description = "Región de GCP donde se desplegarán los recursos."
  type        = string
}
