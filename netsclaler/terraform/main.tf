provider "citrixadc" {
  endpoint             = var.ns_endpoint
  username             = var.ns_username
  password             = var.ns_password
  insecure_skip_verify = true
}

# ============================================
# Nginx App Load Balancer Configuration
# ============================================

# Step 1: Create the service group
resource "citrixadc_servicegroup" "nginx_sg" {
  servicegroupname = "sg_nginx_apps"
  servicetype      = "HTTP"
  usip             = "NO"
}

# Step 2: Create the HTTP monitor
resource "citrixadc_lbmonitor" "http_monitor" {
  monitorname = "mon_http_nginx"
  type        = "HTTP"
  interval    = 5
  retries     = 3
  httprequest = "GET /"
}

# Step 3: Bind monitor to service group (must wait for both to exist)
resource "citrixadc_servicegroup_lbmonitor_binding" "sg_monitor_bind" {
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
  monitorname      = citrixadc_lbmonitor.http_monitor.monitorname

  depends_on = [
    citrixadc_servicegroup.nginx_sg,
    citrixadc_lbmonitor.http_monitor
  ]
}

# Step 4: Add members to service group (must wait for servicegroup)
resource "citrixadc_servicegroup_servicegroupmember_binding" "app1" {
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
  ip               = var.app1_ip
  port             = var.app1_port

  depends_on = [citrixadc_servicegroup.nginx_sg]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "app2" {
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
  ip               = var.app2_ip
  port             = var.app2_port

  depends_on = [citrixadc_servicegroup.nginx_sg]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "app3" {
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname
  ip               = var.app3_ip
  port             = var.app3_port

  depends_on = [citrixadc_servicegroup.nginx_sg]
}

# Step 5: Small delay to ensure servicegroup is fully configured
resource "time_sleep" "nginx_sg_ready" {
  create_duration = "5s"

  depends_on = [
    citrixadc_servicegroup_servicegroupmember_binding.app1,
    citrixadc_servicegroup_servicegroupmember_binding.app2,
    citrixadc_servicegroup_servicegroupmember_binding.app3,
    citrixadc_servicegroup_lbmonitor_binding.sg_monitor_bind
  ]
}

# Step 6: Create the LB vserver
resource "citrixadc_lbvserver" "nginx_lb_vserver" {
  name        = "lbv_nginx_http"
  servicetype = "HTTP"
  ipv46       = var.ns_vip
  port        = 9090
  lbmethod    = "ROUNDROBIN"
  state       = "ENABLED"

  depends_on = [time_sleep.nginx_sg_ready]
}

# Step 7: Bind service group to LB vserver
resource "citrixadc_lbvserver_servicegroup_binding" "lb_to_sg" {
  name             = citrixadc_lbvserver.nginx_lb_vserver.name
  servicegroupname = citrixadc_servicegroup.nginx_sg.servicegroupname

  depends_on = [
    citrixadc_lbvserver.nginx_lb_vserver,
    time_sleep.nginx_sg_ready
  ]
}

# ============================================
# API Service Load Balancer Configuration
# ============================================

# Step 1: Create the service group
resource "citrixadc_servicegroup" "api_sg" {
  servicegroupname = "sg_api_apps"
  servicetype      = "HTTP"
  usip             = "NO"
}

# Step 2: Create the HTTP monitor for API
resource "citrixadc_lbmonitor" "api_http_monitor" {
  monitorname = "mon_http_api"
  type        = "HTTP"
  interval    = 5
  retries     = 3
  httprequest = "GET /"
}

# Step 3: Bind monitor to service group
resource "citrixadc_servicegroup_lbmonitor_binding" "api_sg_monitor_bind" {
  servicegroupname = citrixadc_servicegroup.api_sg.servicegroupname
  monitorname      = citrixadc_lbmonitor.api_http_monitor.monitorname

  depends_on = [
    citrixadc_servicegroup.api_sg,
    citrixadc_lbmonitor.api_http_monitor
  ]
}

# Step 4: Add members to service group
resource "citrixadc_servicegroup_servicegroupmember_binding" "api_app1" {
  servicegroupname = citrixadc_servicegroup.api_sg.servicegroupname
  ip               = var.api_app1_ip
  port             = var.api_app1_port

  depends_on = [citrixadc_servicegroup.api_sg]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "api_app2" {
  servicegroupname = citrixadc_servicegroup.api_sg.servicegroupname
  ip               = var.api_app2_ip
  port             = var.api_app2_port

  depends_on = [citrixadc_servicegroup.api_sg]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "api_app3" {
  servicegroupname = citrixadc_servicegroup.api_sg.servicegroupname
  ip               = var.api_app3_ip
  port             = var.api_app3_port

  depends_on = [citrixadc_servicegroup.api_sg]
}

# Step 5: Small delay to ensure servicegroup is fully configured
resource "time_sleep" "api_sg_ready" {
  create_duration = "5s"

  depends_on = [
    citrixadc_servicegroup_servicegroupmember_binding.api_app1,
    citrixadc_servicegroup_servicegroupmember_binding.api_app2,
    citrixadc_servicegroup_servicegroupmember_binding.api_app3,
    citrixadc_servicegroup_lbmonitor_binding.api_sg_monitor_bind
  ]
}

# Step 6: Create the LB vserver (wait for nginx LB to complete first to avoid VIP conflicts)
resource "citrixadc_lbvserver" "api_lb_vserver" {
  name        = "lbv_api_http"
  servicetype = "HTTP"
  ipv46       = var.ns_vip
  port        = 9091
  lbmethod    = "ROUNDROBIN"
  state       = "ENABLED"

  depends_on = [
    time_sleep.api_sg_ready,
    citrixadc_lbvserver_servicegroup_binding.lb_to_sg  # Wait for nginx LB to complete
  ]
}

# Step 7: Bind service group to LB vserver
resource "citrixadc_lbvserver_servicegroup_binding" "api_lb_to_sg" {
  name             = citrixadc_lbvserver.api_lb_vserver.name
  servicegroupname = citrixadc_servicegroup.api_sg.servicegroupname

  depends_on = [
    citrixadc_lbvserver.api_lb_vserver,
    time_sleep.api_sg_ready
  ]
}
