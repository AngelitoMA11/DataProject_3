variable "project_id" {
  description = "ID del proyecto en GCP"
  type        = string
}

variable "bq_dataset" {
  description = "Nombre del dataset en BigQuery"
  type        = string
}

variable "tables" {
  description = "Lista de nombres de tablas con sus esquemas"
  type        = list(object({
    name   = string
    schema = string
  }))
}
