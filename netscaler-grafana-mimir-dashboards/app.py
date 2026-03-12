#!/usr/bin/env python3
"""
Comprehensive NetScaler/Citrix ADC Prometheus Metrics Simulator

A Flask application that simulates a complete Citrix ADC (NetScaler) Prometheus
exporter endpoint with realistic metrics for testing Grafana dashboards and
monitoring systems.

All metrics use the citrixadc_ prefix matching the official Citrix ADC exporter.
"""

import os
import random
import time
import threading
import json
import re
from typing import Dict, List, Tuple, Any
from flask import Flask, Response, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ============================================================================
# INSTANCE CONFIGURATION (set via environment variables for multi-instance)
# ============================================================================

INSTANCE_NAME = os.environ.get("INSTANCE_NAME", "nsr1.kisaan001.bru.fictionally.org")
INSTANCE_IP = os.environ.get("INSTANCE_IP", "10.78.1.1")
INSTANCE_REGION = os.environ.get("INSTANCE_REGION", "ams")
INSTANCE_ROLE = os.environ.get("INSTANCE_ROLE", "primary")  # primary or secondary

# ============================================================================
# CONFIGURATION AND DATA STRUCTURES
# ============================================================================

# LB Virtual Servers Configuration
LB_VSERVERS = [
    {"name": "lb_vsrv_web_prod",    "type": "HTTP", "port": "80",   "state": "UP", "domain": "www.ticketmaster.com"},
    {"name": "lb_vsrv_web_secure",  "type": "SSL",  "port": "443",  "state": "UP", "domain": "www.ticketmaster.com"},
    {"name": "lb_vsrv_api_gateway", "type": "HTTP", "port": "8080", "state": "UP", "domain": "api.ticketmaster.com"},
    {"name": "lb_vsrv_backend_app", "type": "SSL",  "port": "8443", "state": "UP", "domain": "checkout.ticketmaster.com"},
    {"name": "lb_vsrv_database",    "type": "TCP",  "port": "3306", "state": "UP", "domain": "db.internal.fictionally.org"},
]

# Domain lookup for metrics — keyed by vserver name for fast access
_LB_DOMAIN = {vs["name"]: vs.get("domain", "unknown") for vs in LB_VSERVERS}

# CS Virtual Servers Configuration
CS_VSERVERS = [
    {"name": "cs_vsrv_main_site", "type": "HTTP", "port": "80", "state": "UP"},
    {"name": "cs_vsrv_secure_portal", "type": "SSL", "port": "443", "state": "UP"},
]

# Services Configuration
SERVICES = [
    {"name": "svc_web_01", "type": "HTTP", "port": "8080", "state": "UP"},
    {"name": "svc_web_02", "type": "HTTP", "port": "8080", "state": "UP"},
    {"name": "svc_web_03", "type": "HTTP", "port": "8080", "state": "UP"},
    {"name": "svc_api_01", "type": "HTTP", "port": "8080", "state": "UP"},
    {"name": "svc_api_02", "type": "HTTP", "port": "8080", "state": "UP"},
    {"name": "svc_db_primary", "type": "TCP", "port": "5432", "state": "UP"},
]

# Service Groups Configuration
SERVICE_GROUPS = [
    {"name": "sg_web_pool", "type": "HTTP", "state": "UP", "members": [
        {"ip": "192.168.1.10", "server": "web01"},
        {"ip": "192.168.1.11", "server": "web02"},
        {"ip": "192.168.1.12", "server": "web03"},
    ]},
    {"name": "sg_api_pool", "type": "HTTP", "state": "UP", "members": [
        {"ip": "192.168.2.10", "server": "api01"},
        {"ip": "192.168.2.11", "server": "api02"},
    ]},
    {"name": "sg_db_pool", "type": "TCP", "state": "UP", "members": [
        {"ip": "192.168.3.10", "server": "db01"},
    ]},
]

# SSL Virtual Servers Configuration
SSL_VSERVERS = [
    {"name": "lb_vsrv_web_secure", "type": "SSL", "ip": "10.0.0.10", "state": "UP"},
    {"name": "lb_vsrv_backend_app", "type": "SSL", "ip": "10.0.0.20", "state": "UP"},
    {"name": "cs_vsrv_secure_portal", "type": "SSL", "ip": "10.0.0.30", "state": "UP"},
]

# SSL Certificates Configuration — per-instance, driven by INSTANCE_NAME env var
_CERT_CONFIGS = {
    "nsr1.kisaan001.bru.fictionally.org": [
        {"name": "wildcard_prod_ams", "days_to_expire": 89},
        {"name": "api_gateway_cert", "days_to_expire": 45},
        {"name": "backend_app_cert", "days_to_expire": 12},
        {"name": "monitoring_cert", "days_to_expire": 180},
    ],
    "nsr2.kisaan001.bru.fictionally.org": [
        {"name": "wildcard_prod_ams", "days_to_expire": 89},
        {"name": "api_gateway_cert", "days_to_expire": 45},
        {"name": "backend_app_cert", "days_to_expire": 12},
        {"name": "monitoring_cert", "days_to_expire": 180},
    ],
    "nsr1.kisaan001.lon.fictionally.org": [
        {"name": "wildcard_prod_ash", "days_to_expire": 120},
        {"name": "ticketmaster_ssl_cert", "days_to_expire": 7},
        {"name": "payment_gateway_cert", "days_to_expire": 60},
        {"name": "internal_services_cert", "days_to_expire": 300},
    ],
}
SSL_CERTS = _CERT_CONFIGS.get(INSTANCE_NAME, [
    {"name": "wildcard_prod_cert", "days_to_expire": 89},
    {"name": "api_gateway_cert", "days_to_expire": 45},
    {"name": "backend_app_cert", "days_to_expire": 12},
    {"name": "legacy_cert", "days_to_expire": 365},
])

# Network Interfaces Configuration
INTERFACES = [
    {"id": "0/1", "alias": "LA/1", "speed": "10G"},
    {"id": "0/2", "alias": "LA/2", "speed": "10G"},
    {"id": "1/1", "alias": "MGMT", "speed": "1G"},
]

# GSLB Configuration
GSLB_SITES = [
    {"name": "site_datacenter_east", "ip": "10.10.1.1"},
    {"name": "site_datacenter_west", "ip": "10.10.2.1"},
]

GSLB_VSERVERS = [
    {"name": "gslb_vsrv_www", "type": "HTTP", "state": "UP"},
    {"name": "gslb_vsrv_api", "type": "HTTP", "state": "UP"},
]

# HA Configuration
HA_NODES = [
    {"node": "primary", "ip": "10.0.0.1"},
    {"node": "secondary", "ip": "10.0.0.2"},
]

# AppFirewall Profiles Configuration
APPFW_PROFILES = [
    {"name": "appfw_web_protection", "state": "ENABLED"},
    {"name": "appfw_api_security", "state": "ENABLED"},
]

# DNS Records Configuration
DNS_RECORDS = [
    {"domain": "example.com", "type": "A"},
    {"domain": "api.example.com", "type": "A"},
]

# Cache Policies Configuration
CACHE_POLICIES = [
    {"name": "cache_static_content"},
    {"name": "cache_api_responses"},
]

# System Configuration
CPU_CORES = 8
MAX_BANDWIDTH_MBPS = 10000
MIN_BANDWIDTH_MBPS = 100

# ============================================================================
# GLOBAL METRICS STORAGE
# ============================================================================

metrics_data: Dict[str, Any] = {
    # System Metrics
    "cpu_usage": 45.0,
    "memory_usage": 60.0,
    "mgmt_cpu_usage": 10.0,
    "packet_cpu_usage": 50.0,
    "res_cpu_usage": 15.0,
    "cpu_core_usage": [50.0] * CPU_CORES,
    "var_partition_free_mb": 5000,
    "var_partition_used_mb": 5000,
    "flash_partition_free_mb": 30000,
    "flash_partition_used_mb": 20000,
    "throughput_rx_mbits": 1500.0,
    "throughput_tx_mbits": 1200.0,

    # Bandwidth Metrics
    "max_bandwidth": MAX_BANDWIDTH_MBPS,
    "min_bandwidth": MIN_BANDWIDTH_MBPS,
    "actual_bandwidth": 8000,
    "allocated_licensed_bandwidth": 10000,

    # LB VServer Metrics
    "lb_vserver": {},

    # CS VServer Metrics
    "cs_vserver": {},

    # Service Metrics
    "service": {},

    # Service Group Metrics
    "service_group": {},

    # SSL Global Metrics
    "ssl_tot_sessions": 0,
    "ssl_tot_tlsv11_sessions": 0,
    "ssl_tot_v2_sessions": 0,
    "ssl_tot_v2_handshakes": 0,
    "ssl_tot_encode": 0,
    "ssl_tot_new_sessions": 0,
    "ssl_crypto_utilization": 30.0,
    "ssl_session_rate": 0.0,
    "ssl_dec_rate": 0.0,
    "ssl_encode_rate": 0.0,

    # SSL VServer Metrics
    "ssl_vserver": {},

    # Protocol HTTP Metrics
    "http_tot_requests": 0,
    "http_tot_responses": 0,
    "http_tot_gets": 0,
    "http_tot_posts": 0,
    "http_tot_others": 0,
    "http_tot_rx_request_bytes": 0,
    "http_tot_rx_response_bytes": 0,
    "http_tot_tx_request_bytes": 0,
    "http_tot_10_requests": 0,
    "http_tot_11_requests": 0,
    "http_tot_10_responses": 0,
    "http_tot_11_responses": 0,
    "http_tot_chunked_requests": 0,
    "http_tot_chunked_responses": 0,
    "http_err_tot_incomplete_headers": 0,
    "http_err_tot_incomplete_requests": 0,
    "http_err_tot_incomplete_responses": 0,
    "http_err_tot_server_responses": 0,
    "http_err_tot_large_body": 0,
    "http_err_tot_large_chunk": 0,
    "http_err_tot_large_content": 0,

    # Protocol TCP Metrics
    "tcp_tot_rx_packets": 0,
    "tcp_tot_rx_bytes": 0,
    "tcp_tx_bytes": 0,
    "tcp_tot_tx_packets": 0,
    "tcp_tot_client_conn_opened": 0,
    "tcp_tot_server_conn_opened": 0,
    "tcp_tot_syn": 0,
    "tcp_tot_syn_probe": 0,
    "tcp_tot_server_fin": 0,
    "tcp_tot_client_fin": 0,
    "tcp_active_server_conn": 0,
    "tcp_current_client_conn_est": 0,
    "tcp_current_server_conn_est": 0,
    "tcp_err_badchecksum": 0,
    "tcp_err_any_port_fail": 0,
    "tcp_err_ip_port_fail": 0,
    "tcp_err_bad_conn_state": 0,
    "tcp_err_reset_threshold": 0,

    # Protocol IP Metrics
    "ip_tot_rx_packets": 0,
    "ip_tot_rx_bytes": 0,
    "ip_tx_packets": 0,
    "ip_tx_bytes": 0,
    "ip_rx_mbits": 0,
    "ip_tx_mbits": 0,
    "ip_tot_routed_packets": 0,
    "ip_tot_routed_mbits": 0,
    "ip_tot_fragments": 0,
    "ip_tot_successful_assembly": 0,
    "ip_tot_address_lookup": 0,
    "ip_tot_bad_checksums": 0,
    "ip_tot_ttl_expired": 0,
    "ip_tot_max_clients": 0,

    # Interface Metrics
    "interface": {},

    # AAA Metrics
    "aaa_auth_success": 0,
    "aaa_auth_fail": 0,
    "aaa_auth_only_http_success": 0,
    "aaa_auth_only_http_fail": 0,
    "aaa_auth_non_http_success": 0,
    "aaa_auth_non_http_fail": 0,
    "aaa_tot_sessions": 0,
    "aaa_tot_sessiontimeout": 0,
    "aaa_tot_tm_sessions": 0,
    "aaa_cur_ica_sessions": 0,
    "aaa_cur_ica_only_conn": 0,
    "aaa_cur_ica_conn": 0,
    "aaa_cur_tm_sessions": 0,
    "aaa_cur_sessions": 0,

    # GSLB Metrics
    "gslb_site": {},
    "gslb_vserver": {},

    # HA Metrics
    "ha_sync_success": 0,
    "ha_sync_failure": 0,
    "ha_heartbeat_failures": 0,

    # DNS Metrics
    "dns_tot_queries": 0,
    "dns_tot_answers": 0,
    "dns_tot_nxdomain": 0,
    "dns_record_queries": {},

    # Cache Metrics
    "cache_tot_requests": 0,
    "cache_tot_hits": 0,
    "cache_tot_misses": 0,
    "cache_bytes_served": 0,

    # Compression Metrics
    "compression_tot_requests": 0,
    "compression_ratio": 70.0,
    "compression_bandwidth_savings": 0,

    # AppFirewall Metrics
    "appfw_tot_violations": 0,
    "appfw_tot_log": 0,
    "appfw_tot_blocked": 0,
    "appfw_sql_injection_blocked": 0,
    "appfw_xss_blocked": 0,
    "appfw_csrf_blocked": 0,
    "appfw_profile": {},
}

# ============================================================================
# METRICS INITIALIZATION
# ============================================================================

