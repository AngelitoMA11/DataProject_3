module "pubsub" {
  source         = "./module/pubsub"
  project_id     = var.project_id
  pubsub_topics  = [
    { topic_name = var.topic_vuelos , subscription_name = var.sub_vuelos },
    { topic_name = var.topic_hoteles, subscription_name = var.sub_hoteles }
  ]
}

# module "bigquery" {
#   source     = "./module/bigquery"
#   project_id = var.project_id
#   bq_dataset = var.bq_dataset
  
#   tables = [
#     { name = "match", schema = "schemas/match.json" },
#     { name = "no_match_voluntarios", schema = "schemas/no_match_voluntarios.json" },
#     { name = "no_matches_solicitudes", schema = "schemas/no_matches_solicitudes.json" }
#   ]
# }
