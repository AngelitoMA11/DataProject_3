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


variable "bq_dataset" {
  description = "Nombre del dataset de BigQuery."
  type        = string
}

variable "table_vuelos" {
  description = "Nombre de la tabla de vuelos."
  type        = string
}

variable "table_hoteles" {
  description = "Nombre de la tabla de hoteles."
  type        = string
}

