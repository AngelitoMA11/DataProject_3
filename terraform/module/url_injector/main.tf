resource "null_resource" "update-api-agent" {

  provisioner "local-exec" {
      command = <<EOT
      gcloud run services update ${var.api_agent_name} --region=${var.region} --project=${var.project_id} --update-env-vars=DATA_API_URL=${var.api_data_url}
  EOT
    }
}

resource "null_resource" "streamlit-agent" {

  provisioner "local-exec" {
      command = <<EOT
      gcloud run services update ${var.streamlit_name} --region=${var.region} --project=${var.project_id} --update-env-vars=DATA_API_URL=${var.api_data_url} --update-env-vars=AGENT_API_URL=${var.api_agent_url}
  EOT
    }
}

resource "null_resource" "hoteles-function-url" {

  provisioner "local-exec" {
      command = <<EOT
      gcloud run services update ${var.api_data_name} --region=${var.region} --project=${var.project_id} --update-env-vars=FUNC_VUELOS_URL=${var.function_vuelos} --update-env-vars=FUNC_HOTELES_URL=${var.function_hoteles} --update-env-vars=FUNC_COCHES_URL=${var.function_coches}  
  EOT
    }
}



