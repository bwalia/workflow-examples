provider "citrixadc" {
  endpoint = var.ns_endpoint
  username = var.ns_username
  password = var.ns_password
  insecure_skip_verify = true
}

# NSIP resource removed - not needed when using management IP for services
# resource "citrixadc_nsip" "snip_host" {
#   ipaddress = var.ns_host_ip
#   netmask   = "255.255.255.0"
#   type      = "SNIP"
# }

resource "citrixadc_servicegroup" "nginx_sg" {
  servicegroupname = "sg_nginx_apps"
  servicetype      = "HTTP"
  usip             = "NO"
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "app1" {
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
  ip               = var.app1_ip
  port             = var.app1_port
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "app2" {
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
  ip               = var.app2_ip
  port             = var.app2_port
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "app3" {
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
  ip               = var.app3_ip
  port             = var.app3_port
}

resource "citrixadc_lbmonitor" "http_monitor" {
  monitorname = "mon_http_nginx"
  type        = "HTTP"
  interval    = 5
  retries     = 3

  httprequest = "GET /"
}

resource "citrixadc_servicegroup_lbmonitor_binding" "sg_monitor_bind" {
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
  monitorname      = citrixadc_lbmonitor.http_monitor.monitorname
}

resource "citrixadc_lbvserver" "nginx_lb_vserver" {
  name        = "lbv_nginx_http"
  servicetype = "HTTP"
  ipv46       = var.ns_vip
  port        = 9090
  lbmethod    = "ROUNDROBIN"
  state       = "ENABLED"
}

resource "citrixadc_lbvserver_servicegroup_binding" "lb_to_sg" {
  name             = citrixadc_lbvserver.nginx_lb_vserver.name
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
}
