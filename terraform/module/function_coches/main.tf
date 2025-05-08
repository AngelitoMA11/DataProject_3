resource "google_storage_bucket" "function_bucket" {
  name          = "zip-coches-storage"
  location      = var.region
  force_destroy = true
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "google_pubsub_topic" "default" {
  name = var.topic
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "${var.name}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = "${path.module}/${var.name}.zip"
}


resource "google_cloudfunctions2_function" "function" {
  name     = var.name
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python310"
    entry_point = var.entry_point
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.function_zip.name
      }
    }
  }

  service_config {
    available_memory = "256M"
    timeout_seconds  = 60
    environment_variables = var.env_variables
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = "projects/${var.project_id}/topics/${var.topic}"
    retry_policy   = "RETRY_POLICY_RETRY"
  }

  depends_on = [google_pubsub_topic.default]
}
