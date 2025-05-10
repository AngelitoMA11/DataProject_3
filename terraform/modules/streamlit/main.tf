resource "docker_image" "streamlit" {
  name = var.image_name
  build {
    context = "../../../streamlit_frontend"
    tag     = ["${var.image_name}:latest"]
  }
}

resource "docker_container" "streamlit" {
  name  = var.container_name
  image = docker_image.streamlit.image_id

  dynamic "ports" {
    for_each = var.ports
    content {
      internal = ports.key
      external = ports.value
    }
  }

  dynamic "env" {
    for_each = var.environment
    content {
      name  = env.key
      value = env.value
    }
  }

  networks_advanced {
    name = "travel-planner-network"
  }
} 