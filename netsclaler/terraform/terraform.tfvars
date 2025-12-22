# NetScaler API endpoint - use the domain that works
ns_endpoint = "https://netscaler.fictionally.org"

# Virtual IP address for the load balancer (using NetScaler container IP in bridge mode)
ns_vip = "172.18.0.2"

# Backend IPs - using container IPs in bridge network
app1_ip = "172.18.0.6"
app2_ip = "172.18.0.7"
app3_ip = "172.18.0.5"

# Backend ports - using container internal ports
app1_port = 80
app2_port = 80
app3_port = 80

# NetScaler credentials (auto-generated on first start)
ns_password = "e8d55ea8a55945ac8c1e0c30c509efc8"
