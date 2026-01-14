# ============================================
# NetScaler Primary Configuration
# ============================================
variable "ns_endpoint" {
  description = "NetScaler Primary API endpoint URL"
  type        = string
}

variable "ns_vip" {
  description = "Virtual IP address for Primary load balancer (must be valid IP)"
  type        = string
}

# ============================================
# NetScaler Secondary Configuration (HA)
# ============================================
variable "ns_secondary_endpoint" {
  description = "NetScaler Secondary API endpoint URL"
  type        = string
}

variable "ns_secondary_vip" {
  description = "Virtual IP address for Secondary load balancer (must be valid IP)"
  type        = string
}

variable "ns_secondary_password" {
  description = "NetScaler Secondary password"
  type        = string
}

variable "app1_ip" {
  description = "IP address for nginx app1 container"
  type        = string
}

variable "app2_ip" {
  description = "IP address for nginx app2 container"
  type        = string
}

variable "app3_ip" {
  description = "IP address for nginx app3 container"
  type        = string
}

variable "app1_port" {
  description = "Port for nginx app1"
  type        = number
  default     = 80
}

variable "app2_port" {
  description = "Port for nginx app2"
  type        = number
  default     = 80
}

variable "app3_port" {
  description = "Port for nginx app3"
  type        = number
  default     = 80
}

# API Service Backend IPs
variable "api_app1_ip" {
  description = "IP address for api-app1 container"
  type        = string
}

variable "api_app2_ip" {
  description = "IP address for api-app2 container"
  type        = string
}

variable "api_app3_ip" {
  description = "IP address for api-app3 container"
  type        = string
}

variable "api_app1_port" {
  description = "Port for api-app1"
  type        = number
  default     = 80
}

variable "api_app2_port" {
  description = "Port for api-app2"
  type        = number
  default     = 80
}

variable "api_app3_port" {
  description = "Port for api-app3"
  type        = number
  default     = 80
}

# Web App Service Backend IPs
variable "web_app1_ip" {
  description = "IP address for web-app1 container"
  type        = string
}

variable "web_app2_ip" {
  description = "IP address for web-app2 container"
  type        = string
}

variable "web_app3_ip" {
  description = "IP address for web-app3 container"
  type        = string
}

variable "web_app1_port" {
  description = "Port for web-app1"
  type        = number
  default     = 80
}

variable "web_app2_port" {
  description = "Port for web-app2"
  type        = number
  default     = 80
}

variable "web_app3_port" {
  description = "Port for web-app3"
  type        = number
  default     = 80
}

variable "ns_username" {
  type    = string
  default = "nsroot"
}

variable "ns_password" {
  type = string
}
