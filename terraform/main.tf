terraform {
  backend "gcs" {
    bucket  = "terraform-state-viajes"
    prefix  = "estado/terraform.tfstate"
  }
}


module "pubsub" {
  source         = "./module/pubsub"
  project_id     = var.project_id
  pubsub_topics  = [
    { topic_name = var.topic_vuelos , subscription_name = var.sub_vuelos },
    { topic_name = var.topic_hoteles, subscription_name = var.sub_hoteles }
  ]
}

module "bigquery" {
  source     = "./module/bigquery"
  project_id = var.project_id
  bq_dataset = var.bq_dataset
  
  tables = [
    { name = "vuelos", schema = "schemas/vuelos.json" },
    { name = "hoteles", schema = "schemas/hoteles.json" }
  ]
}
