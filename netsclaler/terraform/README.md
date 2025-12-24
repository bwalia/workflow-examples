# NetScaler Load Balancer - Terraform Configuration

This directory contains Terraform configuration for managing NetScaler CPX load balancer services.

## Current Services

| Service | Port | Service Group | LB VServer | Backends |
|---------|------|---------------|------------|----------|
| Nginx App | 9090 | sg_nginx_apps | lbv_nginx_http | nginx-app1, nginx-app2, nginx-app3 |
| API Service | 9091 | sg_api_apps | lbv_api_http | api-app1, api-app2, api-app3 |
| Web App | 9092 | sg_web_apps | lbv_web_http | web-app1, web-app2, web-app3 |

## How to Add a New Application

Follow these steps to add a new load-balanced application with multiple instances:

### Step 1: Create Application Directories

Create directories for each instance of your new app in the `netsclaler/` directory:

```bash
mkdir -p netsclaler/myapp-1 netsclaler/myapp-2 netsclaler/myapp-3
```

### Step 2: Create nginx.conf for Each Instance

Create `nginx.conf` in each directory. Example for `myapp-1/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    add_header X-Backend-Server "myapp-1" always;
    add_header X-Backend-Status "ok" always;
    add_header X-MyApp-Instance "1" always;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
}
```

### Step 3: Create index.html for Each Instance

Create a unique `index.html` for each instance to identify which backend is serving requests.

### Step 4: Update docker-compose.yml

Add your new services to `netsclaler/docker-compose.yml`:

1. **Add port mapping to netscaler-cpx** (use next available port, e.g., 9093):
```yaml
netscaler-cpx:
  ports:
    - "9093:9093"     # Custom HTTP port for myapp load balancer
```

2. **Add container definitions** (use next available IP range, e.g., 172.28.0.41-43):
```yaml
  # ============================================
  # My App Service - 3 instances load balanced
  # ============================================
  myapp-1:
    image: nginx:alpine
    container_name: myapp-1
    hostname: myapp-1
    ports:
      - "8097:80"
    volumes:
      - ./myapp-1/index.html:/usr/share/nginx/html/index.html:ro
      - ./myapp-1/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
    networks:
      netscaler-network:
        ipv4_address: 172.28.0.41
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

  myapp-2:
    image: nginx:alpine
    container_name: myapp-2
    hostname: myapp-2
    ports:
      - "8098:80"
    volumes:
      - ./myapp-2/index.html:/usr/share/nginx/html/index.html:ro
      - ./myapp-2/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
    networks:
      netscaler-network:
        ipv4_address: 172.28.0.42
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

  myapp-3:
    image: nginx:alpine
    container_name: myapp-3
    hostname: myapp-3
    ports:
      - "8099:80"
    volumes:
      - ./myapp-3/index.html:/usr/share/nginx/html/index.html:ro
      - ./myapp-3/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
    networks:
      netscaler-network:
        ipv4_address: 172.28.0.43
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Step 5: Update Terraform Variables

Add variables to `variables.tf`:

```hcl
# My App Service Backend IPs
variable "myapp_app1_ip" {
  description = "IP address for myapp-1 container"
  type        = string
}

variable "myapp_app2_ip" {
  description = "IP address for myapp-2 container"
  type        = string
}

variable "myapp_app3_ip" {
  description = "IP address for myapp-3 container"
  type        = string
}

variable "myapp_app1_port" {
  description = "Port for myapp-1"
  type        = number
  default     = 80
}

variable "myapp_app2_port" {
  description = "Port for myapp-2"
  type        = number
  default     = 80
}

variable "myapp_app3_port" {
  description = "Port for myapp-3"
  type        = number
  default     = 80
}
```

### Step 6: Update terraform.tfvars

Add values to `terraform.tfvars`:

```hcl
# My App Service Backend IPs - using static container IPs in bridge network
myapp_app1_ip = "172.28.0.41"
myapp_app2_ip = "172.28.0.42"
myapp_app3_ip = "172.28.0.43"

# My App Service Backend ports
myapp_app1_port = 80
myapp_app2_port = 80
myapp_app3_port = 80
```

### Step 7: Add Terraform Resources to main.tf

Add the following resources to `main.tf`. **IMPORTANT:** Make sure to add proper `depends_on` to chain after the previous service to avoid race conditions:

```hcl
# ============================================
# My App Service Load Balancer Configuration
# ============================================

# Step 1: Create the service group
resource "citrixadc_servicegroup" "myapp_sg" {
  servicegroupname = "sg_myapp_apps"
  servicetype      = "HTTP"
  usip             = "NO"
}

# Step 2: Create the HTTP monitor for My App
resource "citrixadc_lbmonitor" "myapp_http_monitor" {
  monitorname = "mon_http_myapp"
  type        = "HTTP"
  interval    = 5
  retries     = 3
  httprequest = "GET /"
}

# Step 3: Bind monitor to service group
resource "citrixadc_servicegroup_lbmonitor_binding" "myapp_sg_monitor_bind" {
  servicegroupname = citrixadc_servicegroup.myapp_sg.servicegroupname
  monitorname      = citrixadc_lbmonitor.myapp_http_monitor.monitorname

  depends_on = [
    citrixadc_servicegroup.myapp_sg,
    citrixadc_lbmonitor.myapp_http_monitor
  ]
}

