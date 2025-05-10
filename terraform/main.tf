terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

# Módulo para el frontend de Streamlit
module "streamlit_frontend" {
  source = "./modules/streamlit"

  container_name = "streamlit_frontend"
  image_name     = "travel-planner-frontend"
  ports = {
    "8501" = "8501"
  }
  environment = {
    "API_AGENT_URL" = "http://api_agent:8000"
    "API_DATA_URL"  = "http://api_data:8001"
  }
}

# Módulo para el agente de IA
module "api_agent" {
  source = "./modules/api_agent"

  container_name = "api_agent"
  image_name     = "travel-planner-agent"
  ports = {
    "8000" = "8000"
  }
  environment = {
    "GOOGLE_API_KEY" = var.google_api_key
  }
}

# Módulo para el servicio de datos
module "api_data" {
  source = "./modules/api_data"

  container_name = "api_data"
  image_name     = "travel-planner-data"
  ports = {
    "8001" = "8001"
  }
} 