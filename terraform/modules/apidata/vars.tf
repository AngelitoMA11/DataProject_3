variable "project_id" {
  description = "ID del proyecto de GCP"
  type        = string
}

variable "region" {
  description = "Región donde se despliega el Cloud Run Job"
  type        = string
}

variable "cloud_run_service_name" {
  description = "Nombre del Cloud Run Job"
  type        = string
}

variable "repository_name" {
  description = "Nombre del repositorio en Artifact Registry"
  type        = string
}

variable "image_name" {
  description = "Nombre de la imagen en Artifact Registry"
  type        = string
}


variable "env_vars" {
  description = "Variables de entorno adicionales para el contenedor (mapa opcional)"
  type        = map(string)
  default     = {}
}

variable "dataset" {
  description = "Nombre del dataset de BigQuery."
  type        = string
}

variable "table_usuarios" {
  description = "Nombre de la tabla de hoteles."
  type        = string
}

variable "table_viajes" {
  description = "Nombre de la tabla de vuelos."
  type        = string
}