variable "name" {}

variable "entry_point" {}

variable "env_variables" {
  type = map(string)
}

variable "region" {
  description = "Región donde se despliega el Cloud Run Job"
  type        = string
}

variable "project_id" {
  description = "ID del proyecto de GCP"
  type        = string
}
