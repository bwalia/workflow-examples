#!/bin/bash
set -e

# NetScaler Deployment Script
# This script handles Docker operations with proper permissions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run docker commands with sudo if needed
docker_cmd() {
    if [ -w /var/run/docker.sock ]; then
        docker "$@"
    else
        sudo docker "$@"
    fi
}

docker_compose_cmd() {
    if [ -w /var/run/docker.sock ]; then
        docker-compose -f "$COMPOSE_FILE" "$@"
    else
        sudo docker-compose -f "$COMPOSE_FILE" "$@"
    fi
}

# Stop existing containers
stop_containers() {
    log_info "Stopping existing containers..."
    docker_compose_cmd down --remove-orphans || true
    log_info "Containers stopped"
}

# Start containers
start_containers() {
    log_info "Starting Docker Compose services..."
    docker_compose_cmd up -d

    log_info "Waiting for containers to initialize..."
    sleep 20

    # Show container status
    log_info "Current container status:"
    docker_cmd ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(netscaler|nginx|api-app|web-app|haproxy)" || true

    log_info "Containers started"
}

# Wait for NetScaler to be ready
wait_for_netscaler() {
    local endpoint="$1"
    local container_name="${2:-netscaler-cpx}"
    local max_attempts="${3:-30}"
    local attempt=1

    log_info "Waiting for NetScaler CPX ($container_name) to start..."

    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt of $max_attempts..."

        # Check if container is running
        if ! docker_cmd ps | grep -q "$container_name"; then
            log_warn "NetScaler container ($container_name) not running, waiting..."
            sleep 10
            attempt=$((attempt + 1))
            continue
        fi

        # Check if API is responding
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -k "$endpoint/nitro/v1/config/nsversion" 2>/dev/null || echo "000")

        if [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "200" ]; then
            log_info "NetScaler API ($container_name) is responding (HTTP $HTTP_CODE)"
            return 0
        fi

        log_warn "NetScaler ($container_name) not ready yet (HTTP $HTTP_CODE), waiting..."
        sleep 10
        attempt=$((attempt + 1))
    done

    log_error "NetScaler ($container_name) failed to start within timeout"
    docker_cmd logs "$container_name" --tail 50
    return 1
}

# Wait for both NetScalers to be ready (HA setup)
wait_for_netscalers() {
    local primary_endpoint="$1"
    local secondary_endpoint="$2"
    local max_attempts="${3:-30}"

    log_info "Waiting for both NetScaler instances to be ready..."

    wait_for_netscaler "$primary_endpoint" "netscaler-cpx" "$max_attempts"
    local primary_result=$?

    wait_for_netscaler "$secondary_endpoint" "netscaler-cpx-secondary" "$max_attempts"
    local secondary_result=$?

    if [ $primary_result -eq 0 ] && [ $secondary_result -eq 0 ]; then
        log_info "Both NetScaler instances are ready!"
        return 0
    else
        log_error "One or both NetScaler instances failed to start"
        return 1
    fi
}

# Get NetScaler password (primary)
get_password() {
    docker_cmd exec netscaler-cpx cat /var/deviceinfo/random_id
}

# Get NetScaler secondary password
get_secondary_password() {
    docker_cmd exec netscaler-cpx-secondary cat /var/deviceinfo/random_id
}

# Get both NetScaler passwords (HA setup)
get_passwords() {
    log_info "NetScaler Primary Password:"
    get_password
    echo ""
    log_info "NetScaler Secondary Password:"
    get_secondary_password
}

# Get container status
get_container_status() {
    log_info "Container Status:"
    docker_cmd ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(netscaler|nginx|api-app|web-app|haproxy)" || true
}

# Get container IPs
get_container_ips() {
    local network="netsclaler_netscaler-network"
    log_info "Container IPs:"
    # HAProxy and NetScaler instances
    for container in haproxy netscaler-cpx netscaler-cpx-secondary; do
        IP=$(docker_cmd inspect "$container" 2>/dev/null | jq -r ".[0].NetworkSettings.Networks[\"$network\"].IPAddress" 2>/dev/null || echo "N/A")
        echo "  $container: $IP"
    done
    # Nginx apps
    for container in nginx-backend nginx-app1 nginx-app2 nginx-app3; do
        IP=$(docker_cmd inspect "$container" 2>/dev/null | jq -r ".[0].NetworkSettings.Networks[\"$network\"].IPAddress" 2>/dev/null || echo "N/A")
        echo "  $container: $IP"
    done
    # API apps
    for container in api-app1 api-app2 api-app3; do
        IP=$(docker_cmd inspect "$container" 2>/dev/null | jq -r ".[0].NetworkSettings.Networks[\"$network\"].IPAddress" 2>/dev/null || echo "N/A")
        echo "  $container: $IP"
    done
    # Web apps
    for container in web-app1 web-app2 web-app3; do
        IP=$(docker_cmd inspect "$container" 2>/dev/null | jq -r ".[0].NetworkSettings.Networks[\"$network\"].IPAddress" 2>/dev/null || echo "N/A")
        echo "  $container: $IP"
    done
}

