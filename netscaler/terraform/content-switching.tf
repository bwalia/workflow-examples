# ============================================
# Content Switching Configuration (Primary)
# Single VIP on port 8888 that routes:
#   /api/*  -> API Service LB (lbv_api_http)
#   /web/*  -> Web App LB (lbv_web_http)
#   default -> Nginx App LB (lbv_nginx_http) via lbvserverbinding
# ============================================

# Enable Content Switching feature on primary CPX
resource "citrixadc_nsfeature" "cs_feature_primary" {
  provider = citrixadc.primary
  cs       = true
  lb       = true
}

# Content Switching VServer - single entry point
resource "citrixadc_csvserver" "cs_vserver" {
  provider         = citrixadc.primary
  name             = "csv_main"
  servicetype      = "HTTP"
  ipv46            = var.ns_vip
  port             = 8888
  state            = "ENABLED"
  lbvserverbinding = citrixadc_lbvserver.nginx_lb_vserver.name

  depends_on = [
    citrixadc_nsfeature.cs_feature_primary,
    citrixadc_lbvserver_servicegroup_binding.lb_to_sg,
    citrixadc_lbvserver_servicegroup_binding.api_lb_to_sg,
    citrixadc_lbvserver_servicegroup_binding.web_lb_to_sg
  ]
}

# CS Policy: route /api/* to API LB vserver
resource "citrixadc_cspolicy" "api_policy" {
  provider   = citrixadc.primary
  policyname = "csp_api"
  rule       = "HTTP.REQ.URL.STARTSWITH(\"/api\")"

  depends_on = [citrixadc_csvserver.cs_vserver]
}

# CS Policy: route /web/* to Web App LB vserver
resource "citrixadc_cspolicy" "web_policy" {
  provider   = citrixadc.primary
  policyname = "csp_web"
  rule       = "HTTP.REQ.URL.STARTSWITH(\"/web\")"

  depends_on = [citrixadc_csvserver.cs_vserver]
}

# Bind API policy to CS vserver with target LB vserver
resource "citrixadc_csvserver_cspolicy_binding" "api_binding" {
  provider        = citrixadc.primary
  name            = citrixadc_csvserver.cs_vserver.name
  policyname      = citrixadc_cspolicy.api_policy.policyname
  priority        = 100
  targetlbvserver = citrixadc_lbvserver.api_lb_vserver.name

  depends_on = [
    citrixadc_csvserver.cs_vserver,
    citrixadc_cspolicy.api_policy,
    citrixadc_lbvserver.api_lb_vserver
  ]
}

# Bind Web policy to CS vserver with target LB vserver
resource "citrixadc_csvserver_cspolicy_binding" "web_binding" {
  provider        = citrixadc.primary
  name            = citrixadc_csvserver.cs_vserver.name
  policyname      = citrixadc_cspolicy.web_policy.policyname
  priority        = 200
  targetlbvserver = citrixadc_lbvserver.web_lb_vserver.name

  depends_on = [
    citrixadc_csvserver.cs_vserver,
    citrixadc_cspolicy.web_policy,
    citrixadc_lbvserver.web_lb_vserver
  ]
}

# ============================================
# Content Switching Configuration (Secondary)
# ============================================

# Enable Content Switching feature on secondary CPX
resource "citrixadc_nsfeature" "cs_feature_secondary" {
  provider = citrixadc.secondary
  cs       = true
  lb       = true
}

resource "citrixadc_csvserver" "cs_vserver_secondary" {
  provider         = citrixadc.secondary
  name             = "csv_main"
  servicetype      = "HTTP"
  ipv46            = var.ns_secondary_vip
  port             = 8888
  state            = "ENABLED"
  lbvserverbinding = citrixadc_lbvserver.nginx_lb_vserver_secondary.name

  depends_on = [
    citrixadc_nsfeature.cs_feature_secondary,
    citrixadc_lbvserver_servicegroup_binding.lb_to_sg_secondary,
    citrixadc_lbvserver_servicegroup_binding.api_lb_to_sg_secondary,
    citrixadc_lbvserver_servicegroup_binding.web_lb_to_sg_secondary
  ]
}

resource "citrixadc_cspolicy" "api_policy_secondary" {
  provider   = citrixadc.secondary
  policyname = "csp_api"
  rule       = "HTTP.REQ.URL.STARTSWITH(\"/api\")"

  depends_on = [citrixadc_csvserver.cs_vserver_secondary]
}

resource "citrixadc_cspolicy" "web_policy_secondary" {
  provider   = citrixadc.secondary
  policyname = "csp_web"
  rule       = "HTTP.REQ.URL.STARTSWITH(\"/web\")"

  depends_on = [citrixadc_csvserver.cs_vserver_secondary]
}

resource "citrixadc_csvserver_cspolicy_binding" "api_binding_secondary" {
  provider        = citrixadc.secondary
  name            = citrixadc_csvserver.cs_vserver_secondary.name
  policyname      = citrixadc_cspolicy.api_policy_secondary.policyname
  priority        = 100
  targetlbvserver = citrixadc_lbvserver.api_lb_vserver_secondary.name

  depends_on = [
    citrixadc_csvserver.cs_vserver_secondary,
    citrixadc_cspolicy.api_policy_secondary,
    citrixadc_lbvserver.api_lb_vserver_secondary
  ]
}

resource "citrixadc_csvserver_cspolicy_binding" "web_binding_secondary" {
  provider        = citrixadc.secondary
  name            = citrixadc_csvserver.cs_vserver_secondary.name
  policyname      = citrixadc_cspolicy.web_policy_secondary.policyname
  priority        = 200
  targetlbvserver = citrixadc_lbvserver.web_lb_vserver_secondary.name

  depends_on = [
    citrixadc_csvserver.cs_vserver_secondary,
    citrixadc_cspolicy.web_policy_secondary,
    citrixadc_lbvserver.web_lb_vserver_secondary
  ]
}
