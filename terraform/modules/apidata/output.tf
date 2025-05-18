output "api_data_url" {
  value       = google_cloud_run_v2_service.service-apidata.uri
  description = "URL pública del servicio Cloud Run api-data"
}
output "api_data_name" {
  description = "Nombre del servicio Cloud Run apiagent"
  value       = google_cloud_run_v2_service.service-apidata.name
}