def initialize_metrics() -> None:
    """Initialize all metric structures with default values."""

    # Initialize LB VServer Metrics
    for vs in LB_VSERVERS:
        name = vs["name"]
        metrics_data["lb_vserver"][name] = {
            "hits_total": 0,
            "requests_total": 0,
            "responses_total": 0,
            "request_bytes_total": 0,
            "response_bytes_received_total": 0,
            "packets_sent_total": 0,
            "packets_received_total": 0,
            "surge_count": 0,
            "spillover_count_total": 0,
            "deferred_requests_total": 0,
            "invalid_response_request_total": 0,
            "busy_error_total": 0,
            "frustrating_transactions_total": 0,
            "tolerable_transactions_total": 0,
            "ttlb_calculated_transactions_total": 0,
            "backup_server_divert_count_total": 0,
            "request_rate": 0.0,
            "request_rate_bytes": 0.0,
            "total_responses_rate": 0.0,
            "response_bytes_received_rate": 0.0,
            "hits_rate": 0.0,
            "average_ttlb": 150.0,
            "active_sessions_count": 0,
            "inactive_services_count": 0,
            "established_connections_count": 0,
            "current_client_connection_count": 0,
            "actual_server_current_connections": 0,
            "surge_queue_requests_count": 0,
            "spill_over_threshold": 100,
            "client_response_time_apdex": 0.95,
            "deferred_requests_rate": 0.0,
            "busy_error_rate": 0.0,
            "frustrating_transactions_rate": 0.0,
            "members_up_total": 3,
            "vserver_health": 100.0,
        }

    # Initialize CS VServer Metrics
    for vs in CS_VSERVERS:
        name = vs["name"]
        metrics_data["cs_vserver"][name] = {
            "hits_total": 0,
            "requests_total": 0,
            "responses_total": 0,
            "request_bytes_total": 0,
            "response_bytes_received_total": 0,
            "packets_sent_total": 0,
            "packets_received_total": 0,
            "spillover_count_total": 0,
            "deferred_requests_total": 0,
            "request_rate": 0.0,
            "total_responses_rate": 0.0,
            "hits_rate": 0.0,
            "average_ttlb": 100.0,
            "established_connections_count": 0,
            "current_client_connection_count": 0,
            "actual_server_current_connections": 0,
            "client_response_time_apdex": 0.97,
            "spill_over_threshold": 100,
        }

    # Initialize Service Metrics
    for svc in SERVICES:
        name = svc["name"]
        metrics_data["service"][name] = {
            "throughput": 0,
            "tot_requests": 0,
            "tot_responses": 0,
            "tot_request_bytes": 0,
            "tot_response_bytes": 0,
            "surge_count": 0,
            "server_established_connections": 0,
            "max_clients": 1000,
            "vsvr_hits": 0,
            "throughput_rate": 0.0,
            "average_server_ttfb": 50.0,
            "responses_rate": 0.0,
            "request_bytes_rate": 0.0,
            "response_bytes_rate": 0.0,
            "current_client_connections": 0,
            "current_server_connections": 0,
            "current_pool_use": 0,
            "current_load": 50,
            "active_transactions": 0,
        }

    # Initialize Service Group Metrics
    for sg in SERVICE_GROUPS:
        sg_name = sg["name"]
        for member in sg["members"]:
            key = f"{sg_name}_{member['ip']}"
            metrics_data["service_group"][key] = {
                "servicegroup_name": sg_name,
                "service_type": sg["type"],
                "state": sg["state"],
                "ip": member["ip"],
                "server_name": member["server"],
                "tot_responses": 0,
                "tot_requests": 0,
                "tot_response_bytes": 0,
                "tot_request_bytes": 0,
                "avg_server_ttfb": 30.0,
                "requests_rate": 0.0,
                "current_server_connections": 0,
                "responses_rate": 0.0,
            }

    # Initialize SSL VServer Metrics
    for ssl_vs in SSL_VSERVERS:
        name = ssl_vs["name"]
        metrics_data["ssl_vserver"][name] = {
            "decrypt_bytes_total": 0,
            "encrypt_bytes_total": 0,
            "session_new_total": 0,
            "session_hits_total": 0,
            "auth_success_total": 0,
            "auth_failure_total": 0,
            "health": 1.0,
            "active_services": 3,
            "encrypt_bytes_rate": 0.0,
            "decrypt_bytes_rate": 0.0,
            "session_new_rate": 0.0,
            "session_hits_rate": 0.0,
            "auth_success_rate": 0.0,
            "auth_failure_rate": 0.0,
        }

    # Initialize Interface Metrics
    for intf in INTERFACES:
        intf_id = intf["id"]
        metrics_data["interface"][intf_id] = {
            "alias": intf["alias"],
            "tot_rx_bytes": 0,
            "tot_tx_bytes": 0,
            "tot_rx_packets": 0,
            "tot_tx_packets": 0,
            "tot_packets": 0,
            "tot_multicast_packets": 0,
            "rx_crc_errors": 0,
            "tot_mac_moved": 0,
            "err_dropped_rx_packets": 0,
            "err_dropped_tx_packets": 0,
            "link_reinitializations": 0,
            "jumbo_packets_received": 0,
            "jumbo_packets_transmitted": 0,
            "trunk_packets_received": 0,
            "trunk_packets_transmitted": 0,
            "rx_bytes_rate": 0.0,
            "tx_bytes_rate": 0.0,
            "rx_packets_rate": 0.0,
            "tx_packets_rate": 0.0,
            "err_dropped_rx_packets_rate": 0.0,
            "err_dropped_tx_packets_rate": 0.0,
            "rx_crc_errors_rate": 0.0,
        }

    # Initialize GSLB Site Metrics
    for site in GSLB_SITES:
        metrics_data["gslb_site"][site["name"]] = {
            "ip": site["ip"],
            "state": 1.0,  # 1=ACTIVE
            "rtt_milliseconds": 10.0,
        }

    # Initialize GSLB VServer Metrics
    for gslb_vs in GSLB_VSERVERS:
        name = gslb_vs["name"]
        metrics_data["gslb_vserver"][name] = {
            "type": gslb_vs["type"],
            "state": gslb_vs["state"],
            "hits_total": 0,
            "requests_total": 0,
        }

    # Initialize DNS Record Metrics
    for record in DNS_RECORDS:
        key = f"{record['domain']}_{record['type']}"
        metrics_data["dns_record_queries"][key] = {
            "domain": record["domain"],
            "type": record["type"],
            "queries": 0,
        }

    # Initialize AppFirewall Profile Metrics
    for profile in APPFW_PROFILES:
        metrics_data["appfw_profile"][profile["name"]] = {
            "state": profile["state"],
            "violations_total": 0,
        }

# ============================================================================
# METRICS UPDATE LOGIC
# ============================================================================

