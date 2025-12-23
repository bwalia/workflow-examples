# NetScaler API endpoint - use the domain that works
ns_endpoint = "https://netscaler.fictionally.org"

# Virtual IP address for the load balancer (using NetScaler container static IP)
ns_vip = "172.28.0.10"

# Backend IPs - using static container IPs in bridge network
app1_ip = "172.28.0.11"
app2_ip = "172.28.0.12"
app3_ip = "172.28.0.13"

# Backend ports - using container internal ports
app1_port = 80
app2_port = 80
app3_port = 80

# NetScaler credentials (auto-generated on first start)
ns_password = ""
