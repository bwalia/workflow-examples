# NetScaler API endpoint - use the domain that works
ns_endpoint = "https://netscaler.fictionally.org"

# Virtual IP address for the load balancer (using NetScaler container static IP)
ns_vip = "172.28.0.10"

# Nginx App Backend IPs - using static container IPs in bridge network
app1_ip = "172.28.0.11"
app2_ip = "172.28.0.12"
app3_ip = "172.28.0.13"

# Nginx App Backend ports - using container internal ports
app1_port = 80
app2_port = 80
app3_port = 80

# API Service Backend IPs - using static container IPs in bridge network
api_app1_ip = "172.28.0.21"
api_app2_ip = "172.28.0.22"
api_app3_ip = "172.28.0.23"

# API Service Backend ports
api_app1_port = 80
api_app2_port = 80
api_app3_port = 80

# Web App Service Backend IPs - using static container IPs in bridge network
web_app1_ip = "172.28.0.31"
web_app2_ip = "172.28.0.32"
web_app3_ip = "172.28.0.33"

# Web App Service Backend ports
web_app1_port = 80
web_app2_port = 80
web_app3_port = 80

# NetScaler credentials (auto-generated on first start)
ns_password = ""
