#!/bin/bash
# NetScaler CPX Deployment Test Suite
# Validates that the full stack (CPX, HAProxy, backends, Terraform LB config) is working.
# Usage: ./test_deployment.sh [host]
#   host: target host (default: localhost)
# Exit code 0 = all tests pass, 1 = one or more failures

set -euo pipefail

HOST="${1:-localhost}"
PASSED=0
FAILED=0
TESTS=()

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

assert_http() {
    local name="$1"
    local url="$2"
    local expected_code="$3"
    local curl_opts="${4:-}"

    local actual_code
    actual_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 15 $curl_opts "$url" 2>/dev/null || echo "000")

    if [ "$actual_code" == "$expected_code" ]; then
        echo -e "  ${GREEN}PASS${NC} $name (HTTP $actual_code)"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}FAIL${NC} $name — expected HTTP $expected_code, got HTTP $actual_code"
        FAILED=$((FAILED + 1))
    fi
}

assert_container_healthy() {
    local name="$1"
    local status
    status=$(docker ps --format '{{.Status}}' --filter "name=^${name}$" 2>/dev/null || echo "not found")

    if echo "$status" | grep -q "(healthy)"; then
        echo -e "  ${GREEN}PASS${NC} container $name is healthy"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}FAIL${NC} container $name — status: $status"
        FAILED=$((FAILED + 1))
    fi
}

assert_container_running() {
    local name="$1"
    if docker ps --format '{{.Names}}' | grep -q "^${name}$" 2>/dev/null; then
        echo -e "  ${GREEN}PASS${NC} container $name is running"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}FAIL${NC} container $name is not running"
        FAILED=$((FAILED + 1))
    fi
}

assert_lb_roundrobin() {
    local name="$1"
    local url="$2"
    local expected_backends="$3"

    local backends_seen=""
    for i in $(seq 1 10); do
        local title
        title=$(curl -s --connect-timeout 5 --max-time 10 "$url" 2>/dev/null | grep -o "<title>[^<]*</title>" | sed 's/<[^>]*>//g' || echo "")
        if [ -n "$title" ] && ! echo "$backends_seen" | grep -qF "$title"; then
            backends_seen="${backends_seen}${title}\n"
        fi
    done

    local count
    count=$(echo -e "$backends_seen" | grep -c . || echo "0")

    if [ "$count" -ge 2 ]; then
        echo -e "  ${GREEN}PASS${NC} $name — saw $count different backends (round-robin working)"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}FAIL${NC} $name — saw only $count backend(s), expected round-robin across $expected_backends"
        FAILED=$((FAILED + 1))
    fi
}

echo "============================================"
echo "  NetScaler CPX Deployment Test Suite"
echo "============================================"
echo ""

# --- Container health ---
echo "1. Container Health"
assert_container_healthy "netscaler-cpx"
assert_container_healthy "netscaler-cpx-secondary"
assert_container_healthy "haproxy"
for c in nginx-app1 nginx-app2 nginx-app3 api-app1 api-app2 api-app3 web-app1 web-app2 web-app3; do
    assert_container_running "$c"
done
echo ""

# --- NetScaler Management API (HTTPS) ---
echo "2. NetScaler Management API (HTTPS)"
assert_http "Primary NITRO API (8443)" "https://${HOST}:8443/nitro/v1/config/nsversion" "401" "-k"
assert_http "Secondary NITRO API (8544)" "https://${HOST}:8544/nitro/v1/config/nsversion" "401" "-k"
echo ""

# --- HAProxy Load Balancer Endpoints ---
echo "3. HAProxy Load Balancer Endpoints"
assert_http "Nginx App LB (9090)" "http://${HOST}:9090/" "200"
assert_http "API Service LB (9091)" "http://${HOST}:9091/" "200"
assert_http "Web App LB (9092)" "http://${HOST}:9092/" "200"
assert_http "HAProxy Stats (8404)" "http://${HOST}:8404/stats" "401"
echo ""

# --- Load Balancer Round-Robin ---
echo "4. Load Balancer Round-Robin Distribution"
assert_lb_roundrobin "Nginx App round-robin" "http://${HOST}:9090/" "3"
assert_lb_roundrobin "API Service round-robin" "http://${HOST}:9091/" "3"
assert_lb_roundrobin "Web App round-robin" "http://${HOST}:9092/" "3"
echo ""

# --- NetScaler Internal Health (via docker exec) ---
echo "5. NetScaler Internal Services"
PRIMARY_HTTP=$(docker exec netscaler-cpx curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/ 2>/dev/null || echo "000")
if [ "$PRIMARY_HTTP" == "200" ]; then
    echo -e "  ${GREEN}PASS${NC} Primary CPX internal HTTP (port 80) — HTTP $PRIMARY_HTTP"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${RED}FAIL${NC} Primary CPX internal HTTP (port 80) — HTTP $PRIMARY_HTTP"
    FAILED=$((FAILED + 1))
fi

SECONDARY_HTTP=$(docker exec netscaler-cpx-secondary curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/ 2>/dev/null || echo "000")
if [ "$SECONDARY_HTTP" == "200" ]; then
    echo -e "  ${GREEN}PASS${NC} Secondary CPX internal HTTP (port 80) — HTTP $SECONDARY_HTTP"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${RED}FAIL${NC} Secondary CPX internal HTTP (port 80) — HTTP $SECONDARY_HTTP"
    FAILED=$((FAILED + 1))
fi
echo ""

# --- Summary ---
TOTAL=$((PASSED + FAILED))
echo "============================================"
if [ "$FAILED" -eq 0 ]; then
    echo -e "  ${GREEN}ALL $TOTAL TESTS PASSED${NC}"
else
    echo -e "  ${RED}$FAILED/$TOTAL TESTS FAILED${NC}"
fi
echo "============================================"

exit "$FAILED"
