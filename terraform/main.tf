terraform {
  backend "gcs" {
    bucket  = "terraform-state-viajes"
    prefix  = "estado/terraform.tfstate"
  }
}


module "bigquery" {
  source     = "./module/bigquery"
  project_id = var.project_id
  bq_dataset = var.bq_dataset
  
  tables = [
    { name = var.table_vuelos, schema = "schemas/vuelos.json" },
    { name = var.table_hoteles, schema = "schemas/hoteles.json" }
  ]
}


module "function_hoteles" {
  source = "./module/function_hoteles"
  project_id     = var.project_id
  region         = var.region
  name           = "hoteles"
  entry_point    = "limpieza_hoteles"
  topic          = var.topic_hoteles
  env_variables  = {
    PROJECT_ID = var.project_id
    DATASET    = var.bq_dataset
    TABLE      = var.table_hoteles
  }
}
