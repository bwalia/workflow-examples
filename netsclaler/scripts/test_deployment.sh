#!/bin/bash
# NetScaler CPX Deployment Test Suite
# Validates: containers, management API, LB, content switching, round-robin, HA headers
# Usage: ./test_deployment.sh [host]
# Exit code 0 = all tests pass, non-zero = number of failures

set -euo pipefail

HOST="${1:-localhost}"
PASSED=0
FAILED=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() {
    echo -e "  ${GREEN}PASS${NC} $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "  ${RED}FAIL${NC} $1"
    FAILED=$((FAILED + 1))
}

assert_http() {
    local name="$1" url="$2" expected="$3" curl_opts="${4:-}"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 15 $curl_opts "$url" 2>/dev/null || echo "000")
    if [ "$code" == "$expected" ]; then
        pass "$name (HTTP $code)"
    else
        fail "$name — expected HTTP $expected, got HTTP $code"
    fi
}

assert_container_healthy() {
    local name="$1"
    local status
    status=$(docker ps --format '{{.Status}}' --filter "name=^${name}$" 2>/dev/null || echo "not found")
    if echo "$status" | grep -q "(healthy)"; then
        pass "container $name is healthy"
    else
        fail "container $name — status: $status"
    fi
}

assert_container_running() {
    local name="$1"
    if docker ps --format '{{.Names}}' | grep -q "^${name}$" 2>/dev/null; then
        pass "container $name is running"
    else
        fail "container $name is not running"
    fi
}

# Verify multiple requests all return 200
assert_lb_consistent() {
    local name="$1" url="$2" num="${3:-5}"
    local success=0
    for i in $(seq 1 "$num"); do
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")
        [ "$code" == "200" ] && success=$((success + 1))
    done
    if [ "$success" -eq "$num" ]; then
        pass "$name — $success/$num requests succeeded"
    else
        fail "$name — only $success/$num requests succeeded"
    fi
}

# Verify round-robin via response header (X-App-Instance, X-Api-Instance, etc.)
assert_roundrobin() {
    local name="$1" url="$2" header="$3" expected_min="${4:-2}"
    local values=""
    for i in $(seq 1 12); do
        local val
        val=$(curl -s -D - -o /dev/null --connect-timeout 5 --max-time 10 "$url" 2>/dev/null | grep -i "^${header}:" | awk '{print $2}' | tr -d '\r' || echo "")
        if [ -n "$val" ] && ! echo "$values" | grep -qF "$val"; then
            values="${values}${val}\n"
        fi
    done
    local count
    count=$(echo -e "$values" | grep -c . || echo "0")
    if [ "$count" -ge "$expected_min" ]; then
        pass "$name — saw $count distinct backends via $header"
    else
        fail "$name — saw only $count backend(s), expected >= $expected_min via $header"
    fi
}

# Verify content switching routes to correct backend type via header
assert_content_switch() {
    local name="$1" url="$2" expected_header="$3"
    local found="false"
    for i in $(seq 1 3); do
        local headers
        headers=$(curl -s -D - -o /dev/null --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "")
        if echo "$headers" | grep -qi "^${expected_header}:"; then
            found="true"
            break
        fi
    done
    if [ "$found" == "true" ]; then
        pass "$name — routed to correct backend (has $expected_header header)"
    else
        fail "$name — expected $expected_header header not found"
    fi
}

echo "============================================"
echo "  NetScaler CPX Deployment Test Suite"
echo "============================================"
echo ""

# --- 1. Container Health ---
echo "1. Container Health"
assert_container_healthy "netscaler-cpx"
assert_container_healthy "netscaler-cpx-secondary"
assert_container_healthy "haproxy"
for c in nginx-app1 nginx-app2 nginx-app3 api-app1 api-app2 api-app3 web-app1 web-app2 web-app3; do
    assert_container_running "$c"
done
echo ""

