resource "google_artifact_registry_repository" "grafana_repo" {
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
}

resource "null_resource" "docker_auth" {
  provisioner "local-exec" {
    command = "gcloud auth configure-docker ${var.region}-docker.pkg.dev"
  }

  depends_on = [google_artifact_registry_repository.grafana_repo]
}

resource "null_resource" "build_push_image" {
    triggers = {
    always_run = "${timestamp()}"
  } 
  provisioner "local-exec" {
    command = <<EOT
        docker build --platform=linux/amd64 -t ${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}/${var.image_name}:latest ${path.module}/docker && docker push ${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}/${var.image_name}:latest 
    EOT
  }
  depends_on = [null_resource.docker_auth]
}

resource "google_cloud_run_service" "grafana" {
  name     = var.grafana_name
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}/${var.image_name}:latest"
        ports {
          container_port = 3000
        }
        env {
          name  = "GF_SECURITY_ADMIN_USER"
          value = var.user_grafana
        }

        env {
          name  = "GF_SECURITY_ADMIN_PASSWORD"
          value = var.password_grafana
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
}
    depends_on = [ null_resource.build_push_image ]
}

resource "google_cloud_run_service_iam_member" "grafana_invoker" {
  service  = google_cloud_run_service.grafana.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
