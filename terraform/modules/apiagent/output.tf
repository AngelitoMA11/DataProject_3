output "api_agent_url" {
  value       = google_cloud_run_v2_service.service-apiagent.uri
  description = "URL pública del servicio Cloud Run api-data"
}
output "api_agent_name" {
  description = "Nombre del servicio Cloud Run apiagent"
  value       = google_cloud_run_v2_service.service-apiagent.name
}