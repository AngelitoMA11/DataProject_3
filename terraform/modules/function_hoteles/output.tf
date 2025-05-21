output "function_hoteles_url" {
  value = google_cloudfunctions2_function.function_hoteles.service_config[0].uri
  description = "Nombre del servicio Cloud Run apidata"
}