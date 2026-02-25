#!/usr/bin/env bash
# =============================================================================
# test_metrics.sh — Smoke-test Prometheus + Grafana observability stack
#
# Automates phases 1–3 of the metrics testing plan:
#   Phase 1: Verify scrape targets are UP
#   Phase 2: Generate traffic to populate metrics
#   Phase 3: Verify specific PromQL queries return data
#
# Usage:
#   ./scripts/test_metrics.sh [options]
#
# Options:
#   --app-url URL       FastAPI base URL       (default: http://localhost:8000)
#   --prom-url URL      Prometheus base URL    (default: http://localhost:9090)
#   --grafana-url URL   Grafana base URL       (default: http://localhost:3000)
#   --wait N            Seconds to wait for first scrape  (default: 70)
#   --no-wait           Skip initial scrape wait (use if stack is already warm)
#   --traffic-only      Only run Phase 2 (traffic generation)
#   --check-only        Only run Phases 1 & 3 (no traffic generation)
#   --redis-error-test  Also run Phase 3b: stop Redis briefly to trigger
#                       redis_operations_total{status="error"} metric
#   -h, --help          Show this help message
# =============================================================================

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
APP_URL="http://api.localhost"
PROM_URL="http://prometheus.localhost"
GRAFANA_URL="http://grafana.localhost"
WAIT_SECONDS=70
DO_WAIT=true
DO_TRAFFIC=true
DO_CHECKS=true
DO_REDIS_ERROR_TEST=false

PASS=0
FAIL=0
WARN=0

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo -e "${BOLD}[$(date +%H:%M:%S)]${RESET} $*"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $*"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${RESET} $*"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}⚠${RESET} $*"; ((WARN++)); }
info() { echo -e "  ${CYAN}ℹ${RESET} $*"; }

prom_query() {
    # Usage: prom_query "PromQL expression"
    # Returns raw result JSON
    local expr="$1"
    curl -sf "${PROM_URL}/api/v1/query" \
        --data-urlencode "query=${expr}" \
        2>/dev/null
}

prom_has_data() {
    # Returns 0 (true) if the query returns at least one non-empty result
    local expr="$1"
    local result
    result=$(prom_query "$expr")
    local count
    count=$(echo "$result" | python3 -c "
import json, sys
d = json.load(sys.stdin)
results = d.get('data', {}).get('result', [])
# Filter out results where value is 0 or NaN
non_zero = [r for r in results if r.get('value') and float(r['value'][1]) != 0]
print(len(non_zero))
" 2>/dev/null || echo "0")
    [[ "$count" -gt 0 ]]
}

prom_value() {
    # Print the first scalar value from a query result
    local expr="$1"
    prom_query "$expr" | python3 -c "
import json, sys
d = json.load(sys.stdin)
results = d.get('data', {}).get('result', [])
if results:
    print(results[0]['value'][1])
else:
    print('no_data')
" 2>/dev/null
}

check_metric() {
    # check_metric "description" "PromQL"
    local desc="$1"
    local expr="$2"
    if prom_has_data "$expr"; then
        local val
        val=$(prom_value "$expr")
        ok "${desc} (${val})"
    else
        fail "${desc} — no data for: ${expr}"
    fi
}

check_metric_exists() {
    # check_metric_exists "description" "PromQL" — passes even if value is 0,
    # just needs the series to exist in Prometheus
    local desc="$1"
    local expr="$2"
    local result
    result=$(prom_query "$expr")
    local count
    count=$(echo "$result" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(len(d.get('data', {}).get('result', [])))
" 2>/dev/null || echo "0")
    if [[ "$count" -gt 0 ]]; then
        local val
        val=$(prom_value "$expr")
        ok "${desc} (${val})"
    else
        fail "${desc} — series not found: ${expr}"
    fi
}

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --app-url)     APP_URL="$2";    shift 2 ;;
        --prom-url)    PROM_URL="$2";   shift 2 ;;
        --grafana-url) GRAFANA_URL="$2"; shift 2 ;;
        --wait)        WAIT_SECONDS="$2"; shift 2 ;;
        --no-wait)     DO_WAIT=false;   shift ;;
        --traffic-only) DO_CHECKS=false; DO_WAIT=false; shift ;;
        --check-only)  DO_TRAFFIC=false; DO_WAIT=false; shift ;;
        --redis-error-test) DO_REDIS_ERROR_TEST=true; shift ;;
        -h|--help)
            sed -n '/^# ====/,/^# ====/p' "$0" | sed 's/^# \{0,2\}//' | sed 's/^#$//'
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Prometheus + Grafana Observability Smoke Test         ${RESET}"
echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
echo ""
info "App:        ${APP_URL}"
info "Prometheus: ${PROM_URL}"
info "Grafana:    ${GRAFANA_URL}"
echo ""