# Step 4: Add members to service group
resource "citrixadc_servicegroup_servicegroupmember_binding" "myapp_app1" {
  servicegroupname = citrixadc_servicegroup.myapp_sg.servicegroupname
  ip               = var.myapp_app1_ip
  port             = var.myapp_app1_port

  depends_on = [citrixadc_servicegroup.myapp_sg]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "myapp_app2" {
  servicegroupname = citrixadc_servicegroup.myapp_sg.servicegroupname
  ip               = var.myapp_app2_ip
  port             = var.myapp_app2_port

  depends_on = [citrixadc_servicegroup.myapp_sg]
}

resource "citrixadc_servicegroup_servicegroupmember_binding" "myapp_app3" {
  servicegroupname = citrixadc_servicegroup.myapp_sg.servicegroupname
  ip               = var.myapp_app3_ip
  port             = var.myapp_app3_port

  depends_on = [citrixadc_servicegroup.myapp_sg]
}

# Step 5: Small delay to ensure servicegroup is fully configured
resource "time_sleep" "myapp_sg_ready" {
  create_duration = "5s"

  depends_on = [
    citrixadc_servicegroup_servicegroupmember_binding.myapp_app1,
    citrixadc_servicegroup_servicegroupmember_binding.myapp_app2,
    citrixadc_servicegroup_servicegroupmember_binding.myapp_app3,
    citrixadc_servicegroup_lbmonitor_binding.myapp_sg_monitor_bind
  ]
}

# Step 6: Create the LB vserver (wait for previous LB to complete first)
resource "citrixadc_lbvserver" "myapp_lb_vserver" {
  name        = "lbv_myapp_http"
  servicetype = "HTTP"
  ipv46       = var.ns_vip
  port        = 9093  # Use next available port
  lbmethod    = "ROUNDROBIN"
  state       = "ENABLED"

  depends_on = [
    time_sleep.myapp_sg_ready,
    citrixadc_lbvserver_servicegroup_binding.web_lb_to_sg  # Wait for previous LB to complete
  ]
}

# Step 7: Bind service group to LB vserver
resource "citrixadc_lbvserver_servicegroup_binding" "myapp_lb_to_sg" {
  name             = citrixadc_lbvserver.myapp_lb_vserver.name
  servicegroupname = citrixadc_servicegroup.myapp_sg.servicegroupname

  depends_on = [
    citrixadc_lbvserver.myapp_lb_vserver,
    time_sleep.myapp_sg_ready
  ]
}
```

### Step 8: Update deploy.sh

Update `netsclaler/scripts/deploy.sh` to include your new containers:

1. Update `get_container_status()` regex:
```bash
docker_cmd ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(netscaler|nginx|api-app|web-app|myapp)" || true
```

2. Add to `get_container_ips()`:
```bash
# My apps
for container in myapp-1 myapp-2 myapp-3; do
    IP=$(docker_cmd inspect "$container" 2>/dev/null | jq -r ".[0].NetworkSettings.Networks[\"$network\"].IPAddress" 2>/dev/null || echo "N/A")
    echo "  $container: $IP"
done
```

3. Update `verify_backends()` container list:
```bash
local containers="nginx-app1 nginx-app2 nginx-app3 api-app1 api-app2 api-app3 web-app1 web-app2 web-app3 myapp-1 myapp-2 myapp-3"
```

### Step 9: Update GitHub Workflow

Update `.github/workflows/netscaler-lb-terraform.yaml`:

1. Add VIP status check in "Verify deployment" step
2. Add backend status check
3. Add load balancer test
4. Update final status check
5. Update deployment summary
6. Update Slack notification

## IP Address Allocation

Current IP allocation in the 172.28.0.0/16 network:

| IP Range | Purpose |
|----------|---------|
| 172.28.0.1 | Gateway |
| 172.28.0.10 | NetScaler CPX |
| 172.28.0.11-13 | nginx-app1, nginx-app2, nginx-app3 |
| 172.28.0.20 | nginx-backend |
| 172.28.0.21-23 | api-app1, api-app2, api-app3 |
| 172.28.0.30 | netscaler-exporter |
| 172.28.0.31-33 | web-app1, web-app2, web-app3 |
| 172.28.0.41+ | Available for new apps |

## Port Allocation

| Port | Service |
|------|---------|
| 9090 | Nginx App LB |
| 9091 | API Service LB |
| 9092 | Web App LB |
| 9093+ | Available for new services |

## Terraform Resource Dependency Chain

The resources are created in a specific order to avoid race conditions:

```
nginx_sg → (members + monitor) → time_sleep → nginx_lb_vserver → nginx_binding
                                                      ↓
api_sg → (members + monitor) → time_sleep → api_lb_vserver → api_binding
                                                      ↓
web_sg → (members + monitor) → time_sleep → web_lb_vserver → web_binding
                                                      ↓
                                              (next service)
```

## Troubleshooting

### "Root object was present, but now absent" Error

This error occurs when there's a race condition. Ensure:
1. All resources have proper `depends_on` blocks
2. `time_sleep` resources are used between servicegroup configuration and lbvserver creation
3. Each new lbvserver depends on the previous service's binding completion

### Containers Not Healthy

Check if:
1. Docker containers are running: `./deploy.sh status`
2. Container IPs are correct: `./deploy.sh ips`
3. HTTP health checks pass: `./deploy.sh verify`

### VIP Status DOWN

This usually means backends are not reachable. Verify:
1. Container network connectivity
2. Port 80 is exposed on containers
3. nginx.conf is properly mounted
