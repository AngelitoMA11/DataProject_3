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
        docker build --platform=linux/amd64 -t ${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/${var.image_name}:latest ${path.module}/../../../apps/streamlit && docker push ${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/${var.image_name}:latest 
    EOT
  }
  depends_on = [null_resource.docker_auth]
}


resource "google_cloud_run_v2_service" "streamlit" {
  name     = var.cloud_run_service_name
  location = var.region
  project  = var.project_id
  deletion_protection = false

  template {

      containers {
        image = "europe-west1-docker.pkg.dev/${var.project_id}/${var.repository_name}/${var.image_name}:latest"

      env {
        name  = "AGENT_API_URL"
        value = ""
      }

      env {
        name  = "DATA_API_URL"
        value = ""
      }

      ports {
        container_port = 8501
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
  service  = google_cloud_run_v2_service.streamlit.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
