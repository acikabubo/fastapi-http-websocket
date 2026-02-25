# Metrics Testing Guide

This guide explains how to smoke-test the Prometheus + Grafana observability
stack before merging to `main`.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Service URLs](#service-urls)
- [Quick Start](#quick-start)
- [Phase 1 — Scrape Target Verification](#phase-1--scrape-target-verification)
- [Phase 2 — Traffic Generation](#phase-2--traffic-generation)
- [Phase 3 — PromQL Assertions](#phase-3--promql-assertions)
- [Phase 3b — Redis Error Metric Test (optional)](#phase-3b--redis-error-metric-test-optional)
- [Manual Verification in Grafana](#manual-verification-in-grafana)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

---

## Prerequisites

- Full Docker stack is running (`make start`)
- `curl` and `python3` are available on the host
- `make` is available

---

## Service URLs

| Service    | URL                          | Auth         |
|------------|------------------------------|--------------|
| FastAPI    | http://api.localhost         | —            |
| Prometheus | http://prometheus.localhost  | admin / admin |
| Grafana    | http://grafana.localhost     | Keycloak SSO (or admin / admin) |
| Loki       | http://loki.localhost        | admin / admin |
| Alloy UI   | http://alloy.localhost       | admin / admin |

> Prometheus, Loki, and Alloy are protected by HTTP BasicAuth via Traefik's
> `observability-auth` middleware.  Credentials are stored in
> `docker/traefik/dynamic/.htpasswd` (default: `admin` / `admin`).

---

## Quick Start

```bash
# Start the full stack (if not already running)
make start

# Run the full smoke-test (phases 1–3, waits 70s for first scrape)
make test-metrics

# Re-run without waiting (stack already warm)
bash scripts/test_metrics.sh --no-wait

# Only generate traffic (Phase 2)
bash scripts/test_metrics.sh --traffic-only

# Only run checks (Phases 1 & 3, no traffic)
bash scripts/test_metrics.sh --check-only

# Full run + Redis error metric test (Phase 3b)
make test-metrics-redis
```

---

## Phase 1 — Scrape Target Verification

The script checks two things:

**1. Prometheus targets are UP**

Queries `GET /api/v1/targets` and asserts each job reports `health: "up"`:

| Job | Target |
|-----|--------|
| `fastapi-app` | `hw-server:8000/metrics` |
| `keycloak` | `hw-keycloak:9000/metrics` |
| `traefik` | `traefik:8080/metrics` |

You can verify this manually at http://prometheus.localhost/targets (log in with `admin` / `admin`).

**2. `/metrics` endpoint content**

Hits `GET /metrics` directly and verifies:

- Response contains `# HELP` lines (valid Prometheus text format)
- The following metric families are registered:

| Metric family | What it tracks |
|---|---|
| `http_requests_total` | HTTP request counter by method, endpoint, status |
| `http_request_duration_seconds` | Request latency histogram |
| `websocket_connections_active` | Current active WS connections |
| `redis_operations_total` | Redis operations by name and status |
| `circuit_breaker_state` | Circuit breaker open/closed/half-open state |
| `token_cache_hits_total` | JWT token cache hit counter |
| `redis_pool_connections_in_use` | Redis pool usage gauge |

---

## Phase 2 — Traffic Generation

The script sends requests to populate metrics before Prometheus scrapes:

| Batch | Count | Path | Purpose |
|-------|-------|------|---------|
| Sequential | 60 | `GET /health` | Populate `http_requests_total{status_code="200"}` |
| Sequential | 30 | `GET /nonexistent` | Populate `http_requests_total{status_code="404"}` |
| Sequential | 10 | `GET /metrics` | Self-populate the metrics counter |
| Parallel burst | 20 | `GET /health` | Exercise `http_requests_in_progress` gauge |

After traffic generation the script waits 70 seconds for Prometheus to complete
a scrape cycle (`scrape_interval` for `fastapi-app` is 60s).

Skip the wait with `--no-wait` when the stack has been running for a while and
Prometheus has already scraped recent data.

---

## Phase 3 — PromQL Assertions

The script runs PromQL queries against the Prometheus HTTP API and asserts
each returns at least one series with a non-zero value (or that the series
exists, for gauges that may legitimately be zero).

### HTTP metrics

| Check | PromQL |
|---|---|
| Request counter is non-zero | `http_requests_total` |
| Request rate is non-zero | `rate(http_requests_total[5m])` |
| p95 latency histogram exists | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` |
| 2xx series exist | `http_requests_total{status_code=~"2.."}` |
| 4xx series exist | `http_requests_total{status_code=~"4.."}` |

### WebSocket metrics

| Check | PromQL |
|---|---|
| Active connections gauge exists | `websocket_connections_active` |
| Total connections counter exists | `websocket_connections_total` |

### Redis metrics

| Check | PromQL |
|---|---|
| Pool connections in use | `redis_pool_connections_in_use` |
| Pool connections available | `redis_pool_connections_available` |
| Pool max connections | `redis_pool_max_connections` |
| Operations counter (all statuses) | `redis_operations_total` |

### Token cache metrics

| Check | PromQL |
|---|---|
| Cache hits counter | `token_cache_hits_total` |
| Cache misses counter | `token_cache_misses_total` |

### Circuit breaker metrics

| Check | PromQL |
|---|---|
| State gauge (redis service) | `circuit_breaker_state{service="redis"}` |
| Failure counter | `circuit_breaker_failures_total` |

### Memory cache metrics (CacheManager L1)

| Check | PromQL |
|---|---|
| Cache hits counter | `memory_cache_hits_total` |
| Cache misses counter | `memory_cache_misses_total` |
| Cache size gauge | `memory_cache_size` |

### Application info

| Check | PromQL |
|---|---|
| Version label gauge | `app_info` |

### Alert rules

Queries `GET /api/v1/rules` and verifies the total rule count is > 0, then
checks these key alerts are defined:

- `HighErrorRate`
- `RedisDown`
- `CircuitBreakerOpen`
- `HighAuthFailureRate`

Full alert list is in `docker/prometheus/alerts.yml`.

### Grafana dashboards

Queries `GET /api/search` and verifies dashboards containing these titles are
provisioned:

- `FastAPI` (from `docker/grafana/provisioning/dashboards/fastapi-metrics.json`)
- `Keycloak` (from `keycloak-metrics.json`)
- `Traefik` (from `traefik-metrics.json`)

---

## Phase 3b — Redis Error Metric Test (optional)

Run with `--redis-error-test` or `make test-metrics-redis`.

This phase verifies that the `@redis_safe` decorator (added in #175) correctly
increments `redis_operations_total{status="error"}` when Redis is unavailable.

Steps performed:

1. Stop `hw-redis` container
2. Send 10 requests to the app (internal Redis operations fail, decorator catches them)
3. Restart `hw-redis`
4. Wait 70s for Prometheus to scrape
5. Assert `redis_operations_total{status="error"}` is non-zero

> **Note:** This briefly stops Redis. Do not run in a shared/production
> environment. It is safe for local development — the app fails open for
> non-critical operations and the container restarts automatically.

---

## Manual Verification in Grafana

After the script passes, open Grafana and verify the pre-provisioned dashboards
visually.

### FastAPI Metrics dashboard

Expected panels with data after traffic generation:

- **HTTP Request Rate** — should show ~1–2 req/s during traffic phase
- **HTTP Request Duration (p50/p95)** — latency histogram populated
- **Redis Operation Rate** — low but non-zero
- **Circuit Breaker State** — should show `0` (closed / healthy)
- **Token Cache Hit Rate** — may be 0 if no authenticated requests were made
- **Application Info** — shows version, environment, Python version labels

### Prometheus Alerts

Open http://prometheus.localhost/alerts to see alert states.  All alerts
should be in **Inactive** state on a healthy stack.

---

## Troubleshooting

### `make test-metrics` fails immediately with "FastAPI app not reachable"

```bash
make start          # start the full stack
# wait ~30s for services to become healthy
make test-metrics
```

### Prometheus target shows `DOWN`

```bash
# Check container logs
docker logs hw-server
docker logs hw-prometheus

# Verify /metrics is reachable from inside the Docker network
docker exec hw-prometheus wget -qO- http://hw-server:8000/metrics | head -5
```

### Grafana dashboard check warns "Could not retrieve dashboards"

The Grafana API check uses `admin:admin` credentials.  If Keycloak SSO
auto-login is enabled, the local admin password may differ.  Open Grafana
in a browser instead and log in via Keycloak.

### Phase 3 PromQL checks fail after `--no-wait`

Prometheus scrapes `fastapi-app` every **60 seconds**.  If the stack just
started or traffic was just generated, wait at least 70s before running checks:

```bash
bash scripts/test_metrics.sh --check-only   # uses default 70s wait
```

### `redis_operations_total{status="error"}` never increments

The metric is only recorded when a `@redis_safe`-decorated function catches an
exception.  Normal operation produces no error labels.  Use `--redis-error-test`
to force errors:

```bash
bash scripts/test_metrics.sh --check-only --redis-error-test
```

---

## Related Documentation

- [Monitoring Guide](monitoring-guide.md) — Prometheus metrics reference, alert rules, Grafana dashboards
- [Testing Guide](testing-guide.md) — Unit, integration, load, and chaos tests
- [Development Guide](development-guide.md) — Running the application, Docker commands
- `scripts/test_metrics.sh` — The automated smoke-test script
- `docker/prometheus/alerts.yml` — All alert rule definitions
- `docker/grafana/provisioning/dashboards/` — Pre-provisioned Grafana dashboards
