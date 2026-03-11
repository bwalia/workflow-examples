# ============================================
# Content Switching Configuration (Primary)
# Single VIP on port 9080 that routes:
#   /api/*  -> API Service LB (lbv_api_http)
#   /web/*  -> Web App LB (lbv_web_http)
#   default -> Nginx App LB (lbv_nginx_http)
# ============================================

# Content Switching VServer - single entry point
resource "citrixadc_csvserver" "cs_vserver" {
  provider    = citrixadc.primary
  name        = "csv_main"
  servicetype = "HTTP"
  ipv46       = var.ns_vip
  port        = 9080
  state       = "ENABLED"

  depends_on = [
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

# CS Action: target API LB vserver
resource "citrixadc_csaction" "api_action" {
  provider        = citrixadc.primary
  name            = "csa_api"
  targetlbvserver = citrixadc_lbvserver.api_lb_vserver.name

  depends_on = [citrixadc_lbvserver.api_lb_vserver]
}

# CS Action: target Web App LB vserver
resource "citrixadc_csaction" "web_action" {
  provider        = citrixadc.primary
  name            = "csa_web"
  targetlbvserver = citrixadc_lbvserver.web_lb_vserver.name

  depends_on = [citrixadc_lbvserver.web_lb_vserver]
}

# Bind API policy to CS vserver
resource "citrixadc_csvserver_cspolicy_binding" "api_binding" {
  provider       = citrixadc.primary
  name           = citrixadc_csvserver.cs_vserver.name
  policyname     = citrixadc_cspolicy.api_policy.policyname
  priority       = 100
  targetlbvserver = citrixadc_lbvserver.api_lb_vserver.name

  depends_on = [
    citrixadc_csvserver.cs_vserver,
    citrixadc_cspolicy.api_policy,
    citrixadc_csaction.api_action
  ]
}

# Bind Web policy to CS vserver
resource "citrixadc_csvserver_cspolicy_binding" "web_binding" {
  provider       = citrixadc.primary
  name           = citrixadc_csvserver.cs_vserver.name
  policyname     = citrixadc_cspolicy.web_policy.policyname
  priority       = 200
  targetlbvserver = citrixadc_lbvserver.web_lb_vserver.name

  depends_on = [
    citrixadc_csvserver.cs_vserver,
    citrixadc_cspolicy.web_policy,
    citrixadc_csaction.web_action
  ]
}

# CS Policy: catch-all default route -> Nginx App LB vserver
resource "citrixadc_cspolicy" "default_policy" {
  provider   = citrixadc.primary
  policyname = "csp_default"
  rule       = "true"

  depends_on = [citrixadc_csvserver.cs_vserver]
}

resource "citrixadc_csaction" "default_action" {
  provider        = citrixadc.primary
  name            = "csa_default"
  targetlbvserver = citrixadc_lbvserver.nginx_lb_vserver.name

  depends_on = [citrixadc_lbvserver.nginx_lb_vserver]
}

resource "citrixadc_csvserver_cspolicy_binding" "default_binding" {
  provider        = citrixadc.primary
  name            = citrixadc_csvserver.cs_vserver.name
  policyname      = citrixadc_cspolicy.default_policy.policyname
  priority        = 300
  targetlbvserver = citrixadc_lbvserver.nginx_lb_vserver.name

  depends_on = [
    citrixadc_csvserver.cs_vserver,
    citrixadc_cspolicy.default_policy,
    citrixadc_csaction.default_action
  ]
}

# ============================================
# Content Switching Configuration (Secondary)
# ============================================

resource "citrixadc_csvserver" "cs_vserver_secondary" {
  provider    = citrixadc.secondary
  name        = "csv_main"
  servicetype = "HTTP"
  ipv46       = var.ns_secondary_vip
  port        = 9080
  state       = "ENABLED"

  depends_on = [
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

resource "citrixadc_csaction" "api_action_secondary" {
  provider        = citrixadc.secondary
  name            = "csa_api"
  targetlbvserver = citrixadc_lbvserver.api_lb_vserver_secondary.name

  depends_on = [citrixadc_lbvserver.api_lb_vserver_secondary]
}

resource "citrixadc_csaction" "web_action_secondary" {
  provider        = citrixadc.secondary
  name            = "csa_web"
  targetlbvserver = citrixadc_lbvserver.web_lb_vserver_secondary.name

  depends_on = [citrixadc_lbvserver.web_lb_vserver_secondary]
}

resource "citrixadc_csvserver_cspolicy_binding" "api_binding_secondary" {
  provider       = citrixadc.secondary
  name           = citrixadc_csvserver.cs_vserver_secondary.name
  policyname     = citrixadc_cspolicy.api_policy_secondary.policyname
  priority       = 100
  targetlbvserver = citrixadc_lbvserver.api_lb_vserver_secondary.name

  depends_on = [
    citrixadc_csvserver.cs_vserver_secondary,
    citrixadc_cspolicy.api_policy_secondary,
    citrixadc_csaction.api_action_secondary
  ]
}

resource "citrixadc_csvserver_cspolicy_binding" "web_binding_secondary" {
  provider       = citrixadc.secondary
  name           = citrixadc_csvserver.cs_vserver_secondary.name
  policyname     = citrixadc_cspolicy.web_policy_secondary.policyname
  priority       = 200
  targetlbvserver = citrixadc_lbvserver.web_lb_vserver_secondary.name

  depends_on = [
    citrixadc_csvserver.cs_vserver_secondary,
    citrixadc_cspolicy.web_policy_secondary,
    citrixadc_csaction.web_action_secondary
  ]
}

resource "citrixadc_cspolicy" "default_policy_secondary" {
  provider   = citrixadc.secondary
  policyname = "csp_default"
  rule       = "true"

  depends_on = [citrixadc_csvserver.cs_vserver_secondary]
}

resource "citrixadc_csaction" "default_action_secondary" {
  provider        = citrixadc.secondary
  name            = "csa_default"
  targetlbvserver = citrixadc_lbvserver.nginx_lb_vserver_secondary.name

  depends_on = [citrixadc_lbvserver.nginx_lb_vserver_secondary]
}

resource "citrixadc_csvserver_cspolicy_binding" "default_binding_secondary" {
  provider        = citrixadc.secondary
  name            = citrixadc_csvserver.cs_vserver_secondary.name
  policyname      = citrixadc_cspolicy.default_policy_secondary.policyname
  priority        = 300
  targetlbvserver = citrixadc_lbvserver.nginx_lb_vserver_secondary.name

  depends_on = [
    citrixadc_csvserver.cs_vserver_secondary,
    citrixadc_cspolicy.default_policy_secondary,
    citrixadc_csaction.default_action_secondary
  ]
}
