# Production Deployment Guide

This guide covers deploying the FastAPI HTTP/WebSocket application to production with Traefik reverse proxy, Keycloak authentication, and full observability stack.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Environment Configuration](#environment-configuration)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Verification](#post-deployment-verification)
- [Scaling](#scaling)
- [Backup and Recovery](#backup-and-recovery)

## Prerequisites

### Required Services

- **Docker** 24.0+ with Docker Compose v2
- **PostgreSQL** 13+ (for application and Keycloak)
- **Redis** 7+ (for rate limiting and sessions)
- **Domain Names**:
  - API endpoint (e.g., `api.example.com`)
  - Authentication (e.g., `auth.example.com`)
  - Monitoring dashboards (e.g., `grafana.example.com`, `prometheus.example.com`)
  - Traefik dashboard (e.g., `traefik.example.com`)

### SSL/TLS Certificates

- Valid SSL certificates for all domains
- Let's Encrypt integration configured in Traefik
- Or provide your own certificates

### Resource Requirements

**Minimum (Single Instance)**:
- CPU: 2 cores
- RAM: 4GB
- Disk: 20GB SSD

**Recommended (Production)**:
- CPU: 4+ cores
- RAM: 8GB+
- Disk: 50GB+ SSD
- Load balancer for multiple instances

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└────────────────────┬────────────────────────────────────────┘
                     │
            ┌────────▼────────┐
            │  Traefik v3.0   │  (Reverse Proxy + SSL)
            │  Port 80/443    │
            └────────┬────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
┌─────▼─────┐  ┌────▼─────┐  ┌────▼────────┐
│  FastAPI  │  │ Keycloak │  │  Grafana    │
│  App      │  │  Auth    │  │  Dashboard  │
│  :8000    │  │  :8080   │  │  :3000      │
└─────┬─────┘  └────┬─────┘  └────┬────────┘
      │             │              │
  ┌───▼──────┬──────▼───────┬──────▼────────┐
  │          │              │               │
┌─▼──────┐ ┌▼────────┐  ┌──▼────────┐  ┌──▼──────┐
│Postgres│ │  Redis  │  │Prometheus │  │  Loki   │
│  :5432 │ │  :6379  │  │   :9090   │  │  :3100  │
└────────┘ └─────────┘  └───────────┘  └─────────┘
```

## Environment Configuration

### 1. Create Production Environment Files

**`.env.production`** (Application environment):

```bash
# ========================================
# Application Settings
# ========================================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# ========================================
# Database Configuration
# ========================================
DATABASE_URL=postgresql+asyncpg://prod_user:CHANGE_ME@postgres:5432/fastapi_prod
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# ========================================
# Redis Configuration
# ========================================
REDIS_IP=redis
REDIS_PORT=6379
REDIS_PASSWORD=CHANGE_ME  # Enable Redis auth
MAIN_REDIS_DB=0
AUTH_REDIS_DB=1
REDIS_MAX_CONNECTIONS=50

# ========================================
# Keycloak Configuration
# ========================================
KEYCLOAK_BASE_URL=https://auth.example.com
KEYCLOAK_REALM=production
KEYCLOAK_CLIENT_ID=fastapi-app
KEYCLOAK_CLIENT_SECRET=CHANGE_ME  # Get from Keycloak admin

KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=CHANGE_ME

# ========================================
# Security
# ========================================
SECRET_KEY=CHANGE_ME  # Generate with: openssl rand -hex 32
ALLOWED_HOSTS=["api.example.com"]
CORS_ORIGINS=["https://app.example.com","https://grafana.example.com"]

# ========================================
# Rate Limiting
# ========================================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
WS_MAX_CONNECTIONS_PER_USER=5
WS_MESSAGE_RATE_LIMIT=100

# ========================================
# Monitoring
# ========================================
PROMETHEUS_ENABLED=true
LOKI_URL=http://loki:3100

# ========================================
# Logging
# ========================================
LOG_CONSOLE_FORMAT=json  # CRITICAL for production
AUDIT_QUEUE_MAX_SIZE=10000
```

**`docker/.pg_env.production`** (PostgreSQL):

```bash
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=fastapi_prod
```

**`docker/.kc_env.production`** (Keycloak):

```bash
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=CHANGE_ME

KC_DB=postgres
KC_DB_URL_HOST=hw-db
KC_DB_URL_DATABASE=keycloak_prod
KC_DB_URL_PORT=5432
KC_DB_USERNAME=prod_user
KC_DB_PASSWORD=CHANGE_ME

# Enable production mode
KC_HOSTNAME=auth.example.com
KC_HOSTNAME_STRICT=true
KC_HTTP_ENABLED=false  # Force HTTPS
KC_PROXY=edge  # Behind Traefik

# Metrics and health
KC_METRICS_ENABLED=true
KC_HEALTH_ENABLED=true
```

### 2. Configure Traefik for Production

**`docker/traefik/traefik.yml`**:

Update for production domains:

```yaml
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true

  websecure:
    address: ":443"
    http:
      tls:
        certResolver: letsencrypt

certificatesResolvers:
  letsencrypt:
    acme:
      email: ops@example.com  # CHANGE THIS
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web
```

**`docker/docker-compose.prod.yml`**:

Update service labels with production domains:

```yaml
services:
  hw-server:
    labels:
      - "traefik.http.routers.fastapi.rule=Host(`api.example.com`)"
      - "traefik.http.routers.fastapi.entrypoints=websecure"
      - "traefik.http.routers.fastapi.tls.certresolver=letsencrypt"

  hw-keycloak:
    labels:
      - "traefik.http.routers.keycloak.rule=Host(`auth.example.com`)"
      - "traefik.http.routers.keycloak.entrypoints=websecure"
      - "traefik.http.routers.keycloak.tls.certresolver=letsencrypt"

  grafana:
    labels:
      - "traefik.http.routers.grafana.rule=Host(`grafana.example.com`)"
      - "traefik.http.routers.grafana.entrypoints=websecure"
      - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"
```

## Deployment Steps

### 1. Initial Setup

```bash
# Clone repository
git clone https://github.com/acikabubo/fastapi-http-websocket.git
cd fastapi-http-websocket

# Checkout production branch
git checkout main

# Create production environment files
cp .env.example .env.production
cp docker/.pg_env docker/.pg_env.production
cp docker/.kc_env docker/.kc_env.production

# IMPORTANT: Update all passwords and secrets in these files
```

### 2. Generate Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate database passwords
openssl rand -base64 32

# Generate Keycloak admin password
openssl rand -base64 24
```

### 3. Configure DNS

Point your domains to the server:

```
api.example.com        → A     → SERVER_IP
auth.example.com       → A     → SERVER_IP
grafana.example.com    → A     → SERVER_IP
prometheus.example.com → A     → SERVER_IP
traefik.example.com    → A     → SERVER_IP
```

### 4. Deploy Services

```bash
# Set UID/GID for file permissions
export UID=$(id -u)
export GID=$(id -g)

# Create volumes
docker volume create postgres-hw-data
docker volume create prometheus-data
docker volume create grafana-data
docker volume create loki-data
docker volume create traefik-certificates

# Start services
docker-compose -f docker/docker-compose.yml \
  --env-file .env.production \
  up -d

# Wait for services to be healthy
docker-compose -f docker/docker-compose.yml ps
```

### 5. Database Initialization

```bash
# Run migrations
docker exec hw-server alembic upgrade head

# Verify migrations
docker exec hw-server alembic current
docker exec hw-server alembic history
```

### 6. Configure Keycloak

```bash
# Access Keycloak admin console
https://auth.example.com

# Login with admin credentials from .kc_env.production

# Create production realm:
1. Realm → Create Realm → Name: "production"
2. Import realm-export.json (update redirect URIs for production domains)

# Create client for FastAPI:
1. Clients → Create Client
2. Client ID: fastapi-app
3. Client Authentication: ON
4. Valid redirect URIs:
   - https://api.example.com/*
5. Web Origins: https://api.example.com
6. Copy client secret to .env.production

# Create users and assign roles
```

### 7. Configure Grafana

```bash
# Access Grafana
https://grafana.example.com

# Login via Keycloak (auto-redirects)

# Import dashboards (already provisioned):
- FastAPI Metrics
- Traefik Metrics
- Keycloak Metrics
- Application Logs

# Configure alerts:
Alerting → Contact points → Add Slack/Email/PagerDuty
```

### 8. Verify SSL Certificates

```bash
# Check Traefik dashboard
https://traefik.example.com

# Verify ACME certificates
docker exec hw-traefik ls -la /letsencrypt/

# Test HTTPS
curl -v https://api.example.com/health
```

## Post-Deployment Verification

### Health Checks

```bash
# Application health
curl https://api.example.com/health
# Expected: {"status":"ok"}

# Keycloak health
curl https://auth.example.com/health
# Expected: {"status":"UP"}

# Prometheus
curl https://prometheus.example.com/-/healthy
# Expected: Healthy

# Traefik
curl https://traefik.example.com/ping
# Expected: OK
```

### Metrics Verification

```bash
# Check Prometheus targets
https://prometheus.example.com/targets

# All targets should be UP:
- fastapi (hw-server:8000/metrics)
- keycloak (hw-keycloak:9000/metrics)
- traefik (traefik:8080/metrics)
```

### Log Verification

```bash
# Check application logs
docker logs hw-server | tail -20

# Expected: Structured JSON logs with no errors
# Verify LOG_CONSOLE_FORMAT=json is working

# Check Loki ingestion
# Grafana → Explore → Loki → Query: {service="shell"}
```

### WebSocket Testing

```bash
# Test WebSocket connection
wscat -c wss://api.example.com/web?access_token=YOUR_TOKEN

# Send test message
{"pkg_id": 1, "req_id": "test-123", "data": {}}

# Expected: Response with same req_id
```

### Rate Limiting Testing

```bash
# Test HTTP rate limit
for i in {1..100}; do curl -s -o /dev/null -w "%{http_code}\n" https://api.example.com/health; done

# Expected: 200 responses, then 429 (Too Many Requests) after limit

# Check rate limit headers
curl -I https://api.example.com/health
# X-RateLimit-Limit: 60
# X-RateLimit-Remaining: 59
# X-RateLimit-Reset: 1234567890
```

## Scaling

### Horizontal Scaling

**Update docker-compose.yml**:

```yaml
services:
  hw-server:
    deploy:
      replicas: 3  # Run 3 instances
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

**Adjust Database Connection Pool**:

```bash
# If running 3 instances
# Total connections = 3 × DB_POOL_SIZE
# Keep total < Postgres max_connections

DB_POOL_SIZE=10  # 3 × 10 = 30 total connections
DB_MAX_OVERFLOW=5
```

**Load Balancer Configuration**:

Traefik automatically load balances across replicas. Monitor distribution:

```promql
# Prometheus query
rate(http_requests_total[5m]) by (instance)
```

### Vertical Scaling

**Database**:

```bash
# PostgreSQL tuning
shared_buffers = 2GB  # 25% of RAM
effective_cache_size = 6GB  # 75% of RAM
work_mem = 16MB
maintenance_work_mem = 512MB
max_connections = 100
```

**Redis**:

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Auto-Scaling (Kubernetes)

For Kubernetes deployments, use HPA (Horizontal Pod Autoscaler):

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Backup and Recovery

See [BACKUP_RECOVERY.md](../operations/BACKUP_RECOVERY.md) for detailed procedures.

**Quick Backup**:

```bash
# Database backup
docker exec hw-db pg_dump -U prod_user fastapi_prod > backup-$(date +%Y%m%d).sql

# Volume backup
docker run --rm -v postgres-hw-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-data-$(date +%Y%m%d).tar.gz /data
```

## Monitoring and Alerts

### Key Metrics to Monitor

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| `http_requests_total{status_code=~"5.."}` | > 5% error rate for 5min | Investigate errors |
| `http_request_duration_seconds{quantile="0.99"}` | > 1s for 5min | Check slow endpoints |
| `ws_connections_active` | > 1000 | Scale horizontally |
| `rate_limit_hits_total` | Sudden spike | Check for abuse |
| `up{job="postgres"}` | == 0 | Database down! |
| `redis_connected_clients` | > 90% of maxclients | Scale Redis |

### Alert Configuration

See [MONITORING.md](../operations/MONITORING.md) for Prometheus alert rules.

## Troubleshooting

See [TROUBLESHOOTING.md](../operations/TROUBLESHOOTING.md) for common issues and solutions.

**Quick Checks**:

```bash
# Check service health
docker-compose -f docker/docker-compose.yml ps

# Check logs
docker logs hw-server --tail 100
docker logs hw-traefik --tail 100

# Check resource usage
docker stats

# Check Traefik routing
curl https://traefik.example.com/api/http/routers
```

## Security Checklist

Before going live, verify:

- [ ] All default passwords changed
- [ ] SSL/TLS certificates valid
- [ ] Firewall configured (only 80/443 open)
- [ ] Database accessible only from app containers
- [ ] Redis password enabled
- [ ] Keycloak production mode enabled
- [ ] CORS origins restricted
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Monitoring and alerts configured
- [ ] Backup procedures tested
- [ ] Secrets not committed to git

## Rollback Procedure

If deployment fails:

```bash
# 1. Stop new version
docker-compose -f docker/docker-compose.yml down

# 2. Restore database backup
docker exec -i hw-db psql -U prod_user fastapi_prod < backup-YYYYMMDD.sql

# 3. Revert to previous git tag
git checkout v1.0.0  # Previous stable version

# 4. Redeploy
docker-compose -f docker/docker-compose.yml up -d

# 5. Verify
curl https://api.example.com/health
```

## Additional Resources

- [Docker Deployment Guide](DOCKER.md)
- [Security Guide](../security/SECURITY_GUIDE.md)
- [Monitoring Guide](../operations/MONITORING.md)
- [Troubleshooting Guide](../operations/TROUBLESHOOTING.md)
- [Backup and Recovery](../operations/BACKUP_RECOVERY.md)

## Support

- GitHub Issues: https://github.com/acikabubo/fastapi-http-websocket/issues
- Internal Docs: Confluence/Wiki
- On-call: PagerDuty rotation
