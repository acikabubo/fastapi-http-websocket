# Monitoring Setup Guide

This application includes comprehensive observability with Prometheus metrics for monitoring and Grafana Loki for centralized log aggregation.

## Quick Start

### 1. View Raw Metrics

Start your FastAPI application and navigate to:
```
http://localhost:8000/metrics
```

You'll see Prometheus text format metrics like:
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/health",status_code="200"} 42.0

# HELP ws_connections_active Active WebSocket connections
# TYPE ws_connections_active gauge
ws_connections_active 5.0
```

### 2. Using Docker Compose (Recommended)

Start the full observability stack with your application:

```bash
cd docker
docker-compose up -d
```

Access the monitoring and logging tools:
- **Application**: http://localhost:8000
- **Prometheus UI**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Loki API**: http://localhost:3100
- **Metrics Endpoint**: http://localhost:8000/metrics

## Available Metrics

### HTTP Metrics
- `http_requests_total` - Total number of HTTP requests (counter)
  - Labels: method, endpoint, status_code
- `http_request_duration_seconds` - HTTP request duration (histogram)
  - Labels: method, endpoint
  - Buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
- `http_requests_in_progress` - In-progress HTTP requests (gauge)
  - Labels: method, endpoint

### WebSocket Metrics
- `ws_connections_active` - Active WebSocket connections (gauge)
- `ws_connections_total` - Total WebSocket connections (counter)
  - Labels: status (accepted, rejected_auth, rejected_limit)
- `ws_messages_received_total` - Total WebSocket messages received (counter)
- `ws_messages_sent_total` - Total WebSocket messages sent (counter)
- `ws_message_processing_duration_seconds` - Message processing duration (histogram)
  - Labels: pkg_id

### Database Metrics (for future instrumentation)
- `db_query_duration_seconds` - Database query duration (histogram)
  - Labels: operation
- `db_connections_active` - Active database connections (gauge)
- `db_query_errors_total` - Database query errors (counter)
  - Labels: operation, error_type

### Redis Metrics (for future instrumentation)
- `redis_operations_total` - Total Redis operations (counter)
  - Labels: operation
- `redis_operation_duration_seconds` - Redis operation duration (histogram)
  - Labels: operation

### Authentication & Rate Limiting
- `auth_attempts_total` - Authentication attempts (counter)
  - Labels: status
- `auth_token_validations_total` - Token validations (counter)
  - Labels: status
- `rate_limit_hits_total` - Rate limit hits (counter)
  - Labels: limit_type

### Application Metrics
- `app_errors_total` - Application errors (counter)
  - Labels: error_type, handler
- `app_info` - Application info (gauge)
  - Labels: version, python_version, environment

## Prometheus Queries

### Useful PromQL Queries

**Request rate (requests per second):**
```promql
rate(http_requests_total[5m])
```

**95th percentile request duration:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Error rate:**
```promql
rate(http_requests_total{status_code=~"5.."}[5m])
```

**WebSocket connection rate:**
```promql
rate(ws_connections_total[5m])
```

**Rate limit hit rate:**
```promql
rate(rate_limit_hits_total[5m])
```

**Average message processing time:**
```promql
rate(ws_message_processing_duration_seconds_sum[5m]) / rate(ws_message_processing_duration_seconds_count[5m])
```

## Grafana Setup

### 1. Add Prometheus Data Source

1. Login to Grafana at http://localhost:3000 (admin/admin)
2. Go to Configuration → Data Sources
3. Click "Add data source"
4. Select "Prometheus"
5. Set URL to `http://prometheus:9090`
6. Click "Save & Test"

### 2. Import Dashboard

A pre-configured dashboard (`grafana-dashboard.json`) is included with panels for:
- HTTP request rate
- HTTP request duration (95th percentile)
- Active WebSocket connections
- WebSocket connection rate
- WebSocket message rate
- Rate limit hits
- HTTP requests in progress
- Application info

To import:
1. Go to Dashboards → Import
2. Upload `grafana-dashboard.json`
3. Select the Prometheus data source
4. Click "Import"

### 3. Create Custom Panels

Example panel configurations:

**Error Rate Panel:**
```json
{
  "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m])",
  "legendFormat": "{{method}} {{endpoint}} - {{status_code}}"
}
```

**WebSocket Active Connections:**
```json
{
  "expr": "ws_connections_active",
  "legendFormat": "Active Connections"
}
```

## Alerts

### Example Alert Rules

Create `prometheus-alerts.yml`:

```yaml
groups:
  - name: fastapi_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests/second"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "95th percentile latency is {{ $value }}s"

      - alert: RateLimitExceeded
        expr: rate(rate_limit_hits_total[5m]) > 10
        for: 2m
        labels:
          severity: info
        annotations:
          summary: "Rate limits being hit frequently"
          description: "Rate limit hit rate: {{ $value }} hits/second"
```

