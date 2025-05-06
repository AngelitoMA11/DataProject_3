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

module "function_vuelos" {
  source = "./module/function"
  project_id     = var.project_id
  region         = var.region
  name           = "vuelos"
  entry_point    = "limpieza_vuelos"
  topic          = var.topic_vuelos
  env_variables  = {
    PROJECT_ID = var.project_id
    DATASET    = var.bq_dataset
    TABLE      = var.table_vuelos
  }
}