def update_metrics() -> None:
    """Background thread that updates all metrics every 5 seconds with realistic simulation."""

    while True:
        try:
            # Update System Metrics
            base_cpu = 45.0
            metrics_data["cpu_usage"] = round(base_cpu + random.uniform(-15, 25), 2)
            metrics_data["memory_usage"] = round(random.uniform(55, 75), 2)
            metrics_data["mgmt_cpu_usage"] = round(random.uniform(5, 15), 2)
            metrics_data["packet_cpu_usage"] = round(random.uniform(30, 70), 2)
            metrics_data["res_cpu_usage"] = round(random.uniform(10, 25), 2)

            # Update per-core CPU usage independently
            for i in range(CPU_CORES):
                metrics_data["cpu_core_usage"][i] = round(random.uniform(20, 80), 2)

            # Update disk metrics
            var_used = random.randint(5000, 6500)
            var_total = 10000
            metrics_data["var_partition_used_mb"] = var_used
            metrics_data["var_partition_free_mb"] = var_total - var_used

            flash_used = random.randint(18000, 22000)
            flash_total = 50000
            metrics_data["flash_partition_used_mb"] = flash_used
            metrics_data["flash_partition_free_mb"] = flash_total - flash_used

            # Update throughput
            metrics_data["throughput_rx_mbits"] = round(random.uniform(500, 3000), 2)
            metrics_data["throughput_tx_mbits"] = round(random.uniform(400, 2500), 2)

            # Update bandwidth metrics
            metrics_data["actual_bandwidth"] = random.randint(7000, 9000)

            # Update LB VServer Metrics
            for vs_name, vs_metrics in metrics_data["lb_vserver"].items():
                # Increment counters
                request_increment = random.randint(100, 1000)
                vs_metrics["requests_total"] += request_increment
                vs_metrics["hits_total"] += int(request_increment * 0.95)

                # Responses ~95-100% of requests
                response_increment = int(request_increment * random.uniform(0.95, 1.0))
                vs_metrics["responses_total"] += response_increment

                # Bytes
                request_bytes = request_increment * random.randint(500, 2000)
                response_bytes = response_increment * random.randint(1000, 5000)
                vs_metrics["request_bytes_total"] += request_bytes
                vs_metrics["response_bytes_received_total"] += response_bytes

                # Packets
                vs_metrics["packets_sent_total"] += random.randint(500, 5000)
                vs_metrics["packets_received_total"] += random.randint(500, 5000)

                # Rates
                vs_metrics["request_rate"] = round(request_increment / 5.0, 2)
                vs_metrics["request_rate_bytes"] = round(request_bytes / 5.0, 2)
                vs_metrics["total_responses_rate"] = round(response_increment / 5.0, 2)
                vs_metrics["response_bytes_received_rate"] = round(response_bytes / 5.0, 2)
                vs_metrics["hits_rate"] = round(vs_metrics["request_rate"] * 0.95, 2)

                # TTLB (Time To Last Byte) - realistic web latency
                vs_metrics["average_ttlb"] = round(random.uniform(50, 300), 2)

                # Connections and sessions
                vs_metrics["active_sessions_count"] = random.randint(100, 1000)
                vs_metrics["established_connections_count"] = random.randint(50, 500)
                vs_metrics["current_client_connection_count"] = random.randint(50, 500)
                vs_metrics["actual_server_current_connections"] = random.randint(20, 200)

                # Surge queue (10% chance of spike)
                if random.random() < 0.1:
                    surge = random.randint(5, 50)
                    vs_metrics["surge_count"] = surge
                    vs_metrics["surge_queue_requests_count"] = surge
                else:
                    vs_metrics["surge_count"] = 0
                    vs_metrics["surge_queue_requests_count"] = 0

                # Busy errors (5% chance)
                if random.random() < 0.05:
                    busy_errors = random.randint(1, 10)
                    vs_metrics["busy_error_total"] += busy_errors
                    vs_metrics["busy_error_rate"] = round(busy_errors / 5.0, 2)
                else:
                    vs_metrics["busy_error_rate"] = 0.0

                # Spillovers (2% chance)
                if random.random() < 0.02:
                    spillover = random.randint(1, 5)
                    vs_metrics["spillover_count_total"] += spillover

                # Deferred requests
                deferred = random.randint(0, 10)
                vs_metrics["deferred_requests_total"] += deferred
                vs_metrics["deferred_requests_rate"] = round(deferred / 5.0, 2)

                # Transaction quality metrics for APDEX calculation
                satisfying = int(request_increment * random.uniform(0.80, 0.95))
                tolerating = int(request_increment * random.uniform(0.03, 0.15))
                frustrating = request_increment - satisfying - tolerating

                vs_metrics["tolerable_transactions_total"] += tolerating
                vs_metrics["frustrating_transactions_total"] += frustrating
                vs_metrics["frustrating_transactions_rate"] = round(frustrating / 5.0, 2)
                vs_metrics["ttlb_calculated_transactions_total"] += request_increment

                # APDEX score: (satisfying + 0.5*tolerating) / total
                total_trans = satisfying + tolerating + frustrating
                if total_trans > 0:
                    apdex = (satisfying + 0.5 * tolerating) / total_trans
                    vs_metrics["client_response_time_apdex"] = round(apdex, 3)

                # Service state changes (5% chance)
                if random.random() < 0.05:
                    vs_metrics["inactive_services_count"] = random.randint(0, 1)
                else:
                    vs_metrics["inactive_services_count"] = 0

                # Members up (typically all up)
                total_members = 3
                vs_metrics["members_up_total"] = total_members - vs_metrics["inactive_services_count"]
                vs_metrics["vserver_health"] = round(
                    (vs_metrics["members_up_total"] / total_members) * 100.0, 1
                )

            # ── Event spike simulation ──────────────────────────────────
            # Every ~120 cycles (~10 min at 5s interval) spike lb_vsrv_web_secure
            # to simulate a major event (e.g. Pitbull concert) going on sale.
            _spike_vs = "lb_vsrv_web_secure"
            if metrics_data["lb_vserver"].get(_spike_vs):
                _cycle = int(time.time() // 5) % 240
                if 0 <= _cycle < 24:          # spike lasts ~2 min out of every 20 min
                    _spike_mul = 80 + (_cycle * 4)
                    metrics_data["lb_vserver"][_spike_vs]["request_rate"] *= _spike_mul
                    metrics_data["lb_vserver"][_spike_vs]["request_rate_bytes"] *= _spike_mul
                    metrics_data["lb_vserver"][_spike_vs]["surge_count"] = random.randint(500, 2000)

            # Update CS VServer Metrics (similar to LB but simpler)
            for vs_name, vs_metrics in metrics_data["cs_vserver"].items():
                request_increment = random.randint(50, 500)
                vs_metrics["requests_total"] += request_increment
                vs_metrics["hits_total"] += int(request_increment * 0.98)

                response_increment = int(request_increment * random.uniform(0.97, 1.0))
                vs_metrics["responses_total"] += response_increment

                request_bytes = request_increment * random.randint(400, 1500)
                response_bytes = response_increment * random.randint(800, 4000)
                vs_metrics["request_bytes_total"] += request_bytes
                vs_metrics["response_bytes_received_total"] += response_bytes

                vs_metrics["packets_sent_total"] += random.randint(200, 3000)
                vs_metrics["packets_received_total"] += random.randint(200, 3000)

                vs_metrics["request_rate"] = round(request_increment / 5.0, 2)
                vs_metrics["total_responses_rate"] = round(response_increment / 5.0, 2)
                vs_metrics["hits_rate"] = round(vs_metrics["request_rate"] * 0.98, 2)
                vs_metrics["average_ttlb"] = round(random.uniform(40, 250), 2)

                vs_metrics["established_connections_count"] = random.randint(30, 300)
                vs_metrics["current_client_connection_count"] = random.randint(30, 300)
                vs_metrics["actual_server_current_connections"] = random.randint(10, 150)

                # High APDEX for CS (content switching is typically fast)
                vs_metrics["client_response_time_apdex"] = round(random.uniform(0.95, 0.99), 3)

                # Spillovers
                if random.random() < 0.01:
                    vs_metrics["spillover_count_total"] += random.randint(1, 3)

                deferred = random.randint(0, 5)
                vs_metrics["deferred_requests_total"] += deferred

            # Update Service Metrics
            for svc_name, svc_metrics in metrics_data["service"].items():
                # Find service config
                svc_config = next((s for s in SERVICES if s["name"] == svc_name), None)

                # 5% chance of toggling service state
                if random.random() < 0.05:
                    svc_config["state"] = "DOWN" if svc_config["state"] == "UP" else "UP"

                if svc_config["state"] == "UP":
                    request_increment = random.randint(50, 500)
                    svc_metrics["tot_requests"] += request_increment

                    response_increment = int(request_increment * random.uniform(0.95, 1.0))
                    svc_metrics["tot_responses"] += response_increment

                    req_bytes = request_increment * random.randint(300, 1200)
                    resp_bytes = response_increment * random.randint(600, 3000)
                    svc_metrics["tot_request_bytes"] += req_bytes
                    svc_metrics["tot_response_bytes"] += resp_bytes

                    throughput_inc = req_bytes + resp_bytes
                    svc_metrics["throughput"] += throughput_inc
                    svc_metrics["throughput_rate"] = round(throughput_inc / 5.0, 2)

                    # TTFB (Time To First Byte) - server response time
                    svc_metrics["average_server_ttfb"] = round(random.uniform(10, 100), 2)

                    svc_metrics["responses_rate"] = round(response_increment / 5.0, 2)
                    svc_metrics["request_bytes_rate"] = round(req_bytes / 5.0, 2)
                    svc_metrics["response_bytes_rate"] = round(resp_bytes / 5.0, 2)

                    svc_metrics["current_client_connections"] = random.randint(10, 100)
                    svc_metrics["current_server_connections"] = random.randint(10, 100)
                    svc_metrics["server_established_connections"] = random.randint(50, 500)

                    svc_metrics["current_pool_use"] = random.randint(0, 80)
                    svc_metrics["current_load"] = random.randint(20, 80)
                    svc_metrics["active_transactions"] = random.randint(5, 50)
                    svc_metrics["vsvr_hits"] += int(request_increment * 0.9)
                else:
                    # Service is down
                    svc_metrics["throughput_rate"] = 0.0
                    svc_metrics["responses_rate"] = 0.0
                    svc_metrics["request_bytes_rate"] = 0.0
                    svc_metrics["response_bytes_rate"] = 0.0
                    svc_metrics["current_client_connections"] = 0
                    svc_metrics["current_server_connections"] = 0
                    svc_metrics["current_pool_use"] = 0
                    svc_metrics["active_transactions"] = 0

            # Update Service Group Metrics
            for key, sg_metrics in metrics_data["service_group"].items():
                # Check if parent service group state is UP
                sg_state = sg_metrics["state"]

                if sg_state == "UP":
                    request_increment = random.randint(30, 300)
                    sg_metrics["tot_requests"] += request_increment

                    response_increment = int(request_increment * random.uniform(0.96, 1.0))
                    sg_metrics["tot_responses"] += response_increment

                    req_bytes = request_increment * random.randint(300, 1000)
                    resp_bytes = response_increment * random.randint(500, 2500)
                    sg_metrics["tot_request_bytes"] += req_bytes
                    sg_metrics["tot_response_bytes"] += resp_bytes

                    sg_metrics["avg_server_ttfb"] = round(random.uniform(10, 80), 2)
                    sg_metrics["requests_rate"] = round(request_increment / 5.0, 2)
                    sg_metrics["responses_rate"] = round(response_increment / 5.0, 2)
                    sg_metrics["current_server_connections"] = random.randint(5, 50)
                else:
                    sg_metrics["requests_rate"] = 0.0
                    sg_metrics["responses_rate"] = 0.0
                    sg_metrics["current_server_connections"] = 0

            # Update SSL Global Metrics
            ssl_session_inc = random.randint(50, 200)
            metrics_data["ssl_tot_sessions"] += ssl_session_inc
            metrics_data["ssl_tot_tlsv11_sessions"] += int(ssl_session_inc * 0.3)
            metrics_data["ssl_tot_v2_sessions"] += int(ssl_session_inc * 0.05)
            metrics_data["ssl_tot_v2_handshakes"] += random.randint(5, 20)

            encode_inc = random.randint(100, 500)
            metrics_data["ssl_tot_encode"] += encode_inc

            new_session_inc = random.randint(10, 50)
            metrics_data["ssl_tot_new_sessions"] += new_session_inc

            metrics_data["ssl_crypto_utilization"] = round(random.uniform(20, 60), 2)
            metrics_data["ssl_session_rate"] = round(ssl_session_inc / 5.0, 2)
            metrics_data["ssl_dec_rate"] = round(random.uniform(1000, 5000), 2)
            metrics_data["ssl_encode_rate"] = round(encode_inc / 5.0, 2)

            # Update SSL VServer Metrics
            for ssl_vs_name, ssl_vs_metrics in metrics_data["ssl_vserver"].items():
                decrypt_bytes_inc = random.randint(50000, 500000)
                encrypt_bytes_inc = random.randint(100000, 800000)

                ssl_vs_metrics["decrypt_bytes_total"] += decrypt_bytes_inc
                ssl_vs_metrics["encrypt_bytes_total"] += encrypt_bytes_inc

                session_new_inc = random.randint(5, 30)
                session_hits_inc = random.randint(20, 100)

                ssl_vs_metrics["session_new_total"] += session_new_inc
                ssl_vs_metrics["session_hits_total"] += session_hits_inc

                auth_success_inc = random.randint(10, 50)
                auth_failure_inc = random.randint(0, 2)

                ssl_vs_metrics["auth_success_total"] += auth_success_inc
                ssl_vs_metrics["auth_failure_total"] += auth_failure_inc

                ssl_vs_metrics["health"] = 1.0 if random.random() > 0.02 else 0.0
                ssl_vs_metrics["active_services"] = random.randint(2, 3)

                ssl_vs_metrics["encrypt_bytes_rate"] = round(encrypt_bytes_inc / 5.0, 2)
                ssl_vs_metrics["decrypt_bytes_rate"] = round(decrypt_bytes_inc / 5.0, 2)
                ssl_vs_metrics["session_new_rate"] = round(session_new_inc / 5.0, 2)
                ssl_vs_metrics["session_hits_rate"] = round(session_hits_inc / 5.0, 2)
                ssl_vs_metrics["auth_success_rate"] = round(auth_success_inc / 5.0, 2)
                ssl_vs_metrics["auth_failure_rate"] = round(auth_failure_inc / 5.0, 2)

            # Update HTTP Protocol Metrics
            http_req_inc = random.randint(500, 3000)
            metrics_data["http_tot_requests"] += http_req_inc

            http_resp_inc = int(http_req_inc * random.uniform(0.95, 1.0))
            metrics_data["http_tot_responses"] += http_resp_inc

            # HTTP methods
            gets = int(http_req_inc * 0.7)
            posts = int(http_req_inc * 0.25)
            others = http_req_inc - gets - posts

            metrics_data["http_tot_gets"] += gets
            metrics_data["http_tot_posts"] += posts
            metrics_data["http_tot_others"] += others

            # HTTP versions
            http_11 = int(http_req_inc * 0.95)
            http_10 = http_req_inc - http_11

            metrics_data["http_tot_11_requests"] += http_11
            metrics_data["http_tot_10_requests"] += http_10
            metrics_data["http_tot_11_responses"] += int(http_resp_inc * 0.95)
            metrics_data["http_tot_10_responses"] += int(http_resp_inc * 0.05)

            # Bytes
            req_bytes_inc = http_req_inc * random.randint(400, 1500)
            resp_bytes_inc = http_resp_inc * random.randint(800, 4000)

            metrics_data["http_tot_rx_request_bytes"] += req_bytes_inc
            metrics_data["http_tot_rx_response_bytes"] += resp_bytes_inc
            metrics_data["http_tot_tx_request_bytes"] += req_bytes_inc

            # Chunked encoding
            chunked_req = int(http_req_inc * 0.05)
            chunked_resp = int(http_resp_inc * 0.1)
            metrics_data["http_tot_chunked_requests"] += chunked_req
            metrics_data["http_tot_chunked_responses"] += chunked_resp

            # Errors (rare)
            if random.random() < 0.1:
                metrics_data["http_err_tot_incomplete_headers"] += random.randint(1, 3)
            if random.random() < 0.05:
                metrics_data["http_err_tot_incomplete_requests"] += random.randint(1, 2)
            if random.random() < 0.05:
                metrics_data["http_err_tot_incomplete_responses"] += random.randint(1, 2)
            if random.random() < 0.03:
                metrics_data["http_err_tot_server_responses"] += random.randint(1, 5)

            # Update TCP Protocol Metrics
            tcp_rx_packets_inc = random.randint(5000, 30000)
            tcp_tx_packets_inc = random.randint(4000, 25000)

            metrics_data["tcp_tot_rx_packets"] += tcp_rx_packets_inc
            metrics_data["tcp_tot_tx_packets"] += tcp_tx_packets_inc

            tcp_rx_bytes_inc = tcp_rx_packets_inc * random.randint(500, 1500)
            tcp_tx_bytes_inc = tcp_tx_packets_inc * random.randint(500, 1500)

            metrics_data["tcp_tot_rx_bytes"] += tcp_rx_bytes_inc
            metrics_data["tcp_tx_bytes"] += tcp_tx_bytes_inc

            # Connections
            client_conn_inc = random.randint(50, 300)
            server_conn_inc = random.randint(40, 250)

            metrics_data["tcp_tot_client_conn_opened"] += client_conn_inc
            metrics_data["tcp_tot_server_conn_opened"] += server_conn_inc

            # SYN packets
            syn_inc = random.randint(50, 300)
            metrics_data["tcp_tot_syn"] += syn_inc
            metrics_data["tcp_tot_syn_probe"] += int(syn_inc * 0.1)

            # FIN packets
            metrics_data["tcp_tot_server_fin"] += random.randint(30, 200)
            metrics_data["tcp_tot_client_fin"] += random.randint(30, 200)

            # Current connections
            metrics_data["tcp_active_server_conn"] = random.randint(500, 2000)
            metrics_data["tcp_current_client_conn_est"] = random.randint(400, 1800)
            metrics_data["tcp_current_server_conn_est"] = random.randint(300, 1500)

            # Errors (rare)
            if random.random() < 0.05:
                metrics_data["tcp_err_badchecksum"] += random.randint(1, 3)
            if random.random() < 0.02:
                metrics_data["tcp_err_any_port_fail"] += random.randint(1, 2)

            # Update IP Protocol Metrics
            ip_rx_packets_inc = random.randint(10000, 50000)
            ip_tx_packets_inc = random.randint(8000, 45000)

            metrics_data["ip_tot_rx_packets"] += ip_rx_packets_inc
            metrics_data["ip_tx_packets"] += ip_tx_packets_inc

            ip_rx_bytes_inc = ip_rx_packets_inc * random.randint(600, 1500)
            ip_tx_bytes_inc = ip_tx_packets_inc * random.randint(600, 1500)

            metrics_data["ip_tot_rx_bytes"] += ip_rx_bytes_inc
            metrics_data["ip_tx_bytes"] += ip_tx_bytes_inc

            # Convert to Mbits
            ip_rx_mbits_inc = int(ip_rx_bytes_inc * 8 / 1000000)
            ip_tx_mbits_inc = int(ip_tx_bytes_inc * 8 / 1000000)

            metrics_data["ip_rx_mbits"] += ip_rx_mbits_inc
            metrics_data["ip_tx_mbits"] += ip_tx_mbits_inc

            # Routed packets
            routed_packets_inc = int(ip_rx_packets_inc * 0.3)
            metrics_data["ip_tot_routed_packets"] += routed_packets_inc
            metrics_data["ip_tot_routed_mbits"] += int(routed_packets_inc * 1200 * 8 / 1000000)

            # Fragments and assembly
            fragments_inc = int(ip_rx_packets_inc * 0.01)
            metrics_data["ip_tot_fragments"] += fragments_inc
            metrics_data["ip_tot_successful_assembly"] += int(fragments_inc * 0.98)

            # Address lookups
            metrics_data["ip_tot_address_lookup"] += random.randint(1000, 5000)

            # Errors (very rare)
            if random.random() < 0.02:
                metrics_data["ip_tot_bad_checksums"] += random.randint(1, 2)
            if random.random() < 0.01:
                metrics_data["ip_tot_ttl_expired"] += random.randint(1, 2)

            # Update Interface Metrics
            for intf_id, intf_metrics in metrics_data["interface"].items():
                # Large counters for network interfaces
                rx_bytes_inc = random.randint(100000, 10000000)
                tx_bytes_inc = random.randint(100000, 10000000)

                intf_metrics["tot_rx_bytes"] += rx_bytes_inc
                intf_metrics["tot_tx_bytes"] += tx_bytes_inc

                rx_packets_inc = random.randint(1000, 100000)
                tx_packets_inc = random.randint(1000, 100000)

                intf_metrics["tot_rx_packets"] += rx_packets_inc
                intf_metrics["tot_tx_packets"] += tx_packets_inc
                intf_metrics["tot_packets"] += rx_packets_inc + tx_packets_inc

                # Multicast
                intf_metrics["tot_multicast_packets"] += random.randint(10, 100)

                # Jumbo frames
                intf_metrics["jumbo_packets_received"] += int(rx_packets_inc * 0.05)
                intf_metrics["jumbo_packets_transmitted"] += int(tx_packets_inc * 0.05)

                # Trunk packets
                intf_metrics["trunk_packets_received"] += int(rx_packets_inc * 0.1)
                intf_metrics["trunk_packets_transmitted"] += int(tx_packets_inc * 0.1)

                # Rates
                intf_metrics["rx_bytes_rate"] = round(rx_bytes_inc / 5.0, 2)
                intf_metrics["tx_bytes_rate"] = round(tx_bytes_inc / 5.0, 2)
                intf_metrics["rx_packets_rate"] = round(rx_packets_inc / 5.0, 2)
                intf_metrics["tx_packets_rate"] = round(tx_packets_inc / 5.0, 2)

                # Errors (very rare)
                if random.random() < 0.02:
                    dropped_rx = random.randint(1, 5)
                    intf_metrics["err_dropped_rx_packets"] += dropped_rx
                    intf_metrics["err_dropped_rx_packets_rate"] = round(dropped_rx / 5.0, 2)
                else:
                    intf_metrics["err_dropped_rx_packets_rate"] = 0.0

                if random.random() < 0.02:
                    dropped_tx = random.randint(1, 5)
                    intf_metrics["err_dropped_tx_packets"] += dropped_tx
                    intf_metrics["err_dropped_tx_packets_rate"] = round(dropped_tx / 5.0, 2)
                else:
                    intf_metrics["err_dropped_tx_packets_rate"] = 0.0

                if random.random() < 0.01:
                    crc_errors = random.randint(1, 3)
                    intf_metrics["rx_crc_errors"] += crc_errors
                    intf_metrics["rx_crc_errors_rate"] = round(crc_errors / 5.0, 2)
                else:
                    intf_metrics["rx_crc_errors_rate"] = 0.0

            # Update AAA Metrics
            auth_success_inc = random.randint(50, 200)
            auth_fail_inc = random.randint(1, 5)

            metrics_data["aaa_auth_success"] += auth_success_inc
            metrics_data["aaa_auth_fail"] += auth_fail_inc

            # HTTP vs non-HTTP auth
            http_auth_success = int(auth_success_inc * 0.7)
            non_http_auth_success = auth_success_inc - http_auth_success

            metrics_data["aaa_auth_only_http_success"] += http_auth_success
            metrics_data["aaa_auth_non_http_success"] += non_http_auth_success

            http_auth_fail = int(auth_fail_inc * 0.6)
            metrics_data["aaa_auth_only_http_fail"] += http_auth_fail
            metrics_data["aaa_auth_non_http_fail"] += auth_fail_inc - http_auth_fail

            # Sessions
            new_sessions = random.randint(10, 50)
            metrics_data["aaa_tot_sessions"] += new_sessions

            # Session timeouts (rare)
            if random.random() < 0.1:
                metrics_data["aaa_tot_sessiontimeout"] += random.randint(1, 3)

            # TM sessions
            metrics_data["aaa_tot_tm_sessions"] += int(new_sessions * 0.3)

            # Current sessions and connections
            metrics_data["aaa_cur_sessions"] = random.randint(100, 500)
            metrics_data["aaa_cur_tm_sessions"] = random.randint(20, 100)
            metrics_data["aaa_cur_ica_sessions"] = random.randint(10, 50)
            metrics_data["aaa_cur_ica_only_conn"] = random.randint(5, 30)
            metrics_data["aaa_cur_ica_conn"] = random.randint(10, 60)

            # Update GSLB Site Metrics
            for site_name, site_metrics in metrics_data["gslb_site"].items():
                # 2% chance of site state change
                if random.random() < 0.02:
                    site_metrics["state"] = 0.0 if site_metrics["state"] == 1.0 else 1.0

                # RTT varies
                site_metrics["rtt_milliseconds"] = round(random.uniform(5, 50), 2)

            # Update GSLB VServer Metrics
            for gslb_vs_name, gslb_vs_metrics in metrics_data["gslb_vserver"].items():
                hits_inc = random.randint(50, 300)
                req_inc = random.randint(40, 280)

                gslb_vs_metrics["hits_total"] += hits_inc
                gslb_vs_metrics["requests_total"] += req_inc

            # Update HA Metrics
            metrics_data["ha_sync_success"] += random.randint(10, 50)

            # 1% chance of sync failure
            if random.random() < 0.01:
                metrics_data["ha_sync_failure"] += random.randint(1, 2)

            # 1% chance of heartbeat failure
            if random.random() < 0.01:
                metrics_data["ha_heartbeat_failures"] += random.randint(1, 2)

            # Update DNS Metrics
            queries_inc = random.randint(200, 1000)
            metrics_data["dns_tot_queries"] += queries_inc

            answers_inc = int(queries_inc * 0.95)
            metrics_data["dns_tot_answers"] += answers_inc

            # NXDOMAIN (not found)
            nxdomain_inc = int(queries_inc * 0.02)
            metrics_data["dns_tot_nxdomain"] += nxdomain_inc

            # Per-record queries
            for key, record_metrics in metrics_data["dns_record_queries"].items():
                record_queries_inc = random.randint(50, 300)
                record_metrics["queries"] += record_queries_inc

            # Update Cache Metrics
            cache_req_inc = random.randint(500, 2000)
            metrics_data["cache_tot_requests"] += cache_req_inc

            # Cache hit ratio 70-85%
            hit_ratio = random.uniform(0.70, 0.85)
            cache_hits_inc = int(cache_req_inc * hit_ratio)
            cache_misses_inc = cache_req_inc - cache_hits_inc

            metrics_data["cache_tot_hits"] += cache_hits_inc
            metrics_data["cache_tot_misses"] += cache_misses_inc

            # Bytes served from cache
            bytes_served_inc = cache_hits_inc * random.randint(2000, 10000)
            metrics_data["cache_bytes_served"] += bytes_served_inc

            # Update Compression Metrics
            compress_req_inc = random.randint(100, 500)
            metrics_data["compression_tot_requests"] += compress_req_inc

            # Compression ratio 60-75%
            metrics_data["compression_ratio"] = round(random.uniform(60, 75), 2)

            # Bandwidth savings
            original_bytes = compress_req_inc * random.randint(5000, 20000)
            compressed_bytes = int(original_bytes * (1 - metrics_data["compression_ratio"] / 100))
            savings = original_bytes - compressed_bytes
            metrics_data["compression_bandwidth_savings"] += savings

            # Update AppFirewall Metrics
            # Violations are rare (0-3 per interval)
            violations_inc = random.randint(0, 3)
            metrics_data["appfw_tot_violations"] += violations_inc

            # Most violations are logged
            if violations_inc > 0:
                metrics_data["appfw_tot_log"] += violations_inc

                # Some are blocked (30% of violations)
                blocked_inc = int(violations_inc * 0.3)
                metrics_data["appfw_tot_blocked"] += blocked_inc

                # Distribute violations across attack types
                if violations_inc > 0:
                    attack_type = random.choice(["sql", "xss", "csrf"])
                    if attack_type == "sql":
                        metrics_data["appfw_sql_injection_blocked"] += blocked_inc
                    elif attack_type == "xss":
                        metrics_data["appfw_xss_blocked"] += blocked_inc
                    else:
                        metrics_data["appfw_csrf_blocked"] += blocked_inc

            # Per-profile violations
            for profile_name, profile_metrics in metrics_data["appfw_profile"].items():
                if violations_inc > 0:
                    profile_violations = random.randint(0, violations_inc)
                    profile_metrics["violations_total"] += profile_violations

        except Exception as e:
            print(f"Error updating metrics: {e}")

        # Sleep for 5 seconds
        time.sleep(5)

# ============================================================================
# PROMETHEUS METRICS GENERATION
# ============================================================================

def generate_metrics() -> str:
    """Generate Prometheus-formatted metrics output with HELP and TYPE annotations."""

    lines: List[str] = []

    # ========================================================================
    # SYSTEM METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_cpu_number Number of CPUs")
    lines.append("# TYPE citrixadc_cpu_number counter")
    lines.append(f"citrixadc_cpu_number {CPU_CORES}")
    lines.append("")

    lines.append("# HELP citrixadc_cpu_usage_percent Total CPU usage percentage")
    lines.append("# TYPE citrixadc_cpu_usage_percent gauge")
    lines.append(f"citrixadc_cpu_usage_percent {metrics_data['cpu_usage']}")
    lines.append("")

    lines.append("# HELP citrixadc_memory_usage_percent Memory usage percentage")
    lines.append("# TYPE citrixadc_memory_usage_percent gauge")
    lines.append(f"citrixadc_memory_usage_percent {metrics_data['memory_usage']}")
    lines.append("")

    lines.append("# HELP citrixadc_management_cpu_usage_percent Management CPU usage percentage")
    lines.append("# TYPE citrixadc_management_cpu_usage_percent gauge")
    lines.append(f"citrixadc_management_cpu_usage_percent {metrics_data['mgmt_cpu_usage']}")
    lines.append("")

    lines.append("# HELP citrixadc_packet_cpu_usage_percent Packet engine CPU usage percentage")
    lines.append("# TYPE citrixadc_packet_cpu_usage_percent gauge")
    lines.append(f"citrixadc_packet_cpu_usage_percent {metrics_data['packet_cpu_usage']}")
    lines.append("")

    lines.append("# HELP citrixadc_res_cpu_usage_percent Resource CPU usage percentage")
    lines.append("# TYPE citrixadc_res_cpu_usage_percent gauge")
    lines.append(f"citrixadc_res_cpu_usage_percent {metrics_data['res_cpu_usage']}")
    lines.append("")

    lines.append("# HELP citrixadc_var_partition_free_mb Var partition free space in MB")
    lines.append("# TYPE citrixadc_var_partition_free_mb counter")
    lines.append(f"citrixadc_var_partition_free_mb {metrics_data['var_partition_free_mb']}")
    lines.append("")

    lines.append("# HELP citrixadc_var_partition_used_mb Var partition used space in MB")
    lines.append("# TYPE citrixadc_var_partition_used_mb counter")
    lines.append(f"citrixadc_var_partition_used_mb {metrics_data['var_partition_used_mb']}")
    lines.append("")

    var_total = metrics_data['var_partition_free_mb'] + metrics_data['var_partition_used_mb']
    var_used_percent = (metrics_data['var_partition_used_mb'] / var_total * 100) if var_total > 0 else 0
    lines.append("# HELP citrixadc_var_partition_used_percent Var partition used percentage")
    lines.append("# TYPE citrixadc_var_partition_used_percent gauge")
    lines.append(f"citrixadc_var_partition_used_percent {var_used_percent:.2f}")
    lines.append("")

    lines.append("# HELP citrixadc_flash_partition_free_mb Flash partition free space in MB")
    lines.append("# TYPE citrixadc_flash_partition_free_mb counter")
    lines.append(f"citrixadc_flash_partition_free_mb {metrics_data['flash_partition_free_mb']}")
    lines.append("")

    lines.append("# HELP citrixadc_flash_partition_used_mb Flash partition used space in MB")
    lines.append("# TYPE citrixadc_flash_partition_used_mb counter")
    lines.append(f"citrixadc_flash_partition_used_mb {metrics_data['flash_partition_used_mb']}")
    lines.append("")

    flash_total = metrics_data['flash_partition_free_mb'] + metrics_data['flash_partition_used_mb']
    flash_used_percent = (metrics_data['flash_partition_used_mb'] / flash_total * 100) if flash_total > 0 else 0
    lines.append("# HELP citrixadc_flash_partition_used_percent Flash partition used percentage")
    lines.append("# TYPE citrixadc_flash_partition_used_percent gauge")
    lines.append(f"citrixadc_flash_partition_used_percent {flash_used_percent:.2f}")
    lines.append("")

    lines.append("# HELP citrixadc_cpu_core_usage_percent Per-core CPU usage percentage")
    lines.append("# TYPE citrixadc_cpu_core_usage_percent gauge")
    for core_idx, usage in enumerate(metrics_data['cpu_core_usage']):
        lines.append(f'citrixadc_cpu_core_usage_percent{{core="{core_idx}"}} {usage}')
    lines.append("")

    lines.append("# HELP citrixadc_throughput_rx_mbits_rate Receive throughput rate in Mbits/sec")
    lines.append("# TYPE citrixadc_throughput_rx_mbits_rate gauge")
    lines.append(f"citrixadc_throughput_rx_mbits_rate {metrics_data['throughput_rx_mbits']}")
    lines.append("")

    lines.append("# HELP citrixadc_throughput_tx_mbits_rate Transmit throughput rate in Mbits/sec")
    lines.append("# TYPE citrixadc_throughput_tx_mbits_rate gauge")
    lines.append(f"citrixadc_throughput_tx_mbits_rate {metrics_data['throughput_tx_mbits']}")
    lines.append("")

    # ========================================================================
    # BANDWIDTH METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_max_bandwidth Maximum bandwidth in Mbps")
    lines.append("# TYPE citrixadc_max_bandwidth counter")
    lines.append(f"citrixadc_max_bandwidth {metrics_data['max_bandwidth']}")
    lines.append("")

    lines.append("# HELP citrixadc_min_bandwidth Minimum bandwidth in Mbps")
    lines.append("# TYPE citrixadc_min_bandwidth counter")
    lines.append(f"citrixadc_min_bandwidth {metrics_data['min_bandwidth']}")
    lines.append("")

    lines.append("# HELP citrixadc_actual_bandwidth Actual bandwidth in Mbps")
    lines.append("# TYPE citrixadc_actual_bandwidth counter")
    lines.append(f"citrixadc_actual_bandwidth {metrics_data['actual_bandwidth']}")
    lines.append("")

    lines.append("# HELP citrixadc_allocated_licensed_bandwidth Allocated licensed bandwidth in Mbps")
    lines.append("# TYPE citrixadc_allocated_licensed_bandwidth counter")
    lines.append(f"citrixadc_allocated_licensed_bandwidth {metrics_data['allocated_licensed_bandwidth']}")
    lines.append("")

    # ========================================================================
    # LB VSERVER METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_lb_hits_total Total hits to LB vserver")
    lines.append("# TYPE citrixadc_lb_hits_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_hits_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["hits_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_requests_total Total requests to LB vserver")
    lines.append("# TYPE citrixadc_lb_requests_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_requests_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["requests_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_responses_total Total responses from LB vserver")
    lines.append("# TYPE citrixadc_lb_responses_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_responses_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["responses_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_request_bytes_total Total request bytes to LB vserver")
    lines.append("# TYPE citrixadc_lb_request_bytes_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_request_bytes_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["request_bytes_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_response_bytes_received_total Total response bytes from LB vserver")
    lines.append("# TYPE citrixadc_lb_response_bytes_received_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_response_bytes_received_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["response_bytes_received_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_packets_sent_total Total packets sent by LB vserver")
    lines.append("# TYPE citrixadc_lb_packets_sent_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_packets_sent_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["packets_sent_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_packets_received_total Total packets received by LB vserver")
    lines.append("# TYPE citrixadc_lb_packets_received_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_packets_received_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["packets_received_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_surge_count Current surge count of LB vserver")
    lines.append("# TYPE citrixadc_lb_surge_count counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_surge_count{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["surge_count"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_spillover_count_total Total spillover count of LB vserver")
    lines.append("# TYPE citrixadc_lb_spillover_count_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_spillover_count_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["spillover_count_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_deffered_requests_total Total deferred requests on LB vserver")
    lines.append("# TYPE citrixadc_lb_deffered_requests_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_deffered_requests_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["deferred_requests_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_invalid_response_request_total Total invalid response/request on LB vserver")
    lines.append("# TYPE citrixadc_lb_invalid_response_request_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_invalid_response_request_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["invalid_response_request_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_busy_error_total Total busy errors on LB vserver")
    lines.append("# TYPE citrixadc_lb_busy_error_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_busy_error_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["busy_error_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_frustrating_transactions_total Total frustrating transactions on LB vserver")
    lines.append("# TYPE citrixadc_lb_frustrating_transactions_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_frustrating_transactions_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["frustrating_transactions_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_tolerable_transactions_total Total tolerable transactions on LB vserver")
    lines.append("# TYPE citrixadc_lb_tolerable_transactions_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_tolerable_transactions_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["tolerable_transactions_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_ttlb_calculated_transactions_total Total TTLB calculated transactions on LB vserver")
    lines.append("# TYPE citrixadc_lb_ttlb_calculated_transactions_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_ttlb_calculated_transactions_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["ttlb_calculated_transactions_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_backup_server_divert_count_total Total backup server divert count on LB vserver")
    lines.append("# TYPE citrixadc_lb_backup_server_divert_count_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_backup_server_divert_count_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["backup_server_divert_count_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_request_rate Request rate on LB vserver")
    lines.append("# TYPE citrixadc_lb_request_rate gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_request_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["request_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_request_rate_bytes Request rate in bytes on LB vserver")
    lines.append("# TYPE citrixadc_lb_request_rate_bytes gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_request_rate_bytes{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["request_rate_bytes"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_total_responses_rate Total response rate on LB vserver")
    lines.append("# TYPE citrixadc_lb_total_responses_rate gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_total_responses_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["total_responses_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_response_bytes_received_rate Response bytes received rate on LB vserver")
    lines.append("# TYPE citrixadc_lb_response_bytes_received_rate gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_response_bytes_received_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["response_bytes_received_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_hits_rate Hits rate on LB vserver")
    lines.append("# TYPE citrixadc_lb_hits_rate gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_hits_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["hits_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_average_ttlb Average Time To Last Byte on LB vserver in milliseconds")
    lines.append("# TYPE citrixadc_lb_average_ttlb gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_average_ttlb{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["average_ttlb"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_active_sessions_count Active sessions count on LB vserver")
    lines.append("# TYPE citrixadc_lb_active_sessions_count gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_active_sessions_count{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["active_sessions_count"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_inactive_services_count Inactive services count on LB vserver")
    lines.append("# TYPE citrixadc_lb_inactive_services_count gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_inactive_services_count{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["inactive_services_count"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_established_connections_count Established connections count on LB vserver")
    lines.append("# TYPE citrixadc_lb_established_connections_count gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_established_connections_count{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["established_connections_count"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_current_client_connection_count Current client connection count on LB vserver")
    lines.append("# TYPE citrixadc_lb_current_client_connection_count gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_current_client_connection_count{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["current_client_connection_count"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_actual_server_current_connections Current server connections on LB vserver")
    lines.append("# TYPE citrixadc_lb_actual_server_current_connections gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_actual_server_current_connections{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["actual_server_current_connections"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_surge_queue_requests_count Surge queue requests count on LB vserver")
    lines.append("# TYPE citrixadc_lb_surge_queue_requests_count gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_surge_queue_requests_count{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["surge_queue_requests_count"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_spill_over_threshold Spillover threshold on LB vserver")
    lines.append("# TYPE citrixadc_lb_spill_over_threshold gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_spill_over_threshold{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["spill_over_threshold"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_client_response_time_adex Client response time APDEX score (0 to 1) on LB vserver")
    lines.append("# TYPE citrixadc_lb_client_response_time_adex gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_client_response_time_adex{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["client_response_time_apdex"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_deferred_requets_rate Deferred requests rate on LB vserver")
    lines.append("# TYPE citrixadc_lb_deferred_requets_rate gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_deferred_requets_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["deferred_requests_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_busy_error_rate Busy error rate on LB vserver")
    lines.append("# TYPE citrixadc_lb_busy_error_rate gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_busy_error_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["busy_error_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_frustrating_transactions_rate Frustrating transactions rate on LB vserver")
    lines.append("# TYPE citrixadc_lb_frustrating_transactions_rate gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_frustrating_transactions_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["frustrating_transactions_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_members_up_total Number of members UP in LB vserver")
    lines.append("# TYPE citrixadc_lb_members_up_total counter")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_members_up_total{{name="{name}"}} {vs_metrics["members_up_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_lb_vserver_health LB vserver health percentage (0-100)")
    lines.append("# TYPE citrixadc_lb_vserver_health gauge")
    for vs in LB_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["lb_vserver"][name]
        lines.append(f'citrixadc_lb_vserver_health{{name="{name}",type="{vs["type"]}",state="{vs["state"]}",domain="{_LB_DOMAIN[name]}"}} {vs_metrics["vserver_health"]}')
    lines.append("")

    # ========================================================================
    # CS VSERVER METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_cs_hits_total Total hits to CS vserver")
    lines.append("# TYPE citrixadc_cs_hits_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_hits_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["hits_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_requests_total Total requests to CS vserver")
    lines.append("# TYPE citrixadc_cs_requests_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_requests_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["requests_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_responses_total Total responses from CS vserver")
    lines.append("# TYPE citrixadc_cs_responses_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_responses_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["responses_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_request_bytes_total Total request bytes to CS vserver")
    lines.append("# TYPE citrixadc_cs_request_bytes_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_request_bytes_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["request_bytes_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_response_bytes_received_total Total response bytes from CS vserver")
    lines.append("# TYPE citrixadc_cs_response_bytes_received_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_response_bytes_received_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["response_bytes_received_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_packets_sent_total Total packets sent by CS vserver")
    lines.append("# TYPE citrixadc_cs_packets_sent_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_packets_sent_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["packets_sent_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_packets_received_total Total packets received by CS vserver")
    lines.append("# TYPE citrixadc_cs_packets_received_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_packets_received_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["packets_received_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_spillover_count_total Total spillover count of CS vserver")
    lines.append("# TYPE citrixadc_cs_spillover_count_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_spillover_count_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["spillover_count_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_deferred_requests_total Total deferred requests on CS vserver")
    lines.append("# TYPE citrixadc_cs_deferred_requests_total counter")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_deferred_requests_total{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["deferred_requests_total"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_request_rate Request rate on CS vserver")
    lines.append("# TYPE citrixadc_cs_request_rate gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_request_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["request_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_total_responses_rate Total response rate on CS vserver")
    lines.append("# TYPE citrixadc_cs_total_responses_rate gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_total_responses_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["total_responses_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_hits_rate Hits rate on CS vserver")
    lines.append("# TYPE citrixadc_cs_hits_rate gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_hits_rate{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["hits_rate"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_average_ttlb Average Time To Last Byte on CS vserver in milliseconds")
    lines.append("# TYPE citrixadc_cs_average_ttlb gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_average_ttlb{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["average_ttlb"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_established_connections_count Established connections count on CS vserver")
    lines.append("# TYPE citrixadc_cs_established_connections_count gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_established_connections_count{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["established_connections_count"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_current_client_connection_count Current client connection count on CS vserver")
    lines.append("# TYPE citrixadc_cs_current_client_connection_count gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_current_client_connection_count{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["current_client_connection_count"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_actual_server_current_connections Current server connections on CS vserver")
    lines.append("# TYPE citrixadc_cs_actual_server_current_connections gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_actual_server_current_connections{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["actual_server_current_connections"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_client_response_time_adex Client response time APDEX score (0 to 1) on CS vserver")
    lines.append("# TYPE citrixadc_cs_client_response_time_adex gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_client_response_time_adex{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["client_response_time_apdex"]}')
    lines.append("")

    lines.append("# HELP citrixadc_cs_spill_over_threshold Spillover threshold on CS vserver")
    lines.append("# TYPE citrixadc_cs_spill_over_threshold gauge")
    for vs in CS_VSERVERS:
        name = vs["name"]
        vs_metrics = metrics_data["cs_vserver"][name]
        lines.append(f'citrixadc_cs_spill_over_threshold{{name="{name}",type="{vs["type"]}",state="{vs["state"]}"}} {vs_metrics["spill_over_threshold"]}')
    lines.append("")

    # ========================================================================
    # SERVICE METRICS
    # ========================================================================

    svc_counters = [
        ("citrixadc_service_throughput", "Total throughput of the service", "counter", "throughput"),
        ("citrixadc_service_tot_requests", "Total requests to the service", "counter", "tot_requests"),
        ("citrixadc_service_tot_responses", "Total responses from the service", "counter", "tot_responses"),
        ("citrixadc_service_tot_request_bytes", "Total request bytes to the service", "counter", "tot_request_bytes"),
        ("citrixadc_service_tot_response_bytes", "Total response bytes from the service", "counter", "tot_response_bytes"),
        ("citrixadc_service_surge_count", "Surge count of the service", "counter", "surge_count"),
        ("citrixadc_service_server_established_connections", "Server established connections", "counter", "server_established_connections"),
        ("citrixadc_service_max_clients", "Maximum clients of the service", "counter", "max_clients"),
        ("citrixadc_service_vsvr_hits", "VServer hits for the service", "counter", "vsvr_hits"),
    ]
    svc_gauges = [
        ("citrixadc_service_throughput_rate", "Throughput rate of the service", "gauge", "throughput_rate"),
        ("citrixadc_service_average_server_ttfb", "Average server TTFB in milliseconds", "gauge", "average_server_ttfb"),
        ("citrixadc_service_responses_rate", "Response rate of the service", "gauge", "responses_rate"),
        ("citrixadc_service_request_bytes_rate", "Request bytes rate", "gauge", "request_bytes_rate"),
        ("citrixadc_service_response_bytes_rate", "Response bytes rate", "gauge", "response_bytes_rate"),
        ("citrixadc_service_current_client_connections", "Current client connections", "gauge", "current_client_connections"),
        ("citrixadc_service_current_server_connections", "Current server connections", "gauge", "current_server_connections"),
        ("citrixadc_service_current_pool_use", "Current pool usage", "gauge", "current_pool_use"),
        ("citrixadc_service_current_load", "Current load on the service", "gauge", "current_load"),
        ("citrixadc_service_active_transactions", "Active transactions", "gauge", "active_transactions"),
    ]
    for metric_name, help_text, metric_type, key in svc_counters + svc_gauges:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} {metric_type}")
        for svc in SERVICES:
            sname = svc["name"]
            val = metrics_data["service"][sname][key]
            lines.append(f'{metric_name}{{name="{sname}",type="{svc["type"]}",state="{svc["state"]}"}} {val}')
        lines.append("")

    # ========================================================================
    # SERVICE GROUP METRICS
    # ========================================================================

    sg_metrics_def = [
        ("citrixadc_services_tot_responses", "Total responses from service group member", "counter", "tot_responses"),
        ("citrixadc_services_tot_requests", "Total requests to service group member", "counter", "tot_requests"),
        ("citrixadc_services_tot_response_bytes", "Total response bytes", "counter", "tot_response_bytes"),
        ("citrixadc_services_tot_request_bytes", "Total request bytes", "counter", "tot_request_bytes"),
        ("citrixadc_services_avg_server_ttfb", "Average server TTFB in milliseconds", "gauge", "avg_server_ttfb"),
        ("citrixadc_services_requests_rate", "Request rate", "gauge", "requests_rate"),
        ("citrixadc_services_current_server_connections", "Current server connections", "gauge", "current_server_connections"),
        ("citrixadc_services_responses_rate", "Response rate", "gauge", "responses_rate"),
    ]
    for metric_name, help_text, metric_type, key in sg_metrics_def:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} {metric_type}")
        for sg in SERVICE_GROUPS:
            for member in sg["members"]:
                sg_key = f"{sg['name']}_{member['ip']}"
                sg_data = metrics_data["service_group"][sg_key]
                val = sg_data[key]
                lines.append(f'{metric_name}{{servicegroup_name="{sg["name"]}",service_type="{sg["type"]}",state="{sg["state"]}",ip="{member["ip"]}",server_name="{member["server"]}"}} {val}')
        lines.append("")

    # ========================================================================
    # SSL GLOBAL METRICS
    # ========================================================================

    ssl_global = [
        ("citrixadc_ssl_tot_sessions", "Total SSL sessions", "counter", "ssl_tot_sessions"),
        ("citrixadc_ssl_tot_tlsv11_sessions", "Total TLSv1.1 sessions", "counter", "ssl_tot_tlsv11_sessions"),
        ("citrixadc_ssl_tot_v2_sessions", "Total SSLv2 sessions", "counter", "ssl_tot_v2_sessions"),
        ("citrixadc_ssl_tot_v2_handshakes", "Total SSLv2 handshakes", "counter", "ssl_tot_v2_handshakes"),
        ("citrixadc_ssl_tot_encode", "Total SSL encode operations", "counter", "ssl_tot_encode"),
        ("citrixadc_ssl_tot_new_sessions", "Total new SSL sessions", "counter", "ssl_tot_new_sessions"),
        ("citrixadc_ssl_crypto_utilization_stat", "SSL crypto hardware utilization", "counter", "ssl_crypto_utilization"),
        ("citrixadc_ssl_session_rate", "SSL session rate", "gauge", "ssl_session_rate"),
        ("citrixadc_ssl_dec_rate", "SSL decryption rate", "gauge", "ssl_dec_rate"),
        ("citrixadc_ssl_encode_rate", "SSL encode rate", "gauge", "ssl_encode_rate"),
    ]
    for metric_name, help_text, metric_type, key in ssl_global:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} {metric_type}")
        lines.append(f"{metric_name} {metrics_data[key]}")
        lines.append("")

    # SSL v2 handshakes rate and new sessions rate
    lines.append("# HELP citrixadc_ssl_v2_handshakes_rate SSLv2 handshakes rate")
    lines.append("# TYPE citrixadc_ssl_v2_handshakes_rate gauge")
    lines.append(f"citrixadc_ssl_v2_handshakes_rate {round(random.uniform(0, 5), 2)}")
    lines.append("")
    lines.append("# HELP citrixadc_new_sessions_rate New SSL sessions rate")
    lines.append("# TYPE citrixadc_new_sessions_rate gauge")
    lines.append(f"citrixadc_new_sessions_rate {round(random.uniform(50, 200), 2)}")
    lines.append("")

    # SSL CertKey
    lines.append("# HELP citrixadc_ssl_cert_days_to_expire Days until SSL certificate expires")
    lines.append("# TYPE citrixadc_ssl_cert_days_to_expire gauge")
    for cert in SSL_CERTS:
        lines.append(f'citrixadc_ssl_cert_days_to_expire{{certkey="{cert["name"]}",instance="{INSTANCE_NAME}",region="{INSTANCE_REGION}",role="{INSTANCE_ROLE}"}} {cert["days_to_expire"]}')
    lines.append("")

    # SSL VServer metrics
    ssl_vs_metrics = [
        ("citrixadc_sslvserver_decrypt_bytes_total", "Total decrypted bytes", "counter", "decrypt_bytes_total"),
        ("citrixadc_sslvserver_encrypt_bytes_total", "Total encrypted bytes", "counter", "encrypt_bytes_total"),
        ("citrixadc_sslvserver_session_new_total", "Total new sessions", "counter", "session_new_total"),
        ("citrixadc_sslvserver_session_hits_total", "Total session hits", "counter", "session_hits_total"),
        ("citrixadc_sslvserver_auth_success_total", "Total auth successes", "counter", "auth_success_total"),
        ("citrixadc_sslvserver_auth_failure_total", "Total auth failures", "counter", "auth_failure_total"),
        ("citrixadc_sslvserver_health", "SSL VServer health", "gauge", "health"),
        ("citrixadc_sslvserver_active_services", "Active services count", "gauge", "active_services"),
        ("citrixadc_sslvserver_encrypt_bytes_rate", "Encrypt bytes rate", "gauge", "encrypt_bytes_rate"),
        ("citrixadc_sslvserver_decrypt_bytes_rate", "Decrypt bytes rate", "gauge", "decrypt_bytes_rate"),
        ("citrixadc_sslvserver_session_new_rate", "New session rate", "gauge", "session_new_rate"),
        ("citrixadc_sslvserver_session_hits_rate", "Session hits rate", "gauge", "session_hits_rate"),
        ("citrixadc_sslvserver_auth_success_rate", "Auth success rate", "gauge", "auth_success_rate"),
        ("citrixadc_sslvserver_auth_failure_rate", "Auth failure rate", "gauge", "auth_failure_rate"),
    ]
    for metric_name, help_text, metric_type, key in ssl_vs_metrics:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} {metric_type}")
        for svs in SSL_VSERVERS:
            sname = svs["name"]
            val = metrics_data["ssl_vserver"][sname][key]
            lines.append(f'{metric_name}{{name="{sname}",type="{svs["type"]}",ip="{svs["ip"]}",state="{svs["state"]}"}} {val}')
        lines.append("")

    # ========================================================================
    # PROTOCOL HTTP METRICS
    # ========================================================================

    http_counters = [
        ("citrixadc_http_tot_requests", "Total HTTP requests received", "http_tot_requests"),
        ("citrixadc_http_tot_responses", "Total HTTP responses sent", "http_tot_responses"),
        ("citrixadc_http_tot_gets", "Total HTTP GET requests", "http_tot_gets"),
        ("citrixadc_http_tot_posts", "Total HTTP POST requests", "http_tot_posts"),
        ("citrixadc_http_tot_others", "Total other HTTP requests", "http_tot_others"),
        ("citrixadc_http_tot_rx_request_bytes", "Total HTTP request bytes received", "http_tot_rx_request_bytes"),
        ("citrixadc_http_tot_rx_response_bytes", "Total HTTP response bytes received", "http_tot_rx_response_bytes"),
        ("citrixadc_http_tot_tx_request_bytes", "Total HTTP request bytes transmitted", "http_tot_tx_request_bytes"),
        ("citrixadc_http_tot_10_requests", "Total HTTP 1.0 requests", "http_tot_10_requests"),
        ("citrixadc_http_tot_11_requests", "Total HTTP 1.1 requests", "http_tot_11_requests"),
        ("citrixadc_http_tot_10_responses", "Total HTTP 1.0 responses", "http_tot_10_responses"),
        ("citrixadc_http_tot_11_responses", "Total HTTP 1.1 responses", "http_tot_11_responses"),
        ("citrixadc_http_tot_chunked_requests", "Total chunked HTTP requests", "http_tot_chunked_requests"),
        ("citrixadc_http_tot_chunked_responses", "Total chunked HTTP responses", "http_tot_chunked_responses"),
        ("citrixadc_http_err_tot_incomplete_header_packets", "Total incomplete header packets", "http_err_tot_incomplete_headers"),
        ("citrixadc_http_err_tot_incomplete_requests", "Total incomplete HTTP requests", "http_err_tot_incomplete_requests"),
        ("citrixadc_http_err_tot_incomplete_responses", "Total incomplete HTTP responses", "http_err_tot_incomplete_responses"),
        ("citrixadc_http_err_tot_server_responses", "Total HTTP server error responses", "http_err_tot_server_responses"),
        ("citrixadc_http_err_tot_large_body_packets", "Total large body packets", "http_err_tot_large_body"),
        ("citrixadc_http_err_tot_large_chunk_requests", "Total large chunk requests", "http_err_tot_large_chunk"),
        ("citrixadc_http_err_tot_large_content_requests", "Total large content requests", "http_err_tot_large_content"),
    ]
    for metric_name, help_text, key in http_counters:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} counter")
        lines.append(f"{metric_name} {metrics_data[key]}")
        lines.append("")

    # HTTP rates (gauges derived from counters)
    http_rate_interval = 5.0
    http_rates = [
        ("citrixadc_http_requests_rate", "HTTP requests rate", round(random.uniform(500, 5000), 2)),
        ("citrixadc_http_responses_rate", "HTTP responses rate", round(random.uniform(500, 5000), 2)),
        ("citrixadc_http_gets_rate", "HTTP GET requests rate", round(random.uniform(300, 3000), 2)),
        ("citrixadc_http_posts_rate", "HTTP POST requests rate", round(random.uniform(100, 1000), 2)),
        ("citrixadc_http_rx_request_bytes_rate", "HTTP request bytes rate", round(random.uniform(100000, 5000000), 2)),
        ("citrixadc_http_rx_response_bytes_rate", "HTTP response bytes rate", round(random.uniform(500000, 10000000), 2)),
    ]
    for metric_name, help_text, val in http_rates:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {val}")
        lines.append("")

    # ========================================================================
    # PROTOCOL TCP METRICS
    # ========================================================================

    tcp_counters = [
        ("citrixadc_tcp_tot_rx_packets", "Total TCP packets received", "tcp_tot_rx_packets"),
        ("citrixadc_tcp_tot_rx_bytes", "Total TCP bytes received", "tcp_tot_rx_bytes"),
        ("citrixadc_tcp_tx_bytes", "Total TCP bytes transmitted", "tcp_tx_bytes"),
        ("citrixadc_tcp_tot_tx_packets", "Total TCP packets transmitted", "tcp_tot_tx_packets"),
        ("citrixadc_tcp_tot_client_connections_opened", "Total client connections opened", "tcp_tot_client_conn_opened"),
        ("citrixadc_tcp_tot_server_connections_opened", "Total server connections opened", "tcp_tot_server_conn_opened"),
        ("citrixadc_tcp_tot_syn", "Total TCP SYN packets", "tcp_tot_syn"),
        ("citrixadc_tcp_tot_syn_probe", "Total TCP SYN probe packets", "tcp_tot_syn_probe"),
        ("citrixadc_tcp_tot_server_fin", "Total TCP server FIN packets", "tcp_tot_server_fin"),
        ("citrixadc_tcp_tot_client_fin", "Total TCP client FIN packets", "tcp_tot_client_fin"),
    ]
    for metric_name, help_text, key in tcp_counters:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} counter")
        lines.append(f"{metric_name} {metrics_data[key]}")
        lines.append("")

    tcp_gauges = [
        ("citrixadc_tcp_active_server_connection", "Active server connections", "tcp_active_server_conn"),
        ("citrixadc_tcp_current_client_connections_est", "Current established client connections", "tcp_current_client_conn_est"),
        ("citrixadc_tcp_current_server_connections_est", "Current established server connections", "tcp_current_server_conn_est"),
        ("citrixadc_tcp_err_badchecksum", "TCP bad checksum errors", "tcp_err_badchecksum"),
        ("citrixadc_tcp_err_any_port_fail", "TCP any port fail errors", "tcp_err_any_port_fail"),
        ("citrixadc_tcp_err_ip_port_fail", "TCP IP port fail errors", "tcp_err_ip_port_fail"),
        ("citrixadc_tcp_err_bad_connection_state", "TCP bad connection state errors", "tcp_err_bad_conn_state"),
        ("citrixadc_tcp_err_reset_threshold", "TCP reset threshold errors", "tcp_err_reset_threshold"),
    ]
    for metric_name, help_text, key in tcp_gauges:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {metrics_data[key]}")
        lines.append("")

    # TCP rate gauges
    tcp_rates = [
        ("citrixadc_tcp_rx_packets_rate", "TCP RX packets rate", round(random.uniform(5000, 50000), 2)),
        ("citrixadc_tcp_rx_bytes_rate", "TCP RX bytes rate", round(random.uniform(1000000, 50000000), 2)),
        ("citrixadc_tcp_tx_packets_rate", "TCP TX packets rate", round(random.uniform(5000, 50000), 2)),
        ("citrixadc_tcp_tx_bytes_rate", "TCP TX bytes rate", round(random.uniform(1000000, 50000000), 2)),
        ("citrixadc_tcp_client_connection_opened_rate", "Client connection opened rate", round(random.uniform(100, 1000), 2)),
        ("citrixadc_tcp_syn_rate", "TCP SYN rate", round(random.uniform(100, 5000), 2)),
        ("citrixadc_tcp_syn_probe_rate", "TCP SYN probe rate", round(random.uniform(0, 50), 2)),
    ]
    for metric_name, help_text, val in tcp_rates:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {val}")
        lines.append("")

    # ========================================================================
    # PROTOCOL IP METRICS
    # ========================================================================

    ip_counters = [
        ("citrixadc_ip_tot_rx_packets", "Total IP packets received", "ip_tot_rx_packets"),
        ("citrixadc_ip_tot_rx_bytes", "Total IP bytes received", "ip_tot_rx_bytes"),
        ("citrixadc_ip_tx_packets", "Total IP packets transmitted", "ip_tx_packets"),
        ("citrixadc_ip_tx_bytes", "Total IP bytes transmitted", "ip_tx_bytes"),
        ("citrixadc_ip_rx_mbits", "IP received megabits", "ip_rx_mbits"),
        ("citrixadc_ip_tx_mbits", "IP transmitted megabits", "ip_tx_mbits"),
        ("citrixadc_ip_tot_routed_packets", "Total routed packets", "ip_tot_routed_packets"),
        ("citrixadc_ip_tot_routed_mbits", "Total routed megabits", "ip_tot_routed_mbits"),
        ("citrixadc_ip_tot_fragments", "Total IP fragments", "ip_tot_fragments"),
        ("citrixadc_ip_tot_successful_assembly", "Total successful assembly", "ip_tot_successful_assembly"),
        ("citrixadc_ip_tot_address_lookup", "Total address lookups", "ip_tot_address_lookup"),
        ("citrixadc_ip_tot_bad_checksums", "Total bad checksums", "ip_tot_bad_checksums"),
        ("citrixadc_ip_tot_ttl_expired", "Total TTL expired", "ip_tot_ttl_expired"),
        ("citrixadc_ip_tot_max_clients", "Total max clients reached", "ip_tot_max_clients"),
    ]
    for metric_name, help_text, key in ip_counters:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} counter")
        lines.append(f"{metric_name} {metrics_data[key]}")
        lines.append("")

    ip_rates = [
        ("citrixadc_ip_rx_packets_rate", "IP RX packets rate", round(random.uniform(10000, 100000), 2)),
        ("citrixadc_ip_rx_bytes_rate", "IP RX bytes rate", round(random.uniform(5000000, 50000000), 2)),
        ("citrixadc_ip_tx_packets_rate", "IP TX packets rate", round(random.uniform(10000, 100000), 2)),
        ("citrixadc_ip_bytes_rate", "IP bytes rate", round(random.uniform(5000000, 50000000), 2)),
        ("citrixadc_ip_rx_mbits_rate", "IP RX megabits rate", round(random.uniform(500, 3000), 2)),
        ("citrixadc_ip_tx_mbits_rate", "IP TX megabits rate", round(random.uniform(500, 3000), 2)),
        ("citrixadc_ip_routed_packets_rate", "Routed packets rate", round(random.uniform(1000, 50000), 2)),
    ]
    for metric_name, help_text, val in ip_rates:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {val}")
        lines.append("")

    # ========================================================================
    # INTERFACE METRICS
    # ========================================================================

    iface_metrics = [
        ("citrixadc_interface_tot_rx_bytes", "Total bytes received on interface", "counter", "tot_rx_bytes"),
        ("citrixadc_interface_tot_tx_bytes", "Total bytes transmitted on interface", "counter", "tot_tx_bytes"),
        ("citrixadc_interface_tot_rx_packets", "Total packets received on interface", "counter", "tot_rx_packets"),
        ("citrixadc_interface_tot_tx_packets", "Total packets transmitted on interface", "counter", "tot_tx_packets"),
        ("citrixadc_interface_tot_packets", "Total packets on interface", "counter", "tot_packets"),
        ("citrixadc_interface_tot_multicast_packets", "Total multicast packets", "counter", "tot_multicast_packets"),
        ("citrixadc_interface_rx_crc_errors", "RX CRC errors on interface", "counter", "rx_crc_errors"),
        ("citrixadc_interface_tot_mac_moved", "Total MAC moved events", "counter", "tot_mac_moved"),
        ("citrixadc_interface_err_dropped_rx_packets", "Dropped RX packets", "counter", "err_dropped_rx_packets"),
        ("citrixadc_interface_err_dropped_tx_packets", "Dropped TX packets", "counter", "err_dropped_tx_packets"),
        ("citrixadc_interface_link_reinitializations", "Link reinitializations", "counter", "link_reinitializations"),
        ("citrixadc_interface_jumbo_packets_received", "Jumbo packets received", "counter", "jumbo_packets_received"),
        ("citrixadc_interface_jumbo_packets_transmitted", "Jumbo packets transmitted", "counter", "jumbo_packets_transmitted"),
        ("citrixadc_interface_trunk_packets_received", "Trunk packets received", "counter", "trunk_packets_received"),
        ("citrixadc_interface_trunk_packets_transmitted", "Trunk packets transmitted", "counter", "trunk_packets_transmitted"),
        ("citrixadc_interface_rx_bytes_rate", "RX bytes rate on interface", "gauge", "rx_bytes_rate"),
        ("citrixadc_interface_tx_bytes_rate", "TX bytes rate on interface", "gauge", "tx_bytes_rate"),
        ("citrixadc_interface_rx_packets_rate", "RX packets rate on interface", "gauge", "rx_packets_rate"),
        ("citrixadc_interface_tx_packets_rate", "TX packets rate on interface", "gauge", "tx_packets_rate"),
        ("citrixadc_interface_err_dropped_rx_packets_rate", "Dropped RX packets rate", "gauge", "err_dropped_rx_packets_rate"),
        ("citrixadc_interface_err_dropped_tx_packets_rate", "Dropped TX packets rate", "gauge", "err_dropped_tx_packets_rate"),
        ("citrixadc_interface_rx_crc_errors_rate", "CRC errors rate", "gauge", "rx_crc_errors_rate"),
    ]
    for metric_name, help_text, metric_type, key in iface_metrics:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} {metric_type}")
        for iface in INTERFACES:
            iface_id = iface["id"]
            iface_data = metrics_data["interface"][iface_id]
            lines.append(f'{metric_name}{{id="{iface_id}",alias="{iface["alias"]}"}} {iface_data[key]}')
        lines.append("")

    # ========================================================================
    # AAA METRICS
    # ========================================================================

    aaa_counters = [
        ("citrixadc_aaa_auth_success", "Total AAA auth successes", "aaa_auth_success"),
        ("citrixadc_aaa_auth_fail", "Total AAA auth failures", "aaa_auth_fail"),
        ("citrixadc_aaa_auth_only_http_success", "Total AAA HTTP auth successes", "aaa_auth_only_http_success"),
        ("citrixadc_aaa_auth_only_http_fail", "Total AAA HTTP auth failures", "aaa_auth_only_http_fail"),
        ("citrixadc_aaa_auth_non_http_success", "Total AAA non-HTTP auth successes", "aaa_auth_non_http_success"),
        ("citrixadc_aaa_auth_non_http_fail", "Total AAA non-HTTP auth failures", "aaa_auth_non_http_fail"),
        ("citrixadc_aaa_tot_sessions", "Total AAA sessions", "aaa_tot_sessions"),
        ("citrixadc_aaa_tot_sessiontimeout", "Total AAA session timeouts", "aaa_tot_sessiontimeout"),
        ("citrixadc_aaa_tot_tm_sessions", "Total TM sessions", "aaa_tot_tm_sessions"),
    ]
    for metric_name, help_text, key in aaa_counters:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} counter")
        lines.append(f"{metric_name} {metrics_data[key]}")
        lines.append("")

    aaa_gauges = [
        ("citrixadc_aaa_cur_ica_sessions", "Current ICA sessions", "aaa_cur_ica_sessions"),
        ("citrixadc_aaa_cur_ica_only_conn", "Current ICA only connections", "aaa_cur_ica_only_conn"),
        ("citrixadc_aaa_cur_ica_conn", "Current ICA connections", "aaa_cur_ica_conn"),
        ("citrixadc_aaa_cur_tm_sessions", "Current TM sessions", "aaa_cur_tm_sessions"),
        ("citrixadc_aaa_cur_sessions", "Current AAA sessions", "aaa_cur_sessions"),
    ]
    for metric_name, help_text, key in aaa_gauges:
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {metrics_data[key]}")
        lines.append("")

    # AAA rates
    lines.append("# HELP citrixadc_aaa_auth_success_rate AAA auth success rate")
    lines.append("# TYPE citrixadc_aaa_auth_success_rate gauge")
    lines.append(f"citrixadc_aaa_auth_success_rate {round(random.uniform(10, 50), 2)}")
    lines.append("")
    lines.append("# HELP citrixadc_aaa_auth_fail_rate AAA auth failure rate")
    lines.append("# TYPE citrixadc_aaa_auth_fail_rate gauge")
    lines.append(f"citrixadc_aaa_auth_fail_rate {round(random.uniform(0, 2), 2)}")
    lines.append("")

    # ========================================================================
    # GSLB METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_gslb_site_state GSLB site state (1=ACTIVE, 0=INACTIVE)")
    lines.append("# TYPE citrixadc_gslb_site_state gauge")
    for site in GSLB_SITES:
        val = metrics_data["gslb_site"].get(site["name"], {}).get("state", 1)
        lines.append(f'citrixadc_gslb_site_state{{name="{site["name"]}",ip="{site["ip"]}"}} {val}')
    lines.append("")

    lines.append("# HELP citrixadc_gslb_service_state GSLB service state (1=UP, 0=DOWN)")
    lines.append("# TYPE citrixadc_gslb_service_state gauge")
    for site in GSLB_SITES:
        site_data = metrics_data["gslb_site"].get(site["name"], {})
        lines.append(f'citrixadc_gslb_service_state{{name="{site["name"]}_svc",ip="{site["ip"]}",site="{site["name"]}"}} {site_data.get("service_state", 1)}')
    lines.append("")

    lines.append("# HELP citrixadc_gslb_site_rtt_milliseconds GSLB site round-trip time in milliseconds")
    lines.append("# TYPE citrixadc_gslb_site_rtt_milliseconds gauge")
    for site in GSLB_SITES:
        site_data = metrics_data["gslb_site"].get(site["name"], {})
        lines.append(f'citrixadc_gslb_site_rtt_milliseconds{{name="{site["name"]}"}} {site_data.get("rtt_milliseconds", 25)}')
    lines.append("")

    lines.append("# HELP citrixadc_gslb_vserver_hits_total Total GSLB vserver hits")
    lines.append("# TYPE citrixadc_gslb_vserver_hits_total counter")
    for gvs in GSLB_VSERVERS:
        gvs_data = metrics_data["gslb_vserver"].get(gvs["name"], {})
        lines.append(f'citrixadc_gslb_vserver_hits_total{{name="{gvs["name"]}",type="{gvs["type"]}",state="{gvs["state"]}"}} {gvs_data.get("hits_total", 0)}')
    lines.append("")

    lines.append("# HELP citrixadc_gslb_vserver_requests_total Total GSLB vserver requests")
    lines.append("# TYPE citrixadc_gslb_vserver_requests_total counter")
    for gvs in GSLB_VSERVERS:
        gvs_data = metrics_data["gslb_vserver"].get(gvs["name"], {})
        lines.append(f'citrixadc_gslb_vserver_requests_total{{name="{gvs["name"]}",type="{gvs["type"]}",state="{gvs["state"]}"}} {gvs_data.get("requests_total", 0)}')
    lines.append("")

    # ========================================================================
    # HA METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_ha_node_state HA node state (1=PRIMARY, 0.5=SECONDARY, 0=UNKNOWN)")
    lines.append("# TYPE citrixadc_ha_node_state gauge")
    lines.append(f'citrixadc_ha_node_state{{node="primary",ip="10.0.0.1"}} 1')
    lines.append(f'citrixadc_ha_node_state{{node="secondary",ip="10.0.0.2"}} 0.5')
    lines.append("")

    lines.append("# HELP citrixadc_ha_sync_success_total Total HA sync successes")
    lines.append("# TYPE citrixadc_ha_sync_success_total counter")
    lines.append(f"citrixadc_ha_sync_success_total {metrics_data['ha_sync_success']}")
    lines.append("")

    lines.append("# HELP citrixadc_ha_sync_failure_total Total HA sync failures")
    lines.append("# TYPE citrixadc_ha_sync_failure_total counter")
    lines.append(f"citrixadc_ha_sync_failure_total {metrics_data['ha_sync_failure']}")
    lines.append("")

    lines.append("# HELP citrixadc_ha_heartbeat_failures_total Total HA heartbeat failures")
    lines.append("# TYPE citrixadc_ha_heartbeat_failures_total counter")
    lines.append(f"citrixadc_ha_heartbeat_failures_total {metrics_data['ha_heartbeat_failures']}")
    lines.append("")

    # ========================================================================
    # DNS METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_dns_tot_queries Total DNS queries")
    lines.append("# TYPE citrixadc_dns_tot_queries counter")
    lines.append(f"citrixadc_dns_tot_queries {metrics_data['dns_tot_queries']}")
    lines.append("")

    lines.append("# HELP citrixadc_dns_queries_rate DNS queries rate")
    lines.append("# TYPE citrixadc_dns_queries_rate gauge")
    lines.append(f"citrixadc_dns_queries_rate {round(random.uniform(200, 1000), 2)}")
    lines.append("")

    lines.append("# HELP citrixadc_dns_tot_answers Total DNS answers")
    lines.append("# TYPE citrixadc_dns_tot_answers counter")
    lines.append(f"citrixadc_dns_tot_answers {metrics_data['dns_tot_answers']}")
    lines.append("")

    lines.append("# HELP citrixadc_dns_tot_nxdomain Total DNS NXDOMAIN responses")
    lines.append("# TYPE citrixadc_dns_tot_nxdomain counter")
    lines.append(f"citrixadc_dns_tot_nxdomain {metrics_data['dns_tot_nxdomain']}")
    lines.append("")

    lines.append("# HELP citrixadc_dns_record_queries_total Total DNS record queries")
    lines.append("# TYPE citrixadc_dns_record_queries_total counter")
    for rec in DNS_RECORDS:
        key = f"{rec['domain']}_{rec['type']}"
        record_data = metrics_data["dns_record_queries"].get(key, {})
        val = record_data.get("queries", 0) if isinstance(record_data, dict) else record_data
        lines.append(f'citrixadc_dns_record_queries_total{{domain="{rec["domain"]}",type="{rec["type"]}"}} {val}')
    lines.append("")

    # ========================================================================
    # CACHE METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_cache_tot_requests Total cache requests")
    lines.append("# TYPE citrixadc_cache_tot_requests counter")
    lines.append(f"citrixadc_cache_tot_requests {metrics_data['cache_tot_requests']}")
    lines.append("")

    lines.append("# HELP citrixadc_cache_tot_hits Total cache hits")
    lines.append("# TYPE citrixadc_cache_tot_hits counter")
    lines.append(f"citrixadc_cache_tot_hits {metrics_data['cache_tot_hits']}")
    lines.append("")

    lines.append("# HELP citrixadc_cache_tot_misses Total cache misses")
    lines.append("# TYPE citrixadc_cache_tot_misses counter")
    lines.append(f"citrixadc_cache_tot_misses {metrics_data['cache_tot_misses']}")
    lines.append("")

    lines.append("# HELP citrixadc_cache_hit_ratio Cache hit ratio")
    lines.append("# TYPE citrixadc_cache_hit_ratio gauge")
    hit_ratio = 0.0
    if metrics_data['cache_tot_requests'] > 0:
        hit_ratio = round((metrics_data['cache_tot_hits'] / metrics_data['cache_tot_requests']) * 100, 2)
    lines.append(f"citrixadc_cache_hit_ratio {hit_ratio}")
    lines.append("")

    lines.append("# HELP citrixadc_cache_bytes_served Total cache bytes served")
    lines.append("# TYPE citrixadc_cache_bytes_served counter")
    lines.append(f"citrixadc_cache_bytes_served {metrics_data['cache_bytes_served']}")
    lines.append("")

    # ========================================================================
    # COMPRESSION METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_compression_tot_requests Total compression requests")
    lines.append("# TYPE citrixadc_compression_tot_requests counter")
    lines.append(f"citrixadc_compression_tot_requests {metrics_data['compression_tot_requests']}")
    lines.append("")

    lines.append("# HELP citrixadc_compression_ratio Compression ratio")
    lines.append("# TYPE citrixadc_compression_ratio gauge")
    lines.append(f"citrixadc_compression_ratio {metrics_data['compression_ratio']}")
    lines.append("")

    lines.append("# HELP citrixadc_compression_bandwidth_savings_bytes Compression bandwidth savings in bytes")
    lines.append("# TYPE citrixadc_compression_bandwidth_savings_bytes counter")
    lines.append(f"citrixadc_compression_bandwidth_savings_bytes {metrics_data['compression_bandwidth_savings']}")
    lines.append("")

    # ========================================================================
    # APPFIREWALL / WAF METRICS
    # ========================================================================

    lines.append("# HELP citrixadc_appfw_tot_violations Total AppFirewall violations")
    lines.append("# TYPE citrixadc_appfw_tot_violations counter")
    lines.append(f"citrixadc_appfw_tot_violations {metrics_data['appfw_tot_violations']}")
    lines.append("")

    lines.append("# HELP citrixadc_appfw_tot_log Total AppFirewall logged events")
    lines.append("# TYPE citrixadc_appfw_tot_log counter")
    lines.append(f"citrixadc_appfw_tot_log {metrics_data['appfw_tot_log']}")
    lines.append("")

    lines.append("# HELP citrixadc_appfw_tot_blocked Total AppFirewall blocked requests")
    lines.append("# TYPE citrixadc_appfw_tot_blocked counter")
    lines.append(f"citrixadc_appfw_tot_blocked {metrics_data['appfw_tot_blocked']}")
    lines.append("")

    lines.append("# HELP citrixadc_appfw_sql_injection_blocked Total SQL injection attacks blocked")
    lines.append("# TYPE citrixadc_appfw_sql_injection_blocked counter")
    lines.append(f"citrixadc_appfw_sql_injection_blocked {metrics_data['appfw_sql_injection_blocked']}")
    lines.append("")

    lines.append("# HELP citrixadc_appfw_xss_blocked Total XSS attacks blocked")
    lines.append("# TYPE citrixadc_appfw_xss_blocked counter")
    lines.append(f"citrixadc_appfw_xss_blocked {metrics_data['appfw_xss_blocked']}")
    lines.append("")

    lines.append("# HELP citrixadc_appfw_csrf_blocked Total CSRF attacks blocked")
    lines.append("# TYPE citrixadc_appfw_csrf_blocked counter")
    lines.append(f"citrixadc_appfw_csrf_blocked {metrics_data['appfw_csrf_blocked']}")
    lines.append("")

    lines.append("# HELP citrixadc_appfw_profile_violations_total Total violations per AppFW profile")
    lines.append("# TYPE citrixadc_appfw_profile_violations_total counter")
    for profile in APPFW_PROFILES:
        pname = profile["name"]
        pdata = metrics_data["appfw_profile"].get(pname, {})
        lines.append(f'citrixadc_appfw_profile_violations_total{{profile_name="{pname}",state="{profile["state"]}"}} {pdata.get("violations_total", 0)}')
    lines.append("")

    return "\n".join(lines)

# Initialize metrics on startup
initialize_metrics()

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/metrics')
def metrics() -> Response:
    """Prometheus metrics endpoint."""
    metrics_output = generate_metrics()
    return Response(metrics_output, mimetype='text/plain; version=0.0.4; charset=utf-8')

@app.route('/health')
def health() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'netscaler-prometheus-simulator'
    }

@app.route('/')
def index() -> str:
    """Root endpoint with information."""
    return """
    <html>
        <head><title>NetScaler/Citrix ADC Prometheus Metrics Simulator</title></head>
        <body>
            <h1>NetScaler/Citrix ADC Prometheus Metrics Simulator</h1>
            <p>A comprehensive Prometheus metrics endpoint for testing Grafana dashboards.</p>
            <ul>
                <li><a href="/metrics">Prometheus Metrics</a></li>
                <li><a href="/health">Health Check</a></li>
                <li><a href="/api/v1/query?query=citrixadc_cpu_usage_percent">API Query Example</a></li>
            </ul>
            <p>Metrics are automatically updated every 5 seconds with realistic simulation.</p>
            <p>All metrics use the citrixadc_ prefix matching the official Citrix ADC exporter.</p>
        </body>
    </html>
    """

@app.route('/api/v1/query', methods=['GET', 'POST'])
def prometheus_query() -> Any:
    """Prometheus query API endpoint for Grafana compatibility."""
    # Support both GET and POST
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        query = data.get('query', '') or request.args.get('query', '')
    else:
        query = request.args.get('query', '')

    if not query:
        return jsonify({'status': 'error', 'errorType': 'bad_data', 'error': 'query parameter required'}), 400

    # Simple query evaluation (for basic compatibility)
    timestamp = time.time()

    # Return mock result
    return jsonify({
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': [{
                'metric': {'__name__': query},
                'value': [timestamp, str(random.uniform(0, 100))]
            }]
        }
    })

@app.route('/api/v1/query_range', methods=['GET', 'POST'])
def prometheus_query_range() -> Any:
    """Prometheus query_range API endpoint for Grafana compatibility."""
    # Support both GET and POST
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        query = data.get('query', '') or request.args.get('query', '')
        start = float(data.get('start', request.args.get('start', time.time() - 3600)))
        end = float(data.get('end', request.args.get('end', time.time())))
        step = float(data.get('step', request.args.get('step', 15)))
    else:
        query = request.args.get('query', '')
        start = float(request.args.get('start', time.time() - 3600))
        end = float(request.args.get('end', time.time()))
        step = float(request.args.get('step', 15))

    if not query:
        return jsonify({'status': 'error', 'errorType': 'bad_data', 'error': 'query parameter required'}), 400

    # Generate time series data
    values = []
    current_time = start
    while current_time <= end:
        values.append([current_time, str(random.uniform(0, 100))])
        current_time += step

    return jsonify({
        'status': 'success',
        'data': {
            'resultType': 'matrix',
            'result': [{
                'metric': {'__name__': query},
                'values': values
            }]
        }
    })

@app.route('/api/v1/labels', methods=['GET'])
def prometheus_labels() -> Any:
    """Prometheus labels API endpoint."""
    labels = ['name', 'type', 'state', 'ip', 'port', 'core', 'certkey', 'id', 'alias',
              'servicegroup_name', 'service_type', 'server_name', 'node', 'domain', 'profile_name']

    return jsonify({
        'status': 'success',
        'data': sorted(labels)
    })

@app.route('/api/v1/label/__name__/values', methods=['GET'])
def prometheus_metric_names() -> Any:
    """Prometheus metric names API endpoint."""
    # Return a sample of metric names
    metric_names = [
        'citrixadc_cpu_usage_percent',
        'citrixadc_memory_usage_percent',
        'citrixadc_lb_requests_total',
        'citrixadc_lb_responses_total',
        'citrixadc_service_throughput',
        'citrixadc_ssl_tot_sessions',
        'citrixadc_http_tot_requests',
        'citrixadc_tcp_tot_rx_bytes',
    ]

    return jsonify({
        'status': 'success',
        'data': sorted(metric_names)
    })

@app.route('/api/v1/label/<label_name>/values', methods=['GET'])
def prometheus_label_values(label_name: str) -> Any:
    """Prometheus label values API endpoint."""
    values = []

    if label_name == 'name':
        values = [vs['name'] for vs in LB_VSERVERS] + [vs['name'] for vs in CS_VSERVERS]
    elif label_name == 'type':
        values = ['HTTP', 'SSL', 'TCP']
    elif label_name == 'state':
        values = ['UP', 'DOWN', 'ENABLED']

    return jsonify({
        'status': 'success',
        'data': sorted(list(set(values)))
    })

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # Start background metrics update thread
    update_thread = threading.Thread(target=update_metrics, daemon=True)
    update_thread.start()

    print("=" * 80)
    print("NetScaler/Citrix ADC Prometheus Metrics Simulator")
    print("=" * 80)
    print(f"Metrics endpoint: http://localhost:8000/metrics")
    print(f"Health check: http://localhost:8000/health")
    print(f"Home page: http://localhost:8000/")
    print("=" * 80)
    print("Metrics update every 5 seconds with realistic simulation")
    print("Press Ctrl+C to stop")
    print("=" * 80)

    # Run Flask app
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)