# ── Pre-flight: check services are reachable ──────────────────────────────────
log "Pre-flight: checking service reachability..."

if curl -sf "${APP_URL}/health" > /dev/null 2>&1; then
    ok "FastAPI app is reachable (${APP_URL}/health)"
else
    fail "FastAPI app not reachable at ${APP_URL}/health — is the stack running? (make start)"
    echo ""
    echo -e "${RED}Aborting: start the stack first with 'make start'${RESET}"
    exit 1
fi

if curl -sf "${PROM_URL}/-/healthy" > /dev/null 2>&1; then
    ok "Prometheus is reachable"
else
    fail "Prometheus not reachable at ${PROM_URL}"
    exit 1
fi

if curl -sf "${GRAFANA_URL}/api/health" > /dev/null 2>&1; then
    ok "Grafana is reachable"
else
    warn "Grafana not reachable at ${GRAFANA_URL} (non-fatal)"
fi

echo ""

# ── Phase 1: Verify scrape targets ───────────────────────────────────────────
if $DO_CHECKS; then
    log "${BOLD}Phase 1${RESET} — Verifying Prometheus scrape targets..."
    echo ""

    TARGETS_JSON=$(curl -sf "${PROM_URL}/api/v1/targets" 2>/dev/null)

    for job in "fastapi-app" "keycloak" "traefik"; do
        state=$(echo "$TARGETS_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
targets = d.get('data', {}).get('activeTargets', [])
for t in targets:
    if t.get('labels', {}).get('job') == '${job}':
        print(t.get('health', 'unknown'))
        break
else:
    print('not_found')
" 2>/dev/null)
        if [[ "$state" == "up" ]]; then
            ok "Scrape target '${job}' is UP"
        elif [[ "$state" == "not_found" ]]; then
            warn "Scrape target '${job}' not found in active targets"
        else
            fail "Scrape target '${job}' is ${state}"
        fi
    done

    echo ""

    # Verify /metrics endpoint returns Prometheus-format text
    log "Verifying /metrics endpoint content..."
    METRICS_BODY=$(curl -sf "${APP_URL}/metrics" 2>/dev/null)
    if echo "$METRICS_BODY" | grep -q "^# HELP"; then
        ok "/metrics returns valid Prometheus text format"
    else
        fail "/metrics did not return expected '# HELP' lines"
    fi

    # Check a few expected metric families are present
    for metric in \
        "http_requests_total" \
        "http_request_duration_seconds" \
        "websocket_connections_active" \
        "redis_operations_total" \
        "circuit_breaker_state" \
        "token_cache_hits_total" \
        "redis_pool_connections_in_use"; do
        if echo "$METRICS_BODY" | grep -q "^# HELP ${metric}"; then
            ok "Metric family '${metric}' is registered"
        else
            fail "Metric family '${metric}' missing from /metrics output"
        fi
    done

    echo ""
fi

# ── Phase 2: Generate traffic ─────────────────────────────────────────────────
if $DO_TRAFFIC; then
    log "${BOLD}Phase 2${RESET} — Generating traffic to populate metrics..."
    echo ""

    # 2a: Health checks (2xx, low-latency, populate http_requests_total)
    info "Sending 60 GET /health requests..."
    for i in $(seq 1 60); do
        curl -sf "${APP_URL}/health" > /dev/null 2>&1 || true
    done
    ok "60 × GET /health sent"

    # 2b: 404 requests (populate 4xx error rate)
    info "Sending 30 requests to a non-existent path (→ 404)..."
    for i in $(seq 1 30); do
        curl -sf "${APP_URL}/this-path-does-not-exist-metrics-test" \
            > /dev/null 2>&1 || true
    done
    ok "30 × GET /nonexistent sent (expect 404s)"

    # 2c: /metrics itself (populate its own counter)
    info "Sending 10 GET /metrics requests..."
    for i in $(seq 1 10); do
        curl -sf "${APP_URL}/metrics" > /dev/null 2>&1 || true
    done
    ok "10 × GET /metrics sent"

    # 2d: Concurrent burst — 20 parallel health checks to bump in-progress gauge
    info "Sending 20 parallel requests (burst)..."
    for i in $(seq 1 20); do
        curl -sf "${APP_URL}/health" > /dev/null 2>&1 &
    done
    wait
    ok "20 parallel requests completed"

    echo ""
fi

# ── Wait for Prometheus to scrape ─────────────────────────────────────────────
if $DO_WAIT && $DO_CHECKS; then
    log "Waiting ${WAIT_SECONDS}s for Prometheus to scrape fresh data..."
    info "(scrape_interval for fastapi-app is 60s)"

    for i in $(seq 1 "$WAIT_SECONDS"); do
        printf "\r  ${CYAN}⏳${RESET} %d/%d seconds..." "$i" "$WAIT_SECONDS"
        sleep 1
    done
    echo ""
    echo ""
fi

# ── Phase 3: PromQL checks ────────────────────────────────────────────────────
if $DO_CHECKS; then
    log "${BOLD}Phase 3${RESET} — Verifying PromQL queries return data..."
    echo ""

    # ── HTTP metrics ──────────────────────────────────────────────────────────
    log "HTTP metrics:"
    check_metric \
        "http_requests_total (cumulative counter)" \
        "http_requests_total"
    check_metric \
        "HTTP request rate (5m, non-zero)" \
        "rate(http_requests_total[5m])"
    check_metric_exists \
        "HTTP p95 latency histogram" \
        "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
    check_metric_exists \
        "HTTP 2xx requests exist" \
        'http_requests_total{status_code=~"2.."}'
    check_metric_exists \
        "HTTP 4xx requests exist" \
        'http_requests_total{status_code=~"4.."}'
    echo ""

    # ── WebSocket metrics ─────────────────────────────────────────────────────
    log "WebSocket metrics:"
    check_metric_exists \
        "websocket_connections_active gauge" \
        "websocket_connections_active"
    check_metric_exists \
        "websocket_connections_total counter" \
        "websocket_connections_total"
    echo ""

    # ── Redis metrics ─────────────────────────────────────────────────────────
    log "Redis metrics:"
    check_metric_exists \
        "redis_pool_connections_in_use gauge" \
        "redis_pool_connections_in_use"
    check_metric_exists \
        "redis_pool_connections_available gauge" \
        "redis_pool_connections_available"
    check_metric_exists \
        "redis_pool_max_connections gauge" \
        "redis_pool_max_connections"
    check_metric_exists \
        "redis_operations_total counter (all statuses)" \
        "redis_operations_total"
    echo ""

    # ── Token cache metrics ───────────────────────────────────────────────────
    log "Token cache metrics:"
    check_metric_exists \
        "token_cache_hits_total counter" \
        "token_cache_hits_total"
    check_metric_exists \
        "token_cache_misses_total counter" \
        "token_cache_misses_total"
    echo ""

    # ── Circuit breaker metrics ───────────────────────────────────────────────
    log "Circuit breaker metrics:"
    check_metric_exists \
        "circuit_breaker_state gauge (redis)" \
        'circuit_breaker_state{service="redis"}'
    check_metric_exists \
        "circuit_breaker_failures_total counter" \
        "circuit_breaker_failures_total"
    echo ""

    # ── Memory cache metrics ──────────────────────────────────────────────────
    log "Memory cache metrics:"
    check_metric_exists \
        "memory_cache_hits_total counter" \
        "memory_cache_hits_total"
    check_metric_exists \
        "memory_cache_misses_total counter" \
        "memory_cache_misses_total"
    check_metric_exists \
        "memory_cache_size gauge" \
        "memory_cache_size"
    echo ""

    # ── Application info ──────────────────────────────────────────────────────
    log "Application info:"
    check_metric_exists \
        "app_info gauge (version labels)" \
        "app_info"
    echo ""

    # ── Alerts ────────────────────────────────────────────────────────────────
    log "Alert rules loaded in Prometheus:"
    RULES_JSON=$(curl -sf "${PROM_URL}/api/v1/rules" 2>/dev/null)
    RULE_COUNT=$(echo "$RULES_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
rules = []
for g in d.get('data', {}).get('groups', []):
    rules.extend(g.get('rules', []))
print(len(rules))
" 2>/dev/null || echo "0")
    if [[ "$RULE_COUNT" -gt 0 ]]; then
        ok "${RULE_COUNT} alert rules loaded"
        # Check a selection of key alerts exist
        for alert_name in \
            "HighErrorRate" \
            "RedisDown" \
            "CircuitBreakerOpen" \
            "HighAuthFailureRate"; do
            found=$(echo "$RULES_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for g in d.get('data', {}).get('groups', []):
    for r in g.get('rules', []):
        if r.get('name') == '${alert_name}':
            print('yes')
            sys.exit(0)
print('no')
" 2>/dev/null)
            if [[ "$found" == "yes" ]]; then
                ok "Alert '${alert_name}' is defined"
            else
                fail "Alert '${alert_name}' not found in loaded rules"
            fi
        done
    else
        fail "No alert rules loaded — check docker/prometheus/alerts.yml"
    fi
    echo ""

    # ── Grafana dashboards ────────────────────────────────────────────────────
    log "Grafana provisioned dashboards:"
    DASH_JSON=$(curl -sf \
        -u "admin:admin" \
        "${GRAFANA_URL}/api/search?type=dash-db" 2>/dev/null || echo "{}")
    DASH_COUNT=$(echo "$DASH_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if isinstance(d, list):
    print(len(d))
else:
    print(0)
" 2>/dev/null || echo "0")
    if [[ "$DASH_COUNT" -gt 0 ]]; then
        ok "${DASH_COUNT} dashboards found in Grafana"
        for dash_title in "FastAPI" "Keycloak" "Traefik"; do
            found=$(echo "$DASH_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
titles = [item.get('title','') for item in (d if isinstance(d, list) else [])]
print('yes' if any('${dash_title}' in t for t in titles) else 'no')
" 2>/dev/null)
            if [[ "$found" == "yes" ]]; then
                ok "Dashboard containing '${dash_title}' is provisioned"
            else
                warn "No dashboard with '${dash_title}' in title found"
            fi
        done
    else
        warn "Could not retrieve Grafana dashboards (auth may differ from admin/admin)"
        info "Open ${GRAFANA_URL} manually to verify dashboards are loaded"
    fi
    echo ""
fi

# ── Phase 3b (optional): Redis error metric test ──────────────────────────────
if $DO_REDIS_ERROR_TEST; then
    log "${BOLD}Phase 3b${RESET} — Redis error metric test (stops hw-redis briefly)..."
    echo ""

    if ! command -v docker &> /dev/null; then
        warn "docker not found — skipping Redis error test"
    else
        CONTAINER="hw-redis"
        info "Stopping ${CONTAINER}..."
        docker stop "$CONTAINER" > /dev/null 2>&1 || { warn "Could not stop ${CONTAINER}"; }

        info "Sending 10 requests (Redis operations will fail internally)..."
        for i in $(seq 1 10); do
            curl -sf "${APP_URL}/health" > /dev/null 2>&1 || true
        done

        info "Restarting ${CONTAINER}..."
        docker start "$CONTAINER" > /dev/null 2>&1 || { warn "Could not restart ${CONTAINER}"; }

        info "Waiting 70s for Prometheus to scrape error metrics..."
        for i in $(seq 1 70); do
            printf "\r  ${CYAN}⏳${RESET} %d/70 seconds..." "$i"
            sleep 1
        done
        echo ""

        check_metric \
            "redis_operations_total{status=error} is non-zero after Redis outage" \
            'redis_operations_total{status="error"}'
        echo ""
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Summary${RESET}"
echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${GREEN}Passed:${RESET}   ${PASS}"
echo -e "  ${RED}Failed:${RESET}   ${FAIL}"
echo -e "  ${YELLOW}Warnings:${RESET} ${WARN}"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    echo -e "${RED}${BOLD}RESULT: FAIL${RESET} — ${FAIL} check(s) did not pass."
    echo ""
    echo "Tips:"
    echo "  • Is the full stack running?  →  make start"
    echo "  • Wait 60–90s after startup for first Prometheus scrape"
    echo "  • Re-run with --no-wait if the stack is already warm"
    echo "  • Check Prometheus targets:   →  ${PROM_URL}/targets"
    echo "  • Check app logs:             →  docker logs hw-server"
    exit 1
else
    echo -e "${GREEN}${BOLD}RESULT: PASS${RESET} — all checks passed."
    echo ""
    echo "Next steps:"
    echo "  • Open Grafana dashboards:    →  ${GRAFANA_URL}"
    echo "  • Open Prometheus UI:         →  ${PROM_URL}"
    echo "  • Trigger Redis errors:       →  $0 --check-only --redis-error-test"
    exit 0
fi
