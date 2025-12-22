variable "ns_endpoint" {
  description = "NetScaler API endpoint URL"
  type        = string
}

variable "ns_vip" {
  description = "Virtual IP address for load balancer (must be valid IP)"
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

variable "ns_username" {
  type    = string
  default = "nsroot"
}

variable "ns_password" {
  type = string
}
