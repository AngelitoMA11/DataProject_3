variable "container_name" {
  description = "Name of the container"
  type        = string
}

variable "image_name" {
  description = "Name of the Docker image"
  type        = string
}

variable "ports" {
  description = "Port mappings for the container"
  type        = map(string)
}

variable "environment" {
  description = "Environment variables for the container"
  type        = map(string)
  default     = {}
} 