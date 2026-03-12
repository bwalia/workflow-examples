# ============================================
# NetScaler Secondary (HA) Configuration
# Mirrors the primary configuration for failover
# ============================================

# ============================================
# Nginx App Load Balancer Configuration (Secondary)
# ============================================

# Step 1: Create the service group
resource "citrixadc_servicegroup" "nginx_sg_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = "sg_nginx_apps"
  servicetype      = "HTTP"
  usip             = "NO"
}

# Step 2: Create the HTTP monitor
resource "citrixadc_lbmonitor" "http_monitor_secondary" {
  provider    = citrixadc.secondary
  monitorname = "mon_http_nginx"
  type        = "HTTP"
  interval    = 5
  retries     = 3
  httprequest = "GET /"
}

# Step 3: Bind monitor to service group
resource "citrixadc_servicegroup_lbmonitor_binding" "sg_monitor_bind_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.nginx_sg_secondary.servicegroupname
  monitorname      = citrixadc_lbmonitor.http_monitor_secondary.monitorname

  depends_on = [
    citrixadc_servicegroup.nginx_sg_secondary,
    citrixadc_lbmonitor.http_monitor_secondary
  ]
}

# Step 4: Add members to service group
resource "citrixadc_servicegroup_servicegroupmember_binding" "app1_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.nginx_sg_secondary.servicegroupname
  ip               = var.app1_ip
  port             = var.app1_port

  depends_on = [citrixadc_servicegroup.nginx_sg_secondary]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "app2_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.nginx_sg_secondary.servicegroupname
  ip               = var.app2_ip
  port             = var.app2_port

  depends_on = [citrixadc_servicegroup.nginx_sg_secondary]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "app3_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.nginx_sg_secondary.servicegroupname
  ip               = var.app3_ip
  port             = var.app3_port

  depends_on = [citrixadc_servicegroup.nginx_sg_secondary]
}

# Step 5: Small delay to ensure servicegroup is fully configured
resource "time_sleep" "nginx_sg_ready_secondary" {
  create_duration = "5s"

  depends_on = [
    citrixadc_servicegroup_servicegroupmember_binding.app1_secondary,
    citrixadc_servicegroup_servicegroupmember_binding.app2_secondary,
    citrixadc_servicegroup_servicegroupmember_binding.app3_secondary,
    citrixadc_servicegroup_lbmonitor_binding.sg_monitor_bind_secondary
  ]
}

# Step 6: Create the LB vserver
resource "citrixadc_lbvserver" "nginx_lb_vserver_secondary" {
  provider    = citrixadc.secondary
  name        = "lbv_nginx_http"
  servicetype = "HTTP"
  ipv46       = var.ns_secondary_vip
  port        = 9090
  lbmethod    = "ROUNDROBIN"
  state       = "ENABLED"

  depends_on = [time_sleep.nginx_sg_ready_secondary]
}

# Step 7: Bind service group to LB vserver
resource "citrixadc_lbvserver_servicegroup_binding" "lb_to_sg_secondary" {
  provider         = citrixadc.secondary
  name             = citrixadc_lbvserver.nginx_lb_vserver_secondary.name
  servicegroupname = citrixadc_servicegroup.nginx_sg_secondary.servicegroupname

  depends_on = [
    citrixadc_lbvserver.nginx_lb_vserver_secondary,
    time_sleep.nginx_sg_ready_secondary
  ]
}

# ============================================
# API Service Load Balancer Configuration (Secondary)
# ============================================

# Step 1: Create the service group
resource "citrixadc_servicegroup" "api_sg_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = "sg_api_apps"
  servicetype      = "HTTP"
  usip             = "NO"
}

# Step 2: Create the HTTP monitor for API
resource "citrixadc_lbmonitor" "api_http_monitor_secondary" {
  provider    = citrixadc.secondary
  monitorname = "mon_http_api"
  type        = "HTTP"
  interval    = 5
  retries     = 3
  httprequest = "GET /"
}

# Step 3: Bind monitor to service group
resource "citrixadc_servicegroup_lbmonitor_binding" "api_sg_monitor_bind_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.api_sg_secondary.servicegroupname
  monitorname      = citrixadc_lbmonitor.api_http_monitor_secondary.monitorname

  depends_on = [
    citrixadc_servicegroup.api_sg_secondary,
    citrixadc_lbmonitor.api_http_monitor_secondary
  ]
}

# Step 4: Add members to service group
resource "citrixadc_servicegroup_servicegroupmember_binding" "api_app1_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.api_sg_secondary.servicegroupname
  ip               = var.api_app1_ip
  port             = var.api_app1_port

  depends_on = [citrixadc_servicegroup.api_sg_secondary]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "api_app2_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.api_sg_secondary.servicegroupname
  ip               = var.api_app2_ip
  port             = var.api_app2_port

  depends_on = [citrixadc_servicegroup.api_sg_secondary]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "api_app3_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.api_sg_secondary.servicegroupname
  ip               = var.api_app3_ip
  port             = var.api_app3_port

  depends_on = [citrixadc_servicegroup.api_sg_secondary]
}

