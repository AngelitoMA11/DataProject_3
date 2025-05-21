terraform {
  backend "gcs" {
    bucket  = "terraform-state-viajes"
    prefix  = "estado/terraform.tfstate"
  }
}


module "bigquery" {
  source     = "./modules/bigquery"
  project_id = var.project_id
  bq_dataset = var.bq_dataset
  
  tables = [
    { name = var.table_vuelos, schema = "schemas/vuelos.json" },
    { name = var.table_hoteles, schema = "schemas/hoteles.json" },
    { name = var.table_coches, schema = "schemas/coches.json" },
    { name = var.table_usuarios, schema = "schemas/usuarios.json" },
    { name = var.table_viajes, schema = "schemas/viajes.json" }
  ]
}


module "function_hoteles" {
  source = "./modules/function_hoteles"
  project_id     = var.project_id
  region         = var.region
  name           = "hoteles"
  entry_point    = "buscar_hoteles"
  env_variables  = {
    PROJECT_ID     = var.project_id
    DATASET        = var.bq_dataset
    TABLE          = var.table_hoteles
    RAPIDAPI_KEY   = var.RAPIDAPI_KEY
    SERPAPI_KEY    = var.SERPAPI_KEY
  }
  depends_on = [ module.apidata ]

}

module "function_vuelos" {
  source      = "./modules/function_vuelos"
  project_id  = var.project_id
  region      = var.region
  name        = "vuelos"
  entry_point = "buscar_vuelos"
  env_variables = {
    PROJECT_ID     = var.project_id
    DATASET        = var.bq_dataset
    TABLE          = var.table_vuelos
    RAPIDAPI_KEY   = var.RAPIDAPI_KEY
    API_DATA_URL   = module.apidata.api_data_url
    SERPAPI_KEY    = var.SERPAPI_KEY
  }
  depends_on = [ module.apidata ]

}


module "function_coches" {
  source = "./modules/function_coches"
  project_id     = var.project_id
  region         = var.region
  name           = "coches"
  entry_point    = "buscar_coches"
  env_variables  = {
    PROJECT_ID     = var.project_id
    DATASET        = var.bq_dataset
    TABLE          = var.table_coches
    RAPIDAPI_KEY   = var.RAPIDAPI_KEY
    API_DATA_URL   = module.apidata.api_data_url
  }
  depends_on = [ module.apidata ]
}

 module "apidata" {
  source                 = "./modules/apidata"
  project_id             = var.project_id
  region                 = var.region
  cloud_run_service_name = var.cloud_run_service_api_data
  repository_name        = var.repository_name_api_data
  image_name             = var.image_name_api_data
  dataset                = var.bq_dataset
  table_usuarios         = var.table_usuarios
  table_viajes           = var.table_viajes
}

module "apiagent" {
  source                 = "./modules/apiagent"
  project_id             = var.project_id
  region                 = var.region
  cloud_run_service_name = var.cloud_run_service_api_agent
  repository_name        = var.repository_name_api_agent
  image_name             = var.image_name_api_agent
  DATABASE_URL           = var.DATABASE_URL
  API_VERSION            = var.API_VERSION
  DEBUG_MODE             = var.DEBUG_MODE
  LANGRAPH_API_KEY       = var.LANGRAPH_API_KEY
  DEFAULT_CURRENCY       = var.DEFAULT_CURRENCY
  GOOGLE_API_KEY         = var.GOOGLE_API_KEY
  SERPAPI_API_KEY        = var.SERPAPI_KEY
  SKYSCANNER_API_KEY     = var.SKYSCANNER_API_KEY
  EXA_API_KEY            = var.EXA_API_KEY
  FIRECRAWL_API_KEY      = var.FIRECRAWL_API_KEY
  TAVILY_API_KEY         = var.TAVILY_API_KEY
  
}

module "streamlit" {
  source                 = "./modules/streamlit"
  project_id             = var.project_id
  region                 = var.region
  cloud_run_service_name = var.cloud_run_service_api_streamlit
  repository_name        = var.repository_name_api_streamlit
  image_name             = var.image_name_api_streamlit
}

module "injector" {
  source             = "./modules/url_injector"
  project_id         = var.project_id
  region             = var.region
  api_agent_name     = module.apiagent.api_agent_name
  api_agent_url      = module.apiagent.api_agent_url
  api_data_url       = module.apidata.api_data_url
  streamlit_name     = module.streamlit.streamlit_name
  function_vuelos    = module.function_vuelos.function_vuelos_url
  function_hoteles   = module.function_hoteles.function_hoteles_url
  function_coches    = module.function_coches.function_coches_url
  api_data_name      = module.apidata.api_data_name
  depends_on         = [module.streamlit, module.apiagent, module.apidata, module.function_coches, module.function_hoteles, module.function_vuelos]
}

module "grafana" {
  source           = "./modules/grafana"
  project_id       = var.project_id
  region           = var.region
  password_grafana = var.password_grafana
  user_grafana     = var.user_grafana
  repository_id    = var.repository_id_grafana
  grafana_name     = var.grafana_name
  image_name       = var.image_name_grafana

}