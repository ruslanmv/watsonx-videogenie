variable "region" {
  description = "IBM Cloud region code"
  type        = string
  default     = "eu-de"
}

variable "domain" {
  description = "Root DNS zone"
  type        = string
}

variable "prefix" {
  description = "Resource prefix"
  type        = string
  default     = "vg"
}

variable "event_streams_plan" {
  description = "Kafka plan tier"
  type        = string
  default     = "standard"
}

variable "cos_class" {
  description = "COS storage class"
  type        = string
  default     = "standard"
}

variable "watsonx_apikey" {
  description = "watsonx API key stored in Secrets Manager"
  type        = string
  sensitive   = true
}
