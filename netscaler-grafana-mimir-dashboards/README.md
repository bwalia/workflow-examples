# NetScaler Grafana Mimir POC

A comprehensive Proof of Concept for monitoring **Citrix ADC (NetScaler)** appliances using **Grafana**, **Prometheus**, and **Grafana Mimir** for long-term metrics storage.

Includes a full metrics simulator that produces 265+ `citrixadc_*` Prometheus metrics matching the official Citrix ADC exporter format, along with 10 specialized Grafana dashboards.

## Architecture

```
┌─────────────────────┐     scrape      ┌──────────────┐   remote_write   ┌───────────────────┐
│  NetScaler Metrics  │ ◄────────────── │  Prometheus  │ ────────────────► │   Grafana Mimir   │
│  Simulator (:8000)  │    /metrics     │              │                   │  (3-node cluster) │
└─────────────────────┘                 └──────────────┘                   │  via Nginx LB     │
                                                                          │  (:9009)           │
                                                                          └────────┬──────────┘
                                                                                   │
                                                                          ┌────────▼──────────┐
                                                                          │     Grafana        │
                                                                          │    (:3001)         │
                                                                          │  10 Dashboards     │
                                                                          └───────────────────┘

Storage: MinIO (S3-compatible object store for Mimir blocks)
Rendering: Grafana Image Renderer (for PNG export)
```

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `netscaler-simulator` | Custom (Flask) | 8000 | Prometheus metrics endpoint with 265+ `citrixadc_*` metrics |
| `prometheus` | prom/prometheus | - | Scrapes simulator, remote-writes to Mimir |
| `mimir-1/2/3` | grafana/mimir | - | 3-node Mimir cluster for long-term storage |
| `load-balancer` | nginx | 9009 | Nginx load balancer in front of Mimir |
| `minio` | minio/minio | - | S3-compatible storage backend for Mimir |
| `grafana` | grafana/grafana | 3001 | Visualization with 10 pre-provisioned dashboards |
| `renderer` | grafana/grafana-image-renderer | 8081 | Server-side PNG rendering of dashboards |

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Run

```bash
docker-compose up -d --build
```

Wait ~30 seconds for metrics to populate through the pipeline, then open Grafana:

```
http://localhost:3001
```

No login required (anonymous admin access enabled).

### Verify the Pipeline

```bash
# Simulator is producing metrics (expect 265+ metric names)
curl -s http://localhost:8000/metrics | grep "^citrixadc_" | cut -d'{' -f1 | cut -d' ' -f1 | sort -u | wc -l

# Mimir has received the metrics
curl -s -H "X-Scope-OrgID: demo" \
  "http://localhost:9009/prometheus/api/v1/label/__name__/values" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(len([m for m in d['data'] if m.startswith('citrixadc_')]),'citrixadc metrics in Mimir')"
```

### Export Dashboard Screenshots

With the image renderer running, export all dashboards as PNG:

```bash
mkdir -p downloads
for uid in ns-system-overview ns-load-balancing ns-content-switching \
           ns-http-protocol ns-tcp-network ns-ssl-tls ns-services \
           ns-interfaces ns-aaa-security ns-golden-signals; do
  curl -s -o "downloads/${uid}.png" \
    "http://localhost:3001/render/d/${uid}?orgId=1&width=1920&height=1080&timeout=60"
  echo "Exported ${uid}.png"
done
```

### Stop

```bash
docker-compose down
```

Add `-v` to also remove persistent volumes (Mimir data, MinIO storage):

```bash
docker-compose down -v
```

## Dashboards

10 specialized Grafana dashboards are auto-provisioned:

| # | Dashboard | UID | Key Panels |
|---|-----------|-----|------------|
| 1 | **System Overview** | `ns-system-overview` | CPU/memory/disk gauges, per-core CPU, RX/TX throughput, bandwidth utilization |
| 2 | **Load Balancing** | `ns-load-balancing` | Request/response rates per vserver, TTLB, APDEX, surge queue, spillovers, busy errors, connections |
| 3 | **Content Switching** | `ns-content-switching` | CS vserver hits, request/response rates, TTLB, APDEX, spillovers, connections |
| 4 | **HTTP Protocol** | `ns-http-protocol` | Total requests/responses, GET vs POST, HTTP 1.0/1.1, chunked encoding, RX/TX bytes, errors |
| 5 | **TCP & Network** | `ns-tcp-network` | Active connections, SYN/FIN packets, packet rates, byte rates, TCP errors, IP metrics |
| 6 | **SSL/TLS** | `ns-ssl-tls` | Session rate, crypto utilization, handshakes, encrypt/decrypt rates, cert expiry, per-vserver SSL |
| 7 | **Services** | `ns-services` | Service state (UP/DOWN), TTFB, throughput, connections, service group member metrics |
| 8 | **Network Interfaces** | `ns-interfaces` | Per-interface RX/TX bytes and packets, CRC errors, dropped packets, jumbo/trunk frames |
| 9 | **AAA & Security** | `ns-aaa-security` | Auth success/failure, session types (ICA, TM), WAF violations, SQLi/XSS/CSRF blocks |
| 10 | **Golden Signals** | `ns-golden-signals` | Latency (TTLB), Traffic (request rate), Errors (5xx, WAF), Saturation (CPU, memory, surge) |

