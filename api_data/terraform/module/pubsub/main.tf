# Crear múltiples tópicos de Pub/Sub
resource "google_pubsub_topic" "topics" {
  for_each = { for t in var.pubsub_topics : t.topic_name => t }

  name    = each.value.topic_name
  project = var.project_id
}

# Crear múltiples suscripciones para cada tópico
resource "google_pubsub_subscription" "subscriptions" {
  for_each = { for t in var.pubsub_topics : t.subscription_name => t }

  name  = each.value.subscription_name
  topic = google_pubsub_topic.topics[each.value.topic_name].id
  project = var.project_id
}