Update `prometheus.yml` to include alerts:
```yaml
rule_files:
  - "prometheus-alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

## Custom Metrics in Code

### Adding Custom Metrics

```python
from app.utils.metrics import http_requests_total, db_query_duration_seconds

# Increment counter
http_requests_total.labels(
    method="POST",
    endpoint="/api/custom",
    status_code=201
).inc()

# Observe histogram
db_query_duration_seconds.labels(operation="select").observe(0.045)
```

### Creating New Metrics

Add to `app/utils/metrics.py`:

```python
from prometheus_client import Counter

custom_events_total = Counter(
    'custom_events_total',
    'Total custom events',
    ['event_type', 'status']
)

# Usage
custom_events_total.labels(event_type='user_action', status='success').inc()
```

## Production Considerations

### 1. Metric Cardinality

Avoid high-cardinality labels (e.g., user IDs, timestamps). Use aggregated labels instead:

❌ Bad:
```python
requests.labels(user_id=user.id)  # Unbounded cardinality
```

✅ Good:
```python
requests.labels(user_type=user.role)  # Bounded cardinality
```

### 2. Performance

- Metrics collection has minimal overhead (~microseconds per metric)
- Use histograms for latency tracking (pre-configured buckets)
- Consider sampling for very high-traffic endpoints if needed

### 3. Retention

Configure Prometheus retention in `docker-compose.yml`:

```yaml
command:
  - '--storage.tsdb.retention.time=30d'
  - '--storage.tsdb.retention.size=10GB'
```

### 4. Security

For production:
- Enable authentication on Prometheus and Grafana
- Use TLS for metrics endpoints
- Restrict network access to monitoring tools
- Consider using read-only Prometheus API tokens

## Troubleshooting

### Metrics not appearing

1. Check `/metrics` endpoint is accessible:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Verify Prometheus is scraping:
   - Go to http://localhost:9090/targets
   - Check if `fastapi-app` target is UP

3. Check Prometheus logs:
   ```bash
   docker logs hw-prometheus
   ```

### Grafana dashboard shows no data

1. Verify data source connection:
   - Configuration → Data Sources → Prometheus → Test

2. Check time range in dashboard (top right)

3. Verify metrics exist in Prometheus:
   - Go to Prometheus → Graph
   - Enter metric name and execute

### High memory usage

If Prometheus uses too much memory:

1. Reduce retention time:
   ```yaml
   --storage.tsdb.retention.time=15d
   ```

2. Reduce scrape frequency in `prometheus.yml`:
   ```yaml
   scrape_interval: 30s  # Instead of 15s
   ```

3. Review metric cardinality:
   ```promql
   count({__name__=~".+"}) by (__name__)
   ```

## Centralized Logging with Loki

### Overview

Grafana Loki provides centralized log aggregation for all Docker containers. Promtail collects logs from Docker containers and ships them to Loki for storage and querying.

### Architecture

```
Docker Containers → Promtail → Loki → Grafana
                      ↓
                 /var/run/docker.sock
```

- **Loki**: Log aggregation system (similar to Prometheus but for logs)
- **Promtail**: Log collection agent that reads Docker container logs
- **Grafana**: Visualization layer for both metrics and logs

### Viewing Logs in Grafana

#### 1. Using the Logs Dashboard

1. Navigate to Grafana: http://localhost:3000
2. Go to Dashboards → Application Logs
3. The dashboard includes:
   - Log volume by service
   - Log level distribution (ERROR, WARNING, INFO)
   - Error logs panel
   - Error rate trends
   - Service-specific log panels

#### 2. Using Explore (Ad-hoc Queries)

1. Go to Explore → Select "Loki" datasource
2. Use LogQL to query logs

### LogQL Query Examples

**Basic Queries:**

```logql
# All logs from shell service (FastAPI)
{service="shell"}

# All logs from specific container
{container="hw-shell"}

# Logs from multiple services
{service=~"shell|hw-db|hw-keycloak"}
```

**Filtering by Content:**

```logql
# All error logs
{service="shell"} |= "ERROR"

# Case-insensitive error search
{service="shell"} |~ "(?i)(error|exception)"

# Filter out health checks
{service="shell"} != "GET /health"

# Python tracebacks
{service="shell"} |= "Traceback"
```

**JSON Log Parsing:**

```logql
# Parse JSON logs and filter by level
{service="shell"} | json | level="ERROR"

# Extract specific JSON field
{service="shell"} | json | line_format "{{.message}}"

# Filter by nested JSON field
{service="shell"} | json | error!=""
```

**Advanced Queries:**

```logql
# Count log lines per service
sum by (service) (count_over_time({job="docker"}[5m]))

# Error rate per service
sum by (service) (rate({job="docker"} |~ "(?i)error" [5m]))

# Top 10 error messages
topk(10, sum by (service) (count_over_time({job="docker"} |~ "(?i)error" [1h])))

# Filter by multiple conditions
{service="shell"}
  | json
  | level="ERROR"
  | line_format "{{.timestamp}} - {{.message}}"
