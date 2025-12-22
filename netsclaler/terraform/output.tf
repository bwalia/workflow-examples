output "netscaler_management_url" {
  description = "NetScaler Management Console URL"
  value       = var.ns_endpoint
}

output "netscaler_api_url" {
  description = "NetScaler NITRO API URL"
  value       = "${var.ns_endpoint}/nitro/v1/config"
}

output "lb_vserver_name" {
  description = "Load Balancer Virtual Server Name"
  value       = citrixadc_lbvserver.nginx_lb_vserver.name
}

output "lb_vserver_url" {
  description = "Load Balancer Public URL (accessible via host port)"
  value       = "http://185.237.99.238:9090"
}

output "service_group_name" {
  description = "Service Group Name"
  value       = citrixadc_servicegroup.nginx_sg.servicegroupname
}

output "app1_backend" {
  description = "App 1 Backend"
  value       = "${var.app1_ip}:${var.app1_port}"
}

output "app2_backend" {
  description = "App 2 Backend"
  value       = "${var.app2_ip}:${var.app2_port}"
}

output "app3_backend" {
  description = "App 3 Backend"
  value       = "${var.app3_ip}:${var.app3_port}"
}
