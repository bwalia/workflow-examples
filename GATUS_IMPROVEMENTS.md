# Gatus Helm Chart - Resilience Improvements

## Overview
Enhanced the Gatus Helm chart with production-grade resilience, observability, and security features.

## Key Improvements

### 1. **High Availability & Auto-Scaling**
- **Replica Count**: Increased from 1 to 2 minimum instances
- **Horizontal Pod Autoscaler (HPA)**: Added with configurable scaling
  - Min replicas: 2
  - Max replicas: 5
  - CPU target: 70% utilization
  - Memory target: 80% utilization
  - Smart scale-up/down policies with stabilization windows
- **Pod Anti-Affinity**: Pods spread across different nodes for fault tolerance
- **Rolling Update Strategy**: Zero-downtime deployments with maxSurge=1, maxUnavailable=0

### 2. **Enhanced Health Checks**
- **Startup Probe**: Added with 30 failure threshold (5 minutes) to allow full initialization
  - Prevents premature pod termination during startup
  - Solves the "context deadline exceeded" issue
- **Liveness Probe**: Monitors pod health with 3 failure threshold
  - Restarts unhealthy pods automatically
- **Readiness Probe**: Controls traffic routing with 3 failure threshold
- **Pre-Stop Hook**: 5-second grace period for graceful shutdown

### 3. **Resource Management**
- **CPU Limits**: 500m (up from 200m) for better performance
- **CPU Requests**: 100m (up from 50m) for reliable scheduling
- **Memory Limits**: 512Mi (up from 256Mi) for handling larger datasets
- **Memory Requests**: 128Mi (up from 64Mi) for consistent allocation
- **Graceful Termination**: 30-second grace period for clean shutdowns

### 4. **Data Persistence**
- **Storage Size**: Increased from 1Gi to 5Gi for long-term data retention
- **PVC Mount**: Proper configuration for SQLite persistence
- **Data Durability**: Survives pod restarts and cluster maintenance

### 5. **Pod Disruption Budget (PDB)**
- Ensures minimum 1 pod remains available during:
  - Cluster maintenance (node drains)
  - Voluntary pod evictions
  - Kubernetes upgrades
- Prevents accidental downtime during infrastructure changes

### 6. **Security Enhancements**
- **Network Policy**: 
  - Ingress from nginx-ingress namespace and same pod selector
  - Egress for DNS, HTTP/HTTPS, and in-cluster services
  - Restricts network access to only necessary connections
- **Read-Only Root Filesystem**: Prevents malicious modifications
- **Non-Root User**: Runs as user 65534 with minimal privileges
- **Security Context**: Drops all Linux capabilities

### 7. **Ingress Improvements**
- **Rate Limiting**: 100 requests per second
- **Timeout Configuration**: 300-second timeouts for long-running checks
- **SSL/TLS Redirect**: Enforces HTTPS connections
- **Better annotations**: Cleaner configuration for nginx

### 8. **Observability & Monitoring**
- **Prometheus Metrics**: Enabled metrics endpoint at `/metrics`
- **ServiceMonitor**: Auto-discovery by Prometheus Operator
  - Configurable scrape interval (30s default)
  - Scrape timeout (10s default)
- **JSON Logging**: Structured logs for better log aggregation
- **Logging Level**: Info-level logging for production

### 9. **Lifecycle Management**
- **Image Pull Policy**: IfNotPresent to reduce registry load
- **DNS Policy**: ClusterFirst for reliable service discovery
- **Restart Policy**: Always for automatic recovery
- **Config Checksum**: Auto-rollout on config changes

## New Templates Added
1. **hpa.yaml** - Horizontal Pod Autoscaler configuration
2. **pdb.yaml** - Pod Disruption Budget for cluster maintenance
3. **networkpolicy.yaml** - Network segmentation and security
4. **servicemonitor.yaml** - Prometheus monitoring integration

## Files Modified
1. **values.yaml**
   - Increased resources and storage
   - Added HPA configuration
   - Added PDB configuration
   - Added affinity rules
   - Added monitoring configuration
   - Updated ingress annotations

2. **templates/deployment.yaml**
   - Added startup probe (solves context deadline exceeded)
   - Improved liveness/readiness probes
   - Added graceful shutdown handling
   - Added rolling update strategy
   - Added lifecycle pre-stop hook

3. **templates/configmap.yaml**
   - Added logging configuration
   - Added metrics endpoint

## Deployment Command
```bash
helm upgrade --install gatus ./helm/gatus \
  --namespace monitoring \
  --values ./helm/gatus/values.yaml \
  --wait \
  --timeout 10m \
  --atomic
```

## Benefits
✅ **Resilience**: Auto-recovery, auto-scaling, and fault tolerance
✅ **Reliability**: Proper health checks prevent false failures
✅ **Availability**: Minimum replicas and PDB ensure continuous service
✅ **Security**: Network policies and restricted privileges
✅ **Observability**: Prometheus integration for monitoring
✅ **Performance**: Better resource allocation and scaling
✅ **Maintainability**: Cleaner configuration and modern Kubernetes patterns

## Testing Recommendations
1. Monitor pod startup times with: `kubectl logs -n monitoring gatus-0 -f`
2. Check HPA status: `kubectl get hpa -n monitoring`
3. Verify network policies: `kubectl get networkpolicies -n monitoring`
4. Test ingress: `curl -v https://test-status.workstation.co.uk`
5. Monitor metrics: Access `/metrics` endpoint on the service
