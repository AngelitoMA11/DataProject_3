output "streamlit_name" {
  description = "Nombre del servicio Cloud Run apidata"
  value       = google_cloud_run_v2_service.streamlit.name
}
