variable "project_id" {
  description = "ID del proyecto de GCP."
  type        = string
}
  
variable "zone" {
  description = "Zona del proyecto"
  type        = string
}

variable "region" {
  description = "Región de GCP donde se desplegarán los recursos."
  type        = string
}

variable "topic_vuelos" {
  description = "Nombre del tópico de requests."
  type        = string
}

variable "topic_hoteles" {
  description = "Nombre del tópico de helpers."
  type        = string
}

variable "topic_coches" {
  description = "Nombre del tópico de helpers."
  type        = string
}

variable "bq_dataset" {
  description = "Nombre del dataset de BigQuery."
  type        = string
}

variable "table_vuelos" {
  description = "Nombre de la tabla de vuelos."
  type        = string
}

variable "table_viajes" {
  description = "Nombre de la tabla de vuelos."
  type        = string
}

variable "table_hoteles" {
  description = "Nombre de la tabla de hoteles."
  type        = string
}

variable "table_usuarios" {
  description = "Nombre de la tabla de hoteles."
  type        = string
}

variable "table_coches" {
  description = "Nombre de la tabla de coches."
  type        = string
}

variable "cloud_run_service_api_data" {
  description = "Nombre del servicio de Cloud Run para el servicio de datos"
  type        = string
}

variable "repository_name_api_data" {
  description = "Nombre del repositorio de Artifact Registry donde está la imagen"
  type        = string
}

variable "image_name_api_data" {
  description = "Nombre de la imagen de contenedor (incluye tag si aplica)"
  type        = string
}

variable "cloud_run_service_api_agent" {
  description = "Nombre del servicio de Cloud Run para el servicio de datos"
  type        = string
}

variable "repository_name_api_agent" {
  description = "Nombre del repositorio de Artifact Registry donde está la imagen"
  type        = string
}

variable "image_name_api_agent" {
  description = "Nombre de la imagen de contenedor (incluye tag si aplica)"
  type        = string
}

variable "cloud_run_service_api_streamlit" {
  description = "Nombre del servicio de Cloud Run para el servicio de datos"
  type        = string
}

variable "repository_name_api_streamlit" {
  description = "Nombre del repositorio de Artifact Registry donde está la imagen"
  type        = string
}

variable "image_name_api_streamlit" {
  description = "Nombre de la imagen de contenedor (incluye tag si aplica)"
  type        = string
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

variable "SERPAPI_KEY" {
  description = "Clave de API de Google."
  type        = string
  sensitive   = true
}

variable "env_variables" {
  description = "Mapa de variables de entorno para el contenedor"
  type        = map(string)
  default     = {}
}

variable "RAPIDAPI_KEY" {
  description = "Clave de API para acceder a RapidAPI"
  type        = string
  sensitive   = true
}

variable "user_grafana" {
  type = string
}

variable "password_grafana" {
  type = string
}

variable "repository_id_grafana" {
  description = "ID del repositorio de Grafana en Artifact Registry"
  type        = string  
}

variable "image_name_grafana" {
  description = "ID del repositorio de Grafana en Artifact Registry"
  type        = string  
}

variable "grafana_name" {
  description = "ID del repositorio de Grafana en Artifact Registry"
  type        = string  
}

variable "TAVILY_API_KEY" {
  type      = string
  sensitive = true
}

variable "FIRECRAWL_API_KEY" {
  type      = string
  sensitive = true
}

variable "EXA_API_KEY" {
  type      = string
  sensitive = true
}

variable "SKYSCANNER_API_KEY" {
  type      = string
  sensitive = true
}
