variable "project_id" {
  description = "ID del proyecto de Google Cloud"
  type        = string
}

variable "region" {
  description = "Región de despliegue de los recursos en Google Cloud"
  type        = string
}
variable "api_agent_name" {
  type        = string
  description = "URL que se inyectará en la variable de entorno AGENT_URL"
}

variable "api_data_name" {
  type        = string
  description = "URL que se inyectará en la variable de entorno AGENT_URL"
}

variable "api_agent_url" {
  type        = string
  description = "URL que se inyectará en la variable de entorno TELEGRAM_URL"
}

variable "streamlit_name" {
  type        = string
  description = "Nombre del servicio Cloud Run (Agente) a actualizar"
}

variable "api_data_url" {
  type        = string
  description = "Nombre del servicio Cloud Run (Telegram) a actualizar"
}

variable "function_vuelos" {
  type        = string
  description = "Nombre del servicio de function vuelos"
}

variable "function_hoteles" {
  type        = string
  description = "Nombre del servicio de function vuelos"
}

variable "function_coches" {
  type        = string
  description = "Nombre del servicio de function vuelos"
}
