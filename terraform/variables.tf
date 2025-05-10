variable "google_api_key" {
  description = "API key for Google Gemini"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
} 