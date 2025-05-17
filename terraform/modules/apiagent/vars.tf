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


variable "DATABASE_URL" {
  description = "URL de conexión a la base de datos."
  type        = string
}

variable "API_VERSION" {
  description = "Versión actual de la API."
  type        = string
}

variable "DEBUG_MODE" {
  description = "Modo de depuración (true o false)."
  type        = string
}

variable "LANGRAPH_API_KEY" {
  description = "Clave de API para Langraph."
  type        = string
  sensitive   = true
}

variable "DEFAULT_CURRENCY" {
  description = "Moneda por defecto usada en la aplicación."
  type        = string
}

variable "GOOGLE_API_KEY" {
  description = "Clave de API de Google."
  type        = string
  sensitive   = true
}

variable "SERPAPI_API_KEY" {
  description = "Clave de API de SERPAPI"
  type        = string
  sensitive   = true
}