# --- 2. NetScaler Management API ---
echo "2. NetScaler Management API (HTTPS)"
assert_http "Primary NITRO API (8443)" "https://${HOST}:8443/nitro/v1/config/nsversion" "401" "-k"
assert_http "Secondary NITRO API (8544)" "https://${HOST}:8544/nitro/v1/config/nsversion" "401" "-k"
echo ""

# --- 3. NetScaler Internal Health ---
echo "3. NetScaler Internal Services"
PRIMARY_HTTP=$(docker exec netscaler-cpx curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/ 2>/dev/null || echo "000")
[ "$PRIMARY_HTTP" == "200" ] && pass "Primary CPX internal HTTP — HTTP $PRIMARY_HTTP" || fail "Primary CPX internal HTTP — HTTP $PRIMARY_HTTP"
SECONDARY_HTTP=$(docker exec netscaler-cpx-secondary curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/ 2>/dev/null || echo "000")
[ "$SECONDARY_HTTP" == "200" ] && pass "Secondary CPX internal HTTP — HTTP $SECONDARY_HTTP" || fail "Secondary CPX internal HTTP — HTTP $SECONDARY_HTTP"
echo ""

# --- 4. HAProxy LB Endpoints ---
echo "4. HAProxy Load Balancer Endpoints"
assert_http "Nginx App LB (9090)" "http://${HOST}:9090/" "200"
assert_http "API Service LB (9091)" "http://${HOST}:9091/" "200"
assert_http "Web App LB (9092)" "http://${HOST}:9092/" "200"
assert_http "Content Switch VIP (9080)" "http://${HOST}:9080/" "200"
assert_http "HAProxy Stats (8404)" "http://${HOST}:8404/stats" "401"
echo ""

# --- 5. LB Consistency ---
echo "5. Load Balancer Consistency (5 sequential requests)"
assert_lb_consistent "Nginx App LB" "http://${HOST}:9090/" 5
assert_lb_consistent "API Service LB" "http://${HOST}:9091/" 5
assert_lb_consistent "Web App LB" "http://${HOST}:9092/" 5
assert_lb_consistent "Content Switch VIP" "http://${HOST}:9080/" 5
echo ""

# --- 6. Round-Robin Distribution ---
echo "6. Round-Robin Distribution (via response headers)"
assert_roundrobin "Nginx App" "http://${HOST}:9090/" "X-App-Instance" 2
assert_roundrobin "API Service" "http://${HOST}:9091/" "X-Api-Instance" 2
assert_roundrobin "Web App" "http://${HOST}:9092/" "X-Web-Instance" 2
echo ""

# --- 7. Content Switching ---
echo "7. Content Switching (single VIP on port 9080, URL-based routing)"
assert_http "CS default (/) -> Nginx" "http://${HOST}:9080/" "200"
assert_http "CS /api/ -> API Service" "http://${HOST}:9080/api/" "200"
assert_http "CS /web/ -> Web App" "http://${HOST}:9080/web/" "200"
assert_content_switch "CS / routes to Nginx" "http://${HOST}:9080/" "X-App-Instance"
assert_content_switch "CS /api/ routes to API" "http://${HOST}:9080/api/" "X-Api-Instance"
assert_content_switch "CS /web/ routes to Web" "http://${HOST}:9080/web/" "X-Web-Instance"
echo ""

# --- 8. HA Headers ---
echo "8. HA Response Headers"
HA_HEADERS=$(curl -s -D - -o /dev/null --connect-timeout 5 "http://${HOST}:9090/" 2>/dev/null || echo "")
echo "$HA_HEADERS" | grep -qi "X-Served-By:" && pass "X-Served-By header present" || fail "X-Served-By header missing"
echo "$HA_HEADERS" | grep -qi "X-HA-Status:" && pass "X-HA-Status header present" || fail "X-HA-Status header missing"
CS_HEADERS=$(curl -s -D - -o /dev/null --connect-timeout 5 "http://${HOST}:9080/" 2>/dev/null || echo "")
echo "$CS_HEADERS" | grep -qi "X-Routing:.*content-switching" && pass "X-Routing: content-switching header on CS VIP" || fail "X-Routing header missing on CS VIP"
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
