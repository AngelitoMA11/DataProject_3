variable "project_id" {
  description = "ID del proyecto en GCP"
  type        = string
}

variable "pubsub_topics" {
  description = "Lista de tópicos con sus suscripciones"
  type        = list(object({
    topic_name       = string
    subscription_name = string
  }))
}