```

**Time-based Queries:**

```logql
# Logs in the last 5 minutes
{service="shell"} [5m]

# Log volume rate
rate({service="shell"}[1m])

# Count over time window
count_over_time({service="shell"}[10m])
```

### Log Retention

By default, logs are retained for **7 days (168 hours)**. This is configured in [docker/loki/loki-config.yml](docker/loki/loki-config.yml:44):

```yaml
limits_config:
  reject_old_samples_max_age: 168h  # 7 days

compactor:
  retention_enabled: true
  retention_delete_delay: 2h
```

To change retention:
1. Edit `docker/loki/loki-config.yml`
2. Update `reject_old_samples_max_age` value (e.g., `720h` for 30 days)
3. Restart Loki: `docker-compose restart loki`

### Log Collection Configuration

Promtail is configured to collect logs from all Docker containers in this project. Configuration is in [docker/promtail/promtail-config.yml](docker/promtail/promtail-config.yml).

**What gets collected:**
- Container logs (stdout/stderr)
- Service name from Docker Compose labels
- Log stream (stdout vs stderr)
- Container ID and name
- Timestamps

**What gets filtered out:**
- Health check requests (`GET /health`)
- Empty log lines

### Structured Logging Best Practices

For better log parsing and filtering, use structured logging in your application:

#### Option 1: JSON Logging (Recommended)

```python
import logging
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure in your app
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

#### Option 2: Using structlog

```python
import structlog

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Usage
logger.info("user_login", user_id=123, username="alice", ip="192.168.1.1")
logger.error("database_error", error=str(e), query=query, duration_ms=145)
logger.warning("rate_limit_hit", user_id=456, endpoint="/api/data")
```

**Benefits of structured logging:**
- Easy to parse in Loki with `| json`
- Filter by specific fields
- Better searchability
- Consistent log format

### Correlating Logs with Metrics

In Grafana, you can correlate metrics spikes with logs:

1. **From Metrics Dashboard to Logs:**
   - Click on a metric spike in Prometheus dashboard
   - Select "Explore" → Switch to Loki datasource
   - Logs from the same time range will appear

2. **From Logs to Metrics:**
   - Find an error in logs
   - Note the timestamp
   - Switch to Prometheus datasource
   - Query metrics around that timestamp

3. **Split View:**
   - Use Grafana's split view (Explore → Split)
   - Prometheus on one side, Loki on the other
   - Same time range for correlation

### Troubleshooting Loki

#### No logs appearing

1. **Check Promtail is running:**
   ```bash
   docker ps | grep promtail
   docker logs hw-promtail
   ```

2. **Verify Promtail can access Docker socket:**
   ```bash
   docker exec hw-promtail ls -la /var/run/docker.sock
   ```

3. **Check Promtail targets:**
   ```bash
   curl http://localhost:9080/targets
   ```

4. **Verify Loki is receiving logs:**
   ```bash
   curl http://localhost:3100/loki/api/v1/label
   curl http://localhost:3100/loki/api/v1/label/service/values
   ```

#### Logs are delayed

- Promtail buffers logs before sending to Loki
- Default refresh interval: 5 seconds
- Check Promtail logs for errors: `docker logs hw-promtail`

#### High Loki memory usage

1. **Reduce retention period** in `loki-config.yml`:
   ```yaml
   limits_config:
     reject_old_samples_max_age: 72h  # 3 days instead of 7
   ```

2. **Limit ingestion rate**:
   ```yaml
   limits_config:
     ingestion_rate_mb: 5  # Reduce from 10MB
     ingestion_burst_size_mb: 10  # Reduce from 20MB
   ```

3. **Filter noisy logs** in `promtail-config.yml`:
   ```yaml
   pipeline_stages:
     - drop:
         expression: '.*DEBUG.*'
         drop_counter_reason: debug_logs
   ```

#### Cannot query old logs

- Check retention settings in `loki-config.yml`
- Verify compactor is running:
  ```bash
  docker logs hw-loki | grep compactor
  ```

### Loki API Usage

Query logs programmatically:

```bash
# Query logs via API
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={service="shell"} |= "error"' \
  --data-urlencode "start=$(date -d '1 hour ago' +%s)000000000" \
  --data-urlencode "end=$(date +%s)000000000" \
  | jq '.data.result'

# Get label values
curl -s "http://localhost:3100/loki/api/v1/label/service/values" | jq

# Get all labels
curl -s "http://localhost:3100/loki/api/v1/labels" | jq
```

### LogQL vs PromQL

| Feature | PromQL (Metrics) | LogQL (Logs) |
|---------|-----------------|--------------|
| Data type | Time-series metrics | Log lines |
| Query | `rate(http_requests_total[5m])` | `{service="shell"} \|= "error"` |
| Aggregation | `sum by (method)` | `count_over_time()` |
| Filtering | Label matchers | Text search + JSON parsing |
| Output | Numbers | Log lines + counts |

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [LogQL Documentation](https://grafana.com/docs/loki/latest/logql/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/advanced/monitoring/)
