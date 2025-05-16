resource "google_storage_bucket" "function_bucket" {
  name          = "zip-coches-storage"
  location      = var.region
  force_destroy = true
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}"
  output_path = "${path.module}/${var.name}.zip"
  excludes    = ["*.tf", "*.zip"]
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "${var.name}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = "${path.module}/${var.name}.zip"  
}

resource "google_cloudfunctions2_function" "function_coches" {
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
    available_memory = "512M"
    timeout_seconds  = 60
    environment_variables = var.env_variables
  }
}

  resource "google_cloud_run_service_iam_member" "member" {
  location = google_cloudfunctions2_function.function_coches.location
  service  = google_cloudfunctions2_function.function_coches.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

 
