# Monitoring Guide

This guide covers Prometheus metrics, alerting, centralized logging with Loki, and monitoring dashboards.

## Table of Contents

- [Prometheus Metrics](#prometheus-metrics)
- [Monitoring Keycloak](#monitoring-keycloak)
- [Prometheus Alerting](#prometheus-alerting)
- [Centralized Logging with Loki](#centralized-logging-with-loki)
- [Audit Logs Dashboard](#audit-logs-dashboard)
- [Connection Pool Monitoring](#connection-pool-monitoring)
- [Related Documentation](#related-documentation)

## Prometheus Metrics

### Accessing Metrics

- **Metrics endpoint**: `GET /metrics`
- Excluded from authentication and rate limiting
- Returns Prometheus text format

### Key Metrics Available

**HTTP Metrics:**
```
http_requests_total{method,endpoint,status_code}
http_request_duration_seconds{method,endpoint}
http_requests_in_progress{method,endpoint}
```

**WebSocket Metrics:**
```
ws_connections_active
ws_connections_total{status}  # status: accepted, rejected_auth, rejected_limit
ws_messages_received_total
ws_messages_sent_total
ws_message_processing_duration_seconds{pkg_id}
```

**Application Metrics:**
```
app_info{version,python_version,environment}
rate_limit_hits_total{limit_type}
auth_attempts_total{status}
```

**Keycloak Authentication Metrics:**
```
keycloak_auth_attempts_total{status,method}  # status: success/failure/error
keycloak_token_validation_total{status,reason}  # status: valid/invalid/expired/error
keycloak_operation_duration_seconds{operation}  # operation: login/validate_token
auth_backend_requests_total{type,outcome}  # type: http/websocket
```

### Setting up Prometheus (Docker)

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

# prometheus.yml
scrape_configs:
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Custom Metrics

```python
from app.utils.metrics import http_requests_total

# Increment counter
http_requests_total.labels(
    method="POST",
    endpoint="/api/custom",
    status_code=201
).inc()

# Observe histogram
from app.utils.metrics import db_query_duration_seconds
db_query_duration_seconds.labels(operation="select").observe(0.045)
```

**IMPORTANT**: When adding new Prometheus metrics to `app/utils/metrics/`, you must also update the Grafana dashboard at `docker/grafana/provisioning/dashboards/fastapi-metrics.json` to visualize the new metrics.

### Metrics Organization

Metrics are split into logical modules:
- `app/utils/metrics/http.py`: HTTP request metrics
- `app/utils/metrics/websocket.py`: WebSocket connection and message metrics
- `app/utils/metrics/database.py`: Database query and connection metrics
- `app/utils/metrics/redis.py`: Redis operations and pool metrics
- `app/utils/metrics/auth.py`: Authentication and Keycloak metrics
- `app/utils/metrics/audit.py`: Audit logging metrics
- `app/utils/metrics/__init__.py`: Re-exports all metrics

## Monitoring Keycloak

### Keycloak Metrics Endpoint

- **Endpoint**: `http://localhost:9999/metrics` (port 9000 internally, mapped to 9999 externally)
- Enabled via `KC_METRICS_ENABLED=true` in `docker/.kc_env`
- Scraped by Prometheus every 30 seconds

### Available Keycloak Metrics

**HTTP Server Metrics:**
```
http_server_requests_seconds_count - Total HTTP requests
http_server_requests_seconds_sum - Total request duration
http_server_active_requests - Current active requests
http_server_connections_seconds_duration_sum - Connection duration
```

**JVM Metrics:**
```
jvm_memory_used_bytes{area="heap"} - JVM heap memory usage
jvm_memory_max_bytes{area="heap"} - Maximum heap memory
jvm_gc_pause_seconds_sum - Garbage collection pause time
jvm_gc_pause_seconds_count - GC pause count
jvm_threads_current - Current thread count
jvm_threads_peak - Peak thread count
```

**Cache/Session Metrics:**
```
vendor_statistics_hits - Cache hit count by cache type
vendor_statistics_misses - Cache miss count
vendor_statistics_entries - Number of entries in cache
```

### Grafana Dashboard

- **Location**: `docker/grafana/provisioning/dashboards/keycloak-metrics.json`
- Auto-provisioned on Grafana startup
- **Access**: http://localhost:3000/d/keycloak-metrics

**Dashboard Panels:**
1. Active Sessions (Gauge)
2. Login Success/Failure Rate (Time Series)
3. Failed Logins (Last Hour) (Stat)
4. Request Duration Percentiles (Time Series)
5. Request Rate (Time Series)
6. JVM Heap Memory Usage (Time Series)
7. Garbage Collection Pause Time (Time Series)
8. JVM Thread Count (Time Series)
9. Database Connection Pool (Time Series)

## Prometheus Alerting

### Alert Configuration

- **Alert rules file**: `docker/prometheus/alerts.yml`
- Evaluation interval: 30 seconds
- Configured in `docker/prometheus/prometheus.yml` via `rule_files: ['alerts.yml']`
- **Access Prometheus alerts UI**: http://localhost:9090/alerts

### Alert Categories

**1. Application Alerts** (`application_alerts` group):
- `HighErrorRate`: HTTP 5xx error rate > 5% for 2 minutes (warning)
- `CriticalErrorRate`: HTTP 5xx error rate > 20% for 1 minute (critical)
- `HighClientErrorRate`: HTTP 4xx error rate > 30% for 5 minutes (info)
- `SlowResponseTime`: 95th percentile response time > 1s for 5 minutes (warning)

**2. Database Alerts** (`database_alerts` group):
- `DatabaseDown`: PostgreSQL unavailable for > 1 minute (critical)
- `SlowDatabaseQueries`: 95th percentile query duration > 0.5s for 5 minutes (warning)

**3. Redis Alerts** (`redis_alerts` group):
- `RedisDown`: Redis cache unavailable for > 1 minute (critical)

**4. WebSocket Alerts** (`websocket_alerts` group):
- `HighWebSocketRejections`: Rejection rate > 5/s for 3 minutes (warning)
- `HighWebSocketConnections`: Active connections > 1000 for 5 minutes (warning)

**5. Audit Alerts** (`audit_alerts` group):
- `AuditLogDropping`: Audit logs drop rate > 1/s for 2 minutes (critical)
- `HighAuditLogDropRate`: Drop rate > 1% for 2 minutes (warning)
- `SustainedAuditQueueOverflow`: Drop rate > 1% for 5+ minutes (critical - compliance risk)
- `AuditQueueNearCapacity`: Queue usage > 80% for 2 minutes (warning)

**6. Rate Limit Alerts** (`rate_limit_alerts` group):
- `HighRateLimitHits`: Rate limit hit rate > 10/s for 5 minutes (info)

**7. Authentication Alerts** (`authentication_alerts` group):
- `HighAuthFailureRate`: Auth failure rate > 20% for 3 minutes (warning)
- `CriticalAuthFailureRate`: Auth failure rate > 50% for 1 minute (critical - possible attack)
- `HighKeycloakAuthFailureRate`: Keycloak auth failure rate > 20% for 3 minutes (warning)
- `KeycloakAuthErrors`: Keycloak auth errors > 1/s for 2 minutes (critical)

**8. Keycloak Alerts** (`keycloak_alerts` group):
- `KeycloakDown`: Keycloak unavailable for > 1 minute (critical)
- `HighKeycloakMemoryUsage`: JVM heap usage > 85% for 5 minutes (warning)

### Alert Severity Levels

- `critical`: Immediate action required (service down, data loss, security incident)
- `warning`: Requires attention (degraded performance, approaching limits)
- `info`: Informational (unusual but not critical activity)

### Configuring Alert Notifications

To receive alert notifications, configure Alertmanager:

**1. Add Alertmanager to docker-compose.yml:**
```yaml
alertmanager:
  image: prom/alertmanager:latest
  ports:
    - "9093:9093"
  volumes:
    - ./docker/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
  command:
    - '--config.file=/etc/alertmanager/alertmanager.yml'
```

**2. Create `docker/alertmanager/alertmanager.yml`:**
```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-notifications'

receivers:
  - name: 'team-notifications'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@example.com'
        auth_password: 'app_password'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

**3. Update Prometheus configuration:**
```yaml
# docker/prometheus/prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Viewing Alerts

- Prometheus alerts UI: http://localhost:9090/alerts
- Alertmanager UI: http://localhost:9093 (after configuration)
- Grafana dashboards: Alerts are visualized in panels

## Centralized Logging with Loki

### Overview

The application uses structured JSON logging with Grafana Loki for centralized log aggregation.

**Logging Stack:**
- **Structured Logging**: JSON format with contextual fields (`app/logging.py`)
- **Grafana Alloy**: Modern observability collector (replaced deprecated Promtail)
- **Loki**: Centralized log aggregation and storage
- **Grafana**: Log visualization and querying with LogQL

**Architecture:**
Logs flow: Application → stdout (JSON or human-readable) → Grafana Alloy → Loki → Grafana

### Why Grafana Alloy?

- Promtail was deprecated in February 2025 (EOL March 2026)
- Alloy is the unified observability agent supporting logs, metrics, and traces
- Uses modern "River" configuration language
- Better performance and more features than Promtail
- Alloy UI available at http://localhost:12345 for debugging

### Console Log Format

Set via environment variable in `docker/.srv_env`:

```bash
# For development (human-readable) - DEFAULT
LOG_CONSOLE_FORMAT=human

# For production (JSON for Grafana Alloy)
LOG_CONSOLE_FORMAT=json
```

**Important Notes:**
- When `LOG_CONSOLE_FORMAT=human`, Alloy will fail to parse JSON fields (acceptable for local dev)
- When `LOG_CONSOLE_FORMAT=json`, all logs are properly parsed and indexed in Loki
- Error log files (`logs/logging_errors.log`) are always in JSON format
- For production deployments with Grafana monitoring, always use `LOG_CONSOLE_FORMAT=json`

### Available Log Fields

Structured logs automatically include:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `logger`: Python logger name
- `message`: Log message
- `request_id`: Correlation ID from `X-Correlation-ID` header
- `user_id`: Authenticated user ID (if available)
- `endpoint`: HTTP endpoint path
- `method`: HTTP method
- `status_code`: HTTP response status code
- `environment`: Deployment environment (dev, staging, production)
- `module`, `function`, `line`: Code location
- `exception`: Stack trace (for ERROR logs)

### Setting Log Context

```python
from app.logging import logger, set_log_context

# Add custom contextual fields
set_log_context(
    user_id="user123",
    operation="create_author",
    duration_ms=45
)

logger.info("Operation completed")  # Will include user_id, operation, duration_ms
```

### Grafana Dashboards

**1. Application Logs Dashboard** (`application-logs`):
   - **Access**: http://localhost:3000/d/application-logs
   - **Panels**: Log volume, error logs, HTTP requests, WebSocket logs, rate limits, auth failures
   - **Variables**: service, level, user_id, endpoint, method, status_code

**2. FastAPI Metrics Dashboard** (`fastapi-metrics`):
   - Includes log panels for correlating logs with metrics
   - Recent errors, HTTP request logs, rate limit events

### Common LogQL Queries

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

# Logs by HTTP status code
{service="shell"} | json | status_code=~"5.."  # 5xx errors
{service="shell"} | json | status_code="429"   # Rate limit hits

# Slow operations (requires duration_ms field)
{service="shell"} | json | duration_ms > 100

# Permission denied events
{service="shell"} | json |~ "(?i)(permission denied|unauthorized|forbidden)"

# Correlate logs by request ID
{service="shell"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"
```

### Log Filtering Variables

Dashboards support filtering by:
- **service**: Docker service name (shell, hw-db, hw-keycloak)
- **level**: Log level (INFO, WARNING, ERROR)
- **user_id**: Filter by authenticated user (regex)
- **endpoint**: Filter by HTTP endpoint (regex)
- **method**: HTTP method (GET, POST, PUT, PATCH, DELETE)
- **status_code**: HTTP status code (regex)

### Best Practices

1. **Always include context**: Use `set_log_context()` for request-specific fields
2. **Use structured fields**: Add fields as keyword arguments, not in message strings
3. **Log at appropriate levels**:
   - `DEBUG`: Detailed diagnostic info
   - `INFO`: Normal operations, request handling
   - `WARNING`: Unexpected but recoverable issues
   - `ERROR`: Errors requiring attention
4. **Include duration for performance tracking**: Add `duration_ms` field
5. **Correlate with request_id**: Every log includes correlation ID for tracing

## Audit Logs Dashboard

### Overview

The Audit Logs Dashboard provides comprehensive visibility into user activities and security events by querying the `user_actions` table directly from PostgreSQL.

### Accessing the Dashboard

- **Location**: `docker/grafana/provisioning/dashboards/audit-logs.json`
- Auto-provisioned on Grafana startup
- **Access**: http://localhost:3000/d/audit-logs
- **Datasource**: PostgreSQL

### Dashboard Panels

**1. Audit Events Over Time** (Time Series)
   - Shows event volume grouped by outcome (success, error, permission_denied)
   - Color-coded: green (success), red (error), orange (permission_denied)

**2. Actions by Type** (Bar Chart)
   - Horizontal bar chart showing top 20 action types
   - Helps identify most common operations

**3. Top Users by Activity** (Bar Chart)
   - Shows top 15 most active users by event count
   - Displays Keycloak usernames

**4. Recent Audit Events** (Table)
   - Paginated table of last 100 events
   - Columns: timestamp, username, action_type, resource, outcome, response_status, duration_ms, ip_address
   - Color-coded cells for quick visual scanning

**5. Failed/Denied Actions** (Table)
   - Filtered view showing only errors and permission denials
   - Critical for security monitoring and debugging

**6. Average Response Time by Action** (Time Series)
   - Line chart showing avg duration_ms per action type
   - Only includes successful operations

### Dashboard Variables (Filters)

- **Username**: Multi-select dropdown of all usernames in audit log
- **Action Type**: Multi-select filter for action types
- **Outcome**: Multi-select filter for operation outcomes

**Time Range:**
- Default: Last 6 hours
- Configurable via Grafana time picker

### Use Cases

**1. Security Monitoring:**
- Identify unauthorized access attempts
- Track failed operations by user
- Monitor IP addresses for suspicious patterns
- Detect brute force attempts

**2. Compliance and Auditing:**
- Export audit trails for compliance reports
- Track who performed what actions and when
- Correlate actions with outcomes

**3. Performance Analysis:**
- Identify slow operations by action type
- Track response time trends
- Find performance bottlenecks per user or action

**4. Troubleshooting:**
- Filter by username to debug user-specific issues
- Use request_id to trace requests across services
- Analyze error messages for root cause

## Connection Pool Monitoring

### Redis Connection Pool Monitoring

**Locations**: `app/storage/redis.py`, `app/tasks/redis_pool_metrics_task.py`

- Real-time monitoring of Redis connection pool health and usage
- Background task collects pool metrics every 15 seconds

**Prometheus metrics tracked:**
- `redis_pool_max_connections`: Maximum connections allowed per pool
- `redis_pool_connections_in_use`: Current active connections
- `redis_pool_connections_available`: Idle connections ready for use
- `redis_pool_connections_created_total`: Total connections created (cumulative)
- `redis_pool_info`: Pool configuration metadata

**Prometheus alerts:**
- `RedisPoolNearExhaustion`: Pool usage > 80% for 3 minutes (warning)
- `RedisPoolExhausted`: Pool usage ≥ 95% for 1 minute (critical)
- `RedisPoolNoAvailableConnections`: Zero available connections for 1 minute (critical)

**Grafana dashboard panels** (IDs 25-27):
- Panel 25: Connections in use vs max connections (timeseries)
- Panel 26: Available connections over time (timeseries)
- Panel 27: Pool usage percentage gauge (0-100%)

### Database Connection Pool Monitoring

**Locations**: `app/storage/db.py`, `app/tasks/db_pool_metrics_task.py`

- Real-time monitoring of PostgreSQL connection pool health
- Background task collects pool metrics every 15 seconds

**Prometheus metrics tracked:**
- `db_pool_max_connections`: Maximum connections allowed
- `db_pool_connections_in_use`: Current active connections
- `db_pool_connections_available`: Idle connections ready for use
- `db_pool_connections_created_total`: Total connections created (cumulative)
- `db_pool_overflow_count`: Overflow connections beyond pool_size
- `db_pool_info`: Pool configuration metadata

**Prometheus alerts:**
- `DatabasePoolNearExhaustion`: Pool usage > 80% for 3 minutes (warning)
- `DatabasePoolExhausted`: Pool usage ≥ 95% for 1 minute (critical)
- `DatabasePoolNoAvailableConnections`: Zero available connections for 1 minute (critical)

**Grafana dashboard panels** (IDs 31-33):
- Panel 31: Connections in use vs max connections (timeseries)
- Panel 32: Available connections over time (timeseries)
- Panel 33: Pool usage percentage gauge (0-100%)

## Related Documentation

- [Git Workflow Guide](git-workflow.md) - Git workflow, issue management, worktree syncing
- [Architecture Guide](architecture-guide.md) - Design patterns, components, request flow
- [Development Guide](development-guide.md) - Running the app, Docker, WebSocket handlers
- [Testing Guide](testing-guide.md) - Test infrastructure, fixtures, load/chaos tests
- [Code Quality Guide](code-quality-guide.md) - Linting, type checking, pre-commit hooks
- [Configuration Guide](configuration-guide.md) - Settings, environment variables, validation
- [Database Guide](database-guide.md) - Sessions, migrations, pagination, relationships
