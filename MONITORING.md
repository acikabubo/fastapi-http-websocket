# Monitoring Setup Guide

This application includes comprehensive Prometheus metrics for monitoring HTTP requests, WebSocket connections, and application health.

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

Start Prometheus and Grafana with your application:

```bash
cd docker
docker-compose up -d prometheus grafana
```

Access the monitoring tools:
- **Prometheus UI**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

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

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/advanced/monitoring/)
