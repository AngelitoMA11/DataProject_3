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
    { name = var.table_hoteles, schema = "schemas/hoteles.json" },
    { name = var.table_coches, schema = "schemas/coches.json" }
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

module "function_vuelos" {
  source = "./module/function_vuelos"
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

module "function_coches" {
  source = "./module/function_coches"
  project_id     = var.project_id
  region         = var.region
  name           = "coches"
  entry_point    = "limpieza_coches"
  topic          = var.topic_coches
  env_variables  = {
    PROJECT_ID = var.project_id
    DATASET    = var.bq_dataset
    TABLE      = var.table_coches
  }
}


