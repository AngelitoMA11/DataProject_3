resource "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_name
  format        = "DOCKER"
}

# Autenticación con Artifact Registry
resource "null_resource" "docker_auth" {
  provisioner "local-exec" {
    command = "gcloud auth configure-docker ${var.region}-docker.pkg.dev"
  }

  depends_on = [google_artifact_registry_repository.repo]
}

# Construcción de la imagen con Docker y push a Artifact Registry
resource "null_resource" "build_push_image" {
    triggers = {
    always_run = "${timestamp()}"
  } 
  provisioner "local-exec" {
    command = <<EOT
        docker build --platform=linux/amd64 -t ${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/${var.image_name}:latest ${path.module}/../../../apps/apiagent && docker push ${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/${var.image_name}:latest 
    EOT
  }
  depends_on = [null_resource.docker_auth]
}


resource "google_cloud_run_v2_service" "service-apiagent" {
  name     = var.cloud_run_service_name
  location = var.region
  project  = var.project_id
  deletion_protection = false
  template {
      containers {
        image = "europe-west1-docker.pkg.dev/${var.project_id}/${var.repository_name}/${var.image_name}:latest"

      env {
        name  = "DATABASE_URL"
        value = var.DATABASE_URL
      }

      env {
        name  = "API_VERSION"
        value = var.API_VERSION
      }

      env {
        name  = "DEBUG_MODE"
        value = var.DEBUG_MODE
      }

      env {
        name  = "LANGRAPH_API_KEY"
        value = var.LANGRAPH_API_KEY
      }

      env {
        name  = "DEFAULT_CURRENCY"
        value = var.DEFAULT_CURRENCY
      }

      env {
        name  = "GOOGLE_API_KEY"
        value = var.GOOGLE_API_KEY
      }

      env {
        name  = "DATA_API_URL"
        value = ""
      }

      env {
        name  = "SERPAPI_API_KEY"
        value = var.SERPAPI_API_KEY
      }
      
      env {
        name  = "TAVILY_API_KEY"
        value = var.TAVILY_API_KEY
      }

      env {
        name  = "FIRECRAWL_API_KEY"
        value = var.FIRECRAWL_API_KEY
      }

      env {
        name  = "EXA_API_KEY"
        value = var.EXA_API_KEY
      }

      env {
        name  = "SKYSCANNER_API_KEY"
        value = var.SKYSCANNER_API_KEY
      }

      ports {
        container_port = 8000
      }
      
    }
  }

  traffic {
    type = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [ null_resource.build_push_image ]
}


# Permitir acceso público
resource "google_cloud_run_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloud_run_v2_service.service-apiagent.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
