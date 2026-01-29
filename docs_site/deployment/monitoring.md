# Monitoring and Observability Guide

Comprehensive guide to monitoring, metrics, logging, and alerting for the FastAPI HTTP/WebSocket application.

## Table of Contents

- [Overview](#overview)
- [Metrics Collection](#metrics-collection)
- [Grafana Dashboards](#grafana-dashboards)
- [Prometheus Alerts](#prometheus-alerts)
- [Log Aggregation](#log-aggregation)
- [Distributed Tracing](#distributed-tracing)
- [Performance Monitoring](#performance-monitoring)

## Overview

### Monitoring Stack

```
┌─────────────────────────────────────────────┐
│         Application Components              │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  │
│  │ FastAPI │  │ Keycloak │  │ Traefik  │  │
│  │  :8000  │  │  :9000   │  │  :8080   │  │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  │
│       │            │             │         │
│       └────────────┴─────────────┘         │
│              Metrics (/metrics)            │
└───────────────────┬─────────────────────────┘
                    │
            ┌───────▼────────┐
            │   Prometheus   │  (Metrics DB)
            │     :9090      │
            └───────┬────────┘
                    │
            ┌───────▼────────┐
            │    Grafana     │  (Visualization)
            │     :3000      │
            └────────────────┘

┌─────────────────────────────────────────────┐
│            Application Logs                 │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  │
│  │ FastAPI │  │  Docker  │  │ Traefik  │  │
│  │  logs   │  │   logs   │  │   logs   │  │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  │
│       │            │             │         │
│       └────────────┴─────────────┘         │
│            JSON logs (stdout)              │
└───────────────────┬─────────────────────────┘
                    │
            ┌───────▼────────┐
            │  Grafana Alloy │  (Log collector)
            │    :12345      │
            └───────┬────────┘
                    │
            ┌───────▼────────┐
            │      Loki      │  (Log aggregation)
            │     :3100      │
            └───────┬────────┘
                    │
            ┌───────▼────────┐
            │    Grafana     │  (Log queries)
            │     :3000      │
            └────────────────┘
```

## Metrics Collection

### Application Metrics

The application exposes Prometheus metrics at `/metrics` endpoint.

**Key Metric Types**:

1. **Counters**: Cumulative values (requests, errors)
2. **Gauges**: Point-in-time values (connections, queue size)
3. **Histograms**: Distributions (latency, request size)
4. **Summaries**: Quantiles (percentiles)

### Available Metrics

#### HTTP Metrics

```promql
# Total HTTP requests by method, endpoint, status
http_requests_total{method="GET",endpoint="/authors",status_code="200"}

# Request duration histogram (seconds)
http_request_duration_seconds{method="POST",endpoint="/authors"}

# Percentiles
http_request_duration_seconds{method="GET",endpoint="/authors",quantile="0.99"}

# In-progress requests
http_requests_in_progress{method="GET",endpoint="/authors"}
```

#### WebSocket Metrics

```promql
# Active WebSocket connections
ws_connections_active

# Total connections by status
ws_connections_total{status="accepted"}
ws_connections_total{status="rejected_auth"}
ws_connections_total{status="rejected_limit"}

# Messages received/sent
ws_messages_received_total
ws_messages_sent_total

# Message processing duration by handler
ws_message_processing_duration_seconds{pkg_id="1"}
```

#### Database Metrics

```promql
# Query duration by operation
db_query_duration_seconds{operation="select"}

# Active database connections
db_connections_active

# Database errors
db_errors_total{operation="insert",error_type="integrity_error"}
```

#### Rate Limiting Metrics

```promql
# Rate limit hits by type
rate_limit_hits_total{limit_type="http"}
rate_limit_hits_total{limit_type="websocket_connection"}
rate_limit_hits_total{limit_type="websocket_message"}
```

#### Authentication Metrics

```promql
# Auth attempts by status
auth_attempts_total{status="success"}
auth_attempts_total{status="failed"}
auth_attempts_total{status="token_expired"}

# Token validation
token_validation_total{status="valid"}
token_validation_total{status="invalid"}
```

#### Application Info

```promql
# Application version and environment
app_info{version="1.0.0",python_version="3.11.0",environment="production"}
```

### Traefik Metrics

```promql
# Requests per service
traefik_service_requests_total{service="fastapi@docker"}

# Request duration
traefik_service_request_duration_seconds{service="fastapi@docker"}

# Backend server status
traefik_service_server_up{service="fastapi@docker"}

# Open connections
traefik_service_open_connections{service="fastapi@docker"}
```

### Keycloak Metrics

```promql
# JVM heap memory
jvm_memory_used_bytes{area="heap"}
jvm_memory_max_bytes{area="heap"}

# Garbage collection
jvm_gc_pause_seconds_sum
jvm_gc_pause_seconds_count

# Thread count
jvm_threads_current
jvm_threads_peak
```

### PostgreSQL Metrics

If using PostgreSQL exporter:

```promql
# Database size
pg_database_size_bytes{datname="fastapi_prod"}

# Active connections
pg_stat_database_numbackends{datname="fastapi_prod"}

# Transactions per second
rate(pg_stat_database_xact_commit{datname="fastapi_prod"}[5m])

# Cache hit ratio
pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)
```

### Redis Metrics

If using Redis exporter:

```promql
# Connected clients
redis_connected_clients

# Memory usage
redis_memory_used_bytes
redis_memory_max_bytes

# Commands per second
rate(redis_commands_processed_total[5m])

# Keyspace hits/misses
redis_keyspace_hits_total
redis_keyspace_misses_total

# Hit ratio
redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)
```

## Grafana Dashboards

### Existing Dashboards

The application includes pre-configured Grafana dashboards:

1. **FastAPI Metrics** (`fastapi-metrics.json`)
   - Request rates and latency
   - WebSocket connections
   - Error rates
   - Rate limiting

2. **Traefik Metrics** (`traefik-metrics.json`)
   - Request distribution
   - Backend health
   - Response times
   - Status codes

3. **Keycloak Metrics** (`keycloak-metrics.json`)
   - JVM metrics
   - Memory usage
   - GC activity
   - Thread count

4. **Application Logs** (`application-logs.json`)
   - Log volume
   - Error logs
   - HTTP requests
   - Rate limits

### Accessing Dashboards

```bash
# Access Grafana
https://grafana.example.com

# Login via Keycloak (auto-redirect)

# Dashboards location
Home → Dashboards → Browse

# Or direct URLs
https://grafana.example.com/d/fastapi-metrics
https://grafana.example.com/d/traefik-metrics
https://grafana.example.com/d/keycloak-metrics
https://grafana.example.com/d/application-logs
```

### Creating Custom Dashboards

**Via UI**:
1. Grafana → Dashboards → New Dashboard
2. Add Panel
3. Select Prometheus data source
4. Enter PromQL query
5. Configure visualization
6. Save dashboard

**Via JSON** (recommended for version control):

```json
{
  "dashboard": {
    "title": "Custom Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

Save to `docker/grafana/provisioning/dashboards/custom.json` and set permissions to 644.

## Prometheus Alerts

### Alert Rules Configuration

Create `docker/prometheus/alerts/application.yml`:

```yaml
groups:
  - name: application
    interval: 30s
    rules:
      # High Error Rate
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status_code=~"5.."}[5m])
          / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
          component: fastapi
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # Slow Response Time
      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.99,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 5m
        labels:
          severity: warning
          component: fastapi
        annotations:
          summary: "Slow response time (p99 > 1s)"
          description: "99th percentile latency is {{ $value }}s"

      # WebSocket Connection Limit
      - alert: HighWebSocketConnections
        expr: ws_connections_active > 1000
        for: 5m
        labels:
          severity: warning
          component: fastapi
        annotations:
          summary: "High number of WebSocket connections"
          description: "{{ $value }} active connections (threshold: 1000)"

      # Rate Limit Abuse
      - alert: RateLimitAbuse
        expr: rate(rate_limit_hits_total[5m]) > 100
        for: 5m
        labels:
          severity: warning
          component: fastapi
        annotations:
          summary: "High rate of rate limit hits"
          description: "{{ $value }} rate limit hits per second"

      # Database Connection Pool Exhaustion
      - alert: DatabaseConnectionPoolExhausted
        expr: db_connections_active / db_connections_max > 0.9
        for: 5m
        labels:
          severity: critical
          component: database
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "{{ $value | humanizePercentage }} of connections in use"

  - name: infrastructure
    interval: 30s
    rules:
      # Service Down
      - alert: ServiceDown
        expr: up{job=~"fastapi|keycloak|traefik"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "Service has been down for 1 minute"

      # Database Down
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
          component: database
        annotations:
          summary: "PostgreSQL is down"
          description: "Database has been unreachable for 1 minute"

      # Redis Down
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
          component: redis
        annotations:
          summary: "Redis is down"
          description: "Redis has been unreachable for 1 minute"

      # High Memory Usage
      - alert: HighMemoryUsage
        expr: |
          container_memory_usage_bytes{name="hw-server"}
          / container_spec_memory_limit_bytes{name="hw-server"} > 0.9
        for: 5m
        labels:
          severity: warning
          component: fastapi
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      # High CPU Usage
      - alert: HighCPUUsage
        expr: |
          rate(container_cpu_usage_seconds_total{name="hw-server"}[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
          component: fastapi
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value | humanizePercentage }}"

  - name: security
    interval: 30s
    rules:
      # High Failed Login Rate
      - alert: HighFailedLoginRate
        expr: rate(auth_attempts_total{status="failed"}[5m]) > 10
        for: 5m
        labels:
          severity: warning
          component: security
        annotations:
          summary: "High rate of failed login attempts"
          description: "{{ $value }} failed logins per second"

      # Unauthorized Access Attempts
      - alert: UnauthorizedAccessAttempts
        expr: rate(http_requests_total{status_code="403"}[5m]) > 5
        for: 5m
        labels:
          severity: warning
          component: security
        annotations:
          summary: "High rate of unauthorized access attempts"
          description: "{{ $value }} 403 responses per second"
```

### Alert Manager Configuration

Create `docker/prometheus/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true

    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'ops@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: 'password'

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/XXX/YYY/ZZZ'
        channel: '#alerts'
        title: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
        description: '{{ .GroupLabels.alertname }}'
```

### Testing Alerts

```bash
# Trigger high error rate alert
for i in {1..1000}; do
  curl -X POST https://api.example.com/nonexistent
done

# Trigger slow response alert
# (Requires endpoint that sleeps)

# Check alert status
https://prometheus.example.com/alerts

# Check AlertManager
https://alertmanager.example.com
```

## Log Aggregation

### Structured Logging

The application uses structured JSON logging (see `app/logging.py`).

**Log Format**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "app.api.http.author",
  "message": "Author created successfully",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "endpoint": "/authors",
  "method": "POST",
  "status_code": 201,
  "duration_ms": 45.2,
  "environment": "production"
}
```

### LogQL Queries

**Common Queries**:

```logql
# Recent error logs
{service="shell"} | json | level="ERROR"

# Logs for specific user
{service="shell"} | json | user_id="user123"

# HTTP requests to specific endpoint
{service="shell"} | json | endpoint=~"/api/authors.*"

# Failed authentication attempts
{service="shell"} | json | logger=~"app.auth.*" |~ "(?i)(error|failed|invalid)"

# Rate limit violations
{service="shell"} | json |~ "(?i)(rate limit|too many requests)"

# WebSocket logs
{service="shell"} | json | logger=~"app.api.ws.*"

# Slow operations (> 100ms)
{service="shell"} | json | duration_ms > 100

# Correlate by request ID
{service="shell"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"

# Error rate over time
rate({service="shell"} | json | level="ERROR"[5m])

# Top 10 error messages
topk(10, sum by (message) (count_over_time({service="shell"} | json | level="ERROR"[1h])))
```

### Log Retention

Configure in `docker/loki/loki-config.yml`:

```yaml
limits_config:
  retention_period: 744h  # 31 days

table_manager:
  retention_deletes_enabled: true
  retention_period: 744h
```

## Distributed Tracing

### Correlation ID Tracing (Built-in)

The application uses **correlation IDs** for distributed tracing without requiring OpenTelemetry. This provides equivalent functionality for monolithic services and simple microservices architectures.

**How It Works:**

1. **X-Correlation-ID Header**: Automatically added to all requests (8-char UUID)
2. **Request Propagation**: Correlation ID flows through entire request lifecycle
3. **Structured Logging**: All logs include `request_id` field
4. **Audit Logs**: Database records include `request_id` column
5. **Grafana Queries**: Filter logs by correlation ID for request tracing

**Architecture:**

```
Client Request
    │
    ├─> X-Correlation-ID: abc12345
    │
    v
┌─────────────────────────────────┐
│  CorrelationIDMiddleware        │
│  - Extract/generate correlation │
│  - Store in request.state       │
│  - Set context variable         │
└─────────────┬───────────────────┘
              │
              ├─> HTTP Handler
              │   └─> logger.info("...", extra={"request_id": "abc12345"})
              │
              ├─> WebSocket Handler
              │   └─> RequestModel(req_id="abc12345")
              │
              ├─> Database Query
              │   └─> audit_log(request_id="abc12345")
              │
              └─> Response
                  └─> X-Correlation-ID: abc12345
```

**Accessing Correlation ID:**

```python
from app.middlewares.correlation_id import get_correlation_id

# In any handler or middleware
correlation_id = get_correlation_id()
logger.info(f"Processing request {correlation_id}")

# Automatically included in structured logs
logger.info("User action", extra={
    "user_id": "123",
    "action": "create_author"
})
# Output: {"request_id": "abc12345", "user_id": "123", "action": "create_author", ...}
```

**Tracing Request Flow in Grafana:**

```logql
# 1. Find request by correlation ID
{service="shell"} | json | request_id="abc12345"

# 2. Trace complete request lifecycle
{service="shell"} | json | request_id="abc12345"
  | line_format "{{.timestamp}} [{{.level}}] {{.logger}}: {{.message}}"

# 3. Filter by specific component
{service="shell"} | json | request_id="abc12345" | logger=~"app.api.*"

# 4. Show error logs only
{service="shell"} | json | request_id="abc12345" | level="ERROR"

# 5. Correlate with audit logs (PostgreSQL dashboard)
SELECT * FROM user_actions WHERE request_id = 'abc12345' ORDER BY timestamp;
```

**Example: Tracing Failed Request**

**1. Find error in logs:**
```logql
{service="shell"} | json | level="ERROR" |~ "Author not found"
```

**2. Extract correlation ID from error log:**
```json
{
  "timestamp": "2025-01-29T10:15:30Z",
  "level": "ERROR",
  "request_id": "abc12345",
  "message": "Author not found: id=999"
}
```

**3. Trace complete request flow:**
```logql
{service="shell"} | json | request_id="abc12345"
```

**Output:**
```
10:15:29 [INFO] app.middlewares.correlation_id: Request received
10:15:29 [INFO] app.auth: User authenticated: user_id=u123
10:15:29 [INFO] app.api.http.author: GET /authors/999
10:15:29 [DEBUG] app.repositories.author: Query: SELECT * FROM authors WHERE id=999
10:15:30 [ERROR] app.api.http.author: Author not found: id=999
10:15:30 [INFO] app.middlewares.audit: Audit log created: outcome=error
```

**4. Check audit log in PostgreSQL:**
```sql
SELECT timestamp, username, action_type, resource, outcome, error_message
FROM user_actions
WHERE request_id = 'abc12345';
```

**Cross-Service Tracing:**

For microservices, propagate correlation ID via HTTP headers:

```python
# Service A: Extract correlation ID
from app.middlewares.correlation_id import get_correlation_id

async def call_service_b():
    correlation_id = get_correlation_id()

    # Pass to downstream service
    response = await httpx.get(
        "http://service-b/api/resource",
        headers={"X-Correlation-ID": correlation_id}
    )

    return response

# Service B: Receives same correlation ID
# CorrelationIDMiddleware extracts it automatically
# All logs in Service B will have same request_id
```

**Correlation ID vs OpenTelemetry:**

| Feature | Correlation ID | OpenTelemetry |
|---------|----------------|---------------|
| Request tracing | ✅ Via logs | ✅ Via spans |
| Cross-service tracking | ✅ Via headers | ✅ Via context propagation |
| Timeline visualization | ❌ Logs only | ✅ Jaeger UI |
| Span-level timing | ❌ | ✅ |
| Implementation complexity | Low | High |
| Dependencies | None | Jaeger, OTLP exporter |
| Best for | Monolithic services | Microservices |

**When to Use OpenTelemetry:**

Consider OpenTelemetry if:
- Running complex microservices architecture (5+ services)
- Need span-level timing within handlers
- Want visualized trace graphs (Jaeger UI)
- Require standard instrumentation across polyglot services

**OpenTelemetry Integration (Optional):**

If you need OpenTelemetry for advanced tracing:

```python
# app/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def setup_tracing():
    """Configure OpenTelemetry tracing."""
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    )

    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    return tracer

# Usage in request handler
from app.tracing import tracer

@router.post("/authors")
async def create_author(data: CreateAuthorInput):
    with tracer.start_as_current_span("create_author"):
        # Your code here
        pass
```

**Best Practice:** Start with correlation IDs. Add OpenTelemetry only when scaling to complex microservices.

## Performance Monitoring

### Key Performance Indicators (KPIs)

| Metric | Target | Critical |
|--------|--------|----------|
| Response Time (p99) | < 500ms | > 1s |
| Error Rate | < 1% | > 5% |
| Availability | > 99.9% | < 99% |
| WebSocket Connections | < 5000 | > 10000 |
| Database Connections | < 80% | > 95% |
| CPU Usage | < 70% | > 90% |
| Memory Usage | < 80% | > 95% |

### Performance Queries

```promql
# Average response time by endpoint
avg(rate(http_request_duration_seconds_sum[5m]))
by (endpoint)
/
avg(rate(http_request_duration_seconds_count[5m]))
by (endpoint)

# Request throughput (req/s)
rate(http_requests_total[5m])

# Error rate percentage
rate(http_requests_total{status_code=~"5.."}[5m])
/
rate(http_requests_total[5m]) * 100

# Apdex score (Application Performance Index)
# Target: 100ms, Tolerating: 400ms
(
  sum(rate(http_request_duration_seconds_bucket{le="0.1"}[5m]))
  + sum(rate(http_request_duration_seconds_bucket{le="0.4"}[5m])) / 2
)
/
sum(rate(http_request_duration_seconds_count[5m]))
```

### Load Testing

Use tools like Locust or k6:

```python
# locustfile.py
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_authors(self):
        self.client.get("/authors")

    @task(1)
    def create_author(self):
        self.client.post("/authors", json={
            "name": "Test Author",
            "bio": "Test bio"
        })

# Run load test
locust -f locustfile.py --host=https://api.example.com
```

## Best Practices

### Monitoring Checklist

- [ ] All services expose /metrics endpoint
- [ ] Prometheus scraping all targets
- [ ] Grafana dashboards configured
- [ ] Alert rules defined
- [ ] AlertManager configured with receivers
- [ ] Log aggregation working (Loki)
- [ ] Structured JSON logging enabled
- [ ] Retention policies configured
- [ ] Performance baselines established
- [ ] On-call rotation defined

### Alert Best Practices

1. **Actionable**: Every alert should require action
2. **Clear**: Descriptions should explain what's wrong
3. **Prioritized**: Use severity levels (critical, warning, info)
4. **Tested**: Test alerts before deploying
5. **Documented**: Runbooks for each alert

### Dashboard Best Practices

1. **Overview first**: Start with high-level metrics
2. **Drill-down**: Link to detailed views
3. **Time range**: Include time range selector
4. **Variables**: Use template variables for filtering
5. **Auto-refresh**: Enable for real-time monitoring

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [LogQL Tutorial](https://grafana.com/docs/loki/latest/logql/)