# Step 5: Small delay to ensure servicegroup is fully configured
resource "time_sleep" "api_sg_ready_secondary" {
  create_duration = "5s"

  depends_on = [
    citrixadc_servicegroup_servicegroupmember_binding.api_app1_secondary,
    citrixadc_servicegroup_servicegroupmember_binding.api_app2_secondary,
    citrixadc_servicegroup_servicegroupmember_binding.api_app3_secondary,
    citrixadc_servicegroup_lbmonitor_binding.api_sg_monitor_bind_secondary
  ]
}

# Step 6: Create the LB vserver
resource "citrixadc_lbvserver" "api_lb_vserver_secondary" {
  provider    = citrixadc.secondary
  name        = "lbv_api_http"
  servicetype = "HTTP"
  ipv46       = var.ns_secondary_vip
  port        = 9091
  lbmethod    = "ROUNDROBIN"
  state       = "ENABLED"

  depends_on = [
    time_sleep.api_sg_ready_secondary,
    citrixadc_lbvserver_servicegroup_binding.lb_to_sg_secondary
  ]
}

# Step 7: Bind service group to LB vserver
resource "citrixadc_lbvserver_servicegroup_binding" "api_lb_to_sg_secondary" {
  provider         = citrixadc.secondary
  name             = citrixadc_lbvserver.api_lb_vserver_secondary.name
  servicegroupname = citrixadc_servicegroup.api_sg_secondary.servicegroupname

  depends_on = [
    citrixadc_lbvserver.api_lb_vserver_secondary,
    time_sleep.api_sg_ready_secondary
  ]
}

# ============================================
# Web App Service Load Balancer Configuration (Secondary)
# ============================================

# Step 1: Create the service group
resource "citrixadc_servicegroup" "web_sg_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = "sg_web_apps"
  servicetype      = "HTTP"
  usip             = "NO"
}

# Step 2: Create the HTTP monitor for Web App
resource "citrixadc_lbmonitor" "web_http_monitor_secondary" {
  provider    = citrixadc.secondary
  monitorname = "mon_http_web"
  type        = "HTTP"
  interval    = 5
  retries     = 3
  httprequest = "GET /"
}

# Step 3: Bind monitor to service group
resource "citrixadc_servicegroup_lbmonitor_binding" "web_sg_monitor_bind_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.web_sg_secondary.servicegroupname
  monitorname      = citrixadc_lbmonitor.web_http_monitor_secondary.monitorname

  depends_on = [
    citrixadc_servicegroup.web_sg_secondary,
    citrixadc_lbmonitor.web_http_monitor_secondary
  ]
}

# Step 4: Add members to service group
resource "citrixadc_servicegroup_servicegroupmember_binding" "web_app1_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.web_sg_secondary.servicegroupname
  ip               = var.web_app1_ip
  port             = var.web_app1_port

  depends_on = [citrixadc_servicegroup.web_sg_secondary]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "web_app2_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.web_sg_secondary.servicegroupname
  ip               = var.web_app2_ip
  port             = var.web_app2_port

  depends_on = [citrixadc_servicegroup.web_sg_secondary]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "web_app3_secondary" {
  provider         = citrixadc.secondary
  servicegroupname = citrixadc_servicegroup.web_sg_secondary.servicegroupname
  ip               = var.web_app3_ip
  port             = var.web_app3_port

  depends_on = [citrixadc_servicegroup.web_sg_secondary]
}

# Step 5: Small delay to ensure servicegroup is fully configured
resource "time_sleep" "web_sg_ready_secondary" {
  create_duration = "5s"

  depends_on = [
    citrixadc_servicegroup_servicegroupmember_binding.web_app1_secondary,
    citrixadc_servicegroup_servicegroupmember_binding.web_app2_secondary,
    citrixadc_servicegroup_servicegroupmember_binding.web_app3_secondary,
    citrixadc_servicegroup_lbmonitor_binding.web_sg_monitor_bind_secondary
  ]
}

# Step 6: Create the LB vserver
resource "citrixadc_lbvserver" "web_lb_vserver_secondary" {
  provider    = citrixadc.secondary
  name        = "lbv_web_http"
  servicetype = "HTTP"
  ipv46       = var.ns_secondary_vip
  port        = 9092
  lbmethod    = "ROUNDROBIN"
  state       = "ENABLED"

  depends_on = [
    time_sleep.web_sg_ready_secondary,
    citrixadc_lbvserver_servicegroup_binding.api_lb_to_sg_secondary
  ]
}

# Step 7: Bind service group to LB vserver
resource "citrixadc_lbvserver_servicegroup_binding" "web_lb_to_sg_secondary" {
  provider         = citrixadc.secondary
  name             = citrixadc_lbvserver.web_lb_vserver_secondary.name
  servicegroupname = citrixadc_servicegroup.web_sg_secondary.servicegroupname

  depends_on = [
    citrixadc_lbvserver.web_lb_vserver_secondary,
    time_sleep.web_sg_ready_secondary
  ]
}