# Verify all backend containers are healthy
verify_backends() {
    local max_attempts="${1:-30}"
    local attempt=1
    local all_healthy=false

    log_info "Verifying all backend containers are healthy..."

    # List of required containers
    local containers="nginx-app1 nginx-app2 nginx-app3 api-app1 api-app2 api-app3 web-app1 web-app2 web-app3"

    while [ $attempt -le $max_attempts ]; do
        all_healthy=true
        echo "Attempt $attempt of $max_attempts..."

        for container in $containers; do
            # Check if container is running
            if ! docker_cmd ps --format "{{.Names}}" | grep -q "^${container}$"; then
                log_warn "Container $container is not running"
                all_healthy=false
                continue
            fi

            # Check container health by making HTTP request
            local ip=$(docker_cmd inspect "$container" 2>/dev/null | jq -r '.[0].NetworkSettings.Networks["netsclaler_netscaler-network"].IPAddress' 2>/dev/null)
            if [ -z "$ip" ] || [ "$ip" == "null" ]; then
                log_warn "Cannot get IP for $container"
                all_healthy=false
                continue
            fi

            # Test HTTP connectivity
            local http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://$ip/" 2>/dev/null || echo "000")
            if [ "$http_code" == "200" ]; then
                echo "  $container ($ip): OK"
            else
                log_warn "  $container ($ip): HTTP $http_code"
                all_healthy=false
            fi
        done

        if [ "$all_healthy" = true ]; then
            log_info "All backend containers are healthy!"
            return 0
        fi

        log_warn "Not all containers are healthy yet, waiting 10 seconds..."
        sleep 10
        attempt=$((attempt + 1))
    done

    log_error "Not all containers became healthy within timeout"
    get_container_status
    return 1
}

# Show container logs
show_logs() {
    local container="$1"
    local lines="${2:-50}"
    docker_cmd logs "$container" --tail "$lines"
}

# Destroy infrastructure
destroy() {
    log_info "Destroying infrastructure..."
    stop_containers
    log_info "Infrastructure destroyed"
}

# Check HAProxy status
check_haproxy() {
    log_info "Checking HAProxy status..."
    local stats_url="http://localhost:8404/stats"

    if curl -s -o /dev/null -w "%{http_code}" "$stats_url" 2>/dev/null | grep -q "200\|401"; then
        log_info "HAProxy is running. Stats available at: $stats_url"
        log_info "Credentials: admin/admin"
    else
        log_warn "HAProxy stats page not accessible"
    fi
}

# Main command handler
case "${1:-help}" in
    stop)
        stop_containers
        ;;
    start)
        start_containers
        ;;
    restart)
        stop_containers
        start_containers
        ;;
    wait)
        wait_for_netscaler "$2" "${3:-netscaler-cpx}" "${4:-30}"
        ;;
    wait-ha)
        wait_for_netscalers "$2" "$3" "${4:-30}"
        ;;
    verify)
        verify_backends "${2:-30}"
        ;;
    password)
        get_password
        ;;
    password-secondary)
        get_secondary_password
        ;;
    passwords)
        get_passwords
        ;;
    status)
        get_container_status
        ;;
    ips)
        get_container_ips
        ;;
    logs)
        show_logs "${2:-netscaler-cpx}" "${3:-50}"
        ;;
    haproxy)
        check_haproxy
        ;;
    destroy)
        destroy
        ;;
    help|*)
        echo "NetScaler Deployment Script (with HA Support)"
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  stop                        Stop all containers"
        echo "  start                       Start all containers"
        echo "  restart                     Restart all containers"
        echo "  wait <endpoint> [container] Wait for NetScaler to be ready"
        echo "  wait-ha <primary> <secondary> Wait for both NetScalers (HA)"
        echo "  verify [attempts]           Verify all backend containers are healthy"
        echo "  password                    Get NetScaler primary password"
        echo "  password-secondary          Get NetScaler secondary password"
        echo "  passwords                   Get both NetScaler passwords"
        echo "  status                      Show container status"
        echo "  ips                         Show container IPs"
        echo "  logs [container]            Show container logs"
        echo "  haproxy                     Check HAProxy status"
        echo "  destroy                     Destroy infrastructure"
        echo "  help                        Show this help"
        ;;
esac
