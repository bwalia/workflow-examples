# Nexus Repository Manager - K3s Deployment

## Overview

Sonatype Nexus deployed via Helm to K3s with wslproxy ingress, cert-manager TLS, and Vault credential management.

- **UI**: `https://dev-nexus.workstation.co.uk`
- **Docker Registry**: `https://dev-registry.workstation.co.uk`
- **Credentials**: `admin` / stored in Vault at `secret/nexus/admin`

## Docker Registry Push/Pull Test

### Prerequisites

On each K3s node that will push/pull images:

1. Add internal LB IP to `/etc/hosts` (bypasses external reverse proxy body size limit):
   ```
   192.168.1.211 dev-registry.workstation.co.uk dev-nexus.workstation.co.uk
   ```

2. Configure Docker to allow insecure registry (wslproxy uses default self-signed cert internally):
   ```json
   # /etc/docker/daemon.json
   {"insecure-registries": ["dev-registry.workstation.co.uk"]}
   ```
   Then restart Docker: `sudo systemctl restart docker`

### Login

```bash
docker login dev-registry.workstation.co.uk -u admin -p admin123
```

### Build and Push

```bash
# Build a test image from the netscaler nginx config
mkdir -p /tmp/test-netscaler-image
cat > /tmp/test-netscaler-image/Dockerfile <<'EOF'
FROM nginx:alpine
LABEL maintainer="bwalia" description="NetScaler nginx test app"
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN echo '<html><body><h1>NetScaler Nginx App - Registry Test</h1></body></html>' > /usr/share/nginx/html/index.html
EXPOSE 80
EOF

cat > /tmp/test-netscaler-image/nginx.conf <<'EOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
    add_header X-Backend-Server "netscaler-nginx-test" always;
    add_header X-Backend-Status "ok" always;
}
EOF

# Build and tag
docker build -t dev-registry.workstation.co.uk/netscaler/nginx-app:latest /tmp/test-netscaler-image/

# Push
docker push dev-registry.workstation.co.uk/netscaler/nginx-app:latest
```

### Pull and Verify

```bash
# Remove local image
docker rmi dev-registry.workstation.co.uk/netscaler/nginx-app:latest

# Pull from registry
docker pull dev-registry.workstation.co.uk/netscaler/nginx-app:latest

# Run and verify
docker run --rm -d --name test-netscaler-pull -p 18080:80 \
  dev-registry.workstation.co.uk/netscaler/nginx-app:latest

curl -s http://localhost:18080
# Expected: <html><body><h1>NetScaler Nginx App - Registry Test</h1></body></html>

curl -sI http://localhost:18080 | grep X-Backend
# Expected: X-Backend-Server: netscaler-nginx-test

docker stop test-netscaler-pull
```

### Verify via Nexus API

```bash
# List images in registry
curl -s -u admin:admin123 \
  https://dev-registry.workstation.co.uk/v2/_catalog

# List tags for an image
curl -s -u admin:admin123 \
  https://dev-registry.workstation.co.uk/v2/netscaler/nginx-app/tags/list
```

## Troubleshooting

### 413 Request Entity Too Large

The wslproxy openresty configmap must have `client_max_body_size` set large enough for Docker layer uploads. Check:

```bash
kubectl exec -n wslproxy-system <openresty-pod> -- \
  openresty -T 2>&1 | grep client_max_body_size
```

Should show `client_max_body_size 10g;` at both `http` and HTTPS `server` block levels.

If pushing from a node that resolves the registry to the WAN IP (external reverse proxy), ensure `/etc/hosts` points to the internal LB IP instead.

### Nexus Docker Hosted Repository

The `docker-hosted` repository on port 5000 must exist in Nexus. Create via API if missing:

```bash
kubectl exec -n nexus deploy/nexus-nexus-repository-manager -- \
  curl -s -X POST -u admin:admin123 \
  -H 'Content-Type: application/json' \
  http://localhost:8081/service/rest/v1/repositories/docker/hosted \
  -d '{
    "name": "docker-hosted",
    "online": true,
    "storage": {
      "blobStoreName": "default",
      "strictContentTypeValidation": true,
      "writePolicy": "ALLOW"
    },
    "docker": {
      "v1Enabled": false,
      "forceBasicAuth": true,
      "httpPort": 5000
    }
  }'
```

## Deployment

Triggered via GitHub Actions workflow `.github/workflows/deploy-nexus.yml`:

```bash
# Manual deploy
gh workflow run deploy-nexus.yml -f environment=dev -f action=deploy

# Destroy
gh workflow run deploy-nexus.yml -f environment=dev -f action=destroy
```