## Metrics Simulator

The simulator (`app.py`) generates Prometheus metrics matching the official **Citrix ADC exporter** format with the `citrixadc_` prefix. Metrics are updated every 5 seconds with realistic values.

### Metric Categories

| Category | Metrics | Examples |
|----------|---------|---------|
| System | 15 | CPU usage, memory, disk partitions, per-core CPU |
| Bandwidth | 4 | Max/min/actual/licensed bandwidth |
| LB VServer | 27 | Requests, responses, TTLB, APDEX, surge, spillovers, connections |
| CS VServer | 17 | Hits, requests, responses, TTLB, connections |
| Services | 19 | Throughput, TTFB, connections, pool usage, load |
| Service Groups | 8 | Per-member requests, responses, TTFB, connections |
| SSL Global | 12 | Sessions, handshakes, crypto utilization, encode/decode rates |
| SSL VServer | 14 | Per-vserver encrypt/decrypt, auth success/failure |
| SSL CertKey | 1 | Days to certificate expiration |
| HTTP Protocol | 27 | GET/POST, HTTP 1.0/1.1, chunked, bytes, errors |
| TCP Protocol | 25 | Packets, bytes, connections, SYN/FIN, errors |
| IP Protocol | 21 | Packets, bytes, fragments, checksums, TTL |
| Interfaces | 21 | Per-interface RX/TX bytes/packets, CRC errors, drops |
| AAA | 14 | Auth success/fail, sessions (ICA, TM, HTTP) |
| GSLB | 5 | Site state, RTT, vserver hits/requests |
| HA | 3 | Sync success/failure, heartbeat failures |
| DNS | 5 | Queries, answers, NXDOMAIN, per-record queries |
| Cache | 5 | Hits, misses, hit ratio, bytes served |
| Compression | 3 | Requests, ratio, bandwidth savings |
| AppFirewall | 7 | Violations, blocks, SQLi/XSS/CSRF, per-profile |

### Endpoints

| Path | Description |
|------|-------------|
| `/metrics` | Prometheus scrape endpoint |
| `/health` | Health check |
| `/api/v1/query` | Prometheus-compatible instant query API |
| `/api/v1/query_range` | Prometheus-compatible range query API |
| `/api/v1/labels` | Label names |
| `/api/v1/label/<name>/values` | Label values |

### Mock Data

The simulator creates realistic mock infrastructure:

- **5 LB Virtual Servers**: HTTP, SSL, TCP (web, API, database)
- **2 CS Virtual Servers**: HTTP and SSL content switching
- **6 Services**: Web (x3), API (x2), Database
- **3 Service Groups**: Web pool, API pool, DB pool with individual members
- **3 SSL Virtual Servers** with encrypt/decrypt tracking
- **4 SSL Certificates** with varying expiry (12-365 days)
- **3 Network Interfaces**: 2x 10G data + 1x 1G management
- **2 GSLB Sites**: East and West datacenter
- **2 HA Nodes**: Primary and Secondary
- **2 AppFirewall Profiles**: Web protection and API security
- **8 CPU Cores** with independent utilization

## Project Structure

```
.
├── app.py                          # Metrics simulator (Flask)
├── Dockerfile                      # Simulator container build
├── docker-compose.yml              # Full stack orchestration
├── requirements.txt                # Python dependencies
├── config/
│   ├── prometheus.yaml             # Prometheus scrape config
│   ├── grafana-provisioning-datasources.yaml
│   ├── grafana-provisioning-dashboards.yaml
│   ├── mimir.yaml                  # Mimir cluster config
│   ├── nginx.conf                  # Mimir load balancer
│   └── alertmanager-fallback-config.yaml
├── dashboards/                     # 10 NetScaler Grafana dashboards
│   ├── 01-system-overview.json
│   ├── 02-load-balancing.json
│   ├── 03-content-switching.json
│   ├── 04-http-protocol.json
│   ├── 05-tcp-network.json
│   ├── 06-ssl-tls.json
│   ├── 07-services.json
│   ├── 08-network-interfaces.json
│   ├── 09-aaa-security.json
│   └── 10-golden-signals.json
├── mimir-mixin-dashboards/         # Mimir operational dashboards
│   └── *.json
└── downloads/                      # Exported dashboard PNGs
```

## Configuration

### Prometheus

Scrapes the simulator every 10 seconds and remote-writes to Mimir:

```yaml
scrape_configs:
  - job_name: demo/netscaler
    static_configs:
      - targets: ["netscaler-simulator:8000"]
        labels:
          instance: "netscaler-vpx-01"
    scrape_interval: 10s
```

### Grafana Datasource

Dashboards query Mimir (not the simulator directly), ensuring the full pipeline is exercised:

```yaml
datasources:
  - name: Mimir
    type: prometheus
    uid: mimir-datasource
    url: http://load-balancer:9009/prometheus
```

### Mimir

3-node cluster with MinIO backend, configured for the `demo` tenant.
