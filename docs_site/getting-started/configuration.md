# Configuration

Learn how to configure the application and its services for different environments.

## Environment Files

The project uses multiple environment files:

| File | Purpose | Location |
|------|---------|----------|
| `.env` | Application configuration | Project root |
| `docker/.srv_env` | Service environment | Docker directory |
| `docker/.pg_env` | PostgreSQL credentials | Docker directory |
| `docker/.kc_env` | Keycloak configuration | Docker directory |

## Application Configuration

### .env File

Create `.env` in the project root:

```bash
# ========================================
# Environment & Security
# ========================================
ENV=dev  # dev, staging, production
ALLOWED_HOSTS=["*"]  # Use specific domains in production: ["example.com", "*.example.com"]
TRUSTED_PROXIES=["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]  # Docker networks
MAX_REQUEST_BODY_SIZE=1048576  # 1MB
EXCLUDED_PATHS=/health|/metrics|/docs.*  # Regex for paths excluded from auth

# ========================================
# Database Configuration
# ========================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fastapi
DB_USER=fastapi
DB_PASSWORD=fastapi
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_INIT_MAX_RETRIES=5
DB_INIT_RETRY_INTERVAL=5
DEFAULT_PAGE_SIZE=20

# ========================================
# Redis Configuration
# ========================================
REDIS_IP=localhost
REDIS_PORT=6379
MAIN_REDIS_DB=1
AUTH_REDIS_DB=10
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECT_TIMEOUT=5
REDIS_HEALTH_CHECK_INTERVAL=30
REDIS_RETRY_ON_TIMEOUT=true

# ========================================
# Keycloak Configuration
# ========================================
KEYCLOAK_BASE_URL=http://localhost:8080
KEYCLOAK_REALM=development
KEYCLOAK_CLIENT_ID=fastapi-app
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin
USER_SESSION_REDIS_KEY_PREFIX=user_session:

# ========================================
# Rate Limiting
# ========================================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
RATE_LIMIT_FAIL_MODE=open  # open or closed
WS_MAX_CONNECTIONS_PER_USER=5
WS_MESSAGE_RATE_LIMIT=100

# ========================================
# Audit Logging
# ========================================
AUDIT_LOG_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=90
AUDIT_QUEUE_MAX_SIZE=10000
AUDIT_BATCH_SIZE=100
AUDIT_BATCH_TIMEOUT=5

# ========================================
# Logging
# ========================================
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_CONSOLE_FORMAT=human  # human or json (use json in production for Grafana Alloy)
LOG_FILE_PATH=logs/logging_errors.log
LOG_EXCLUDED_PATHS=/health|/metrics

# ========================================
# Circuit Breaker
# ========================================
CIRCUIT_BREAKER_ENABLED=true
KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX=5
KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT=60
REDIS_CIRCUIT_BREAKER_FAIL_MAX=3
REDIS_CIRCUIT_BREAKER_TIMEOUT=30

# ========================================
# Profiling
# ========================================
PROFILING_ENABLED=true
PROFILING_OUTPUT_DIR=profiling_reports
PROFILING_INTERVAL_SECONDS=30
```

## Docker Services Configuration

### PostgreSQL (docker/.pg_env)

```bash
POSTGRES_USER=fastapi
POSTGRES_PASSWORD=fastapi
POSTGRES_DB=fastapi
```

### Keycloak (docker/.kc_env)

```bash
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin

KC_DB=postgres
KC_DB_URL_HOST=hw-db
KC_DB_URL_DATABASE=keycloak
KC_DB_URL_PORT=5432
KC_DB_USERNAME=fastapi
KC_DB_PASSWORD=fastapi

KC_HOSTNAME=localhost
KC_HTTP_ENABLED=true
KC_HOSTNAME_STRICT=false
KC_PROXY=edge

KC_METRICS_ENABLED=true
KC_HEALTH_ENABLED=true
```

### Application Service (docker/.srv_env)

```bash
LOG_CONSOLE_FORMAT=human  # human for development, json for production
```

## Configuration Options

### Environment & Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `dev` | Environment type (`dev`, `staging`, `production`). Controls default log levels and security settings. |
| `ALLOWED_HOSTS` | `["*"]` | List of allowed Host header values to prevent Host header injection attacks. Use `["example.com", "*.example.com"]` in production. |
| `TRUSTED_PROXIES` | Docker networks | List of trusted proxy IP addresses/networks (CIDR notation) for X-Forwarded-For validation. Prevents IP spoofing. |
| `MAX_REQUEST_BODY_SIZE` | `1048576` (1MB) | Maximum request body size in bytes. Protects against large payload attacks. |
| `EXCLUDED_PATHS` | Docs, metrics | Regex patterns for paths excluded from authentication (e.g., `/health`, `/metrics`, `/docs`). |

**Production Security:**
- Always set specific `ALLOWED_HOSTS` in production (never use `["*"]`)
- Configure `TRUSTED_PROXIES` to match your load balancer/proxy IPs
- Keep `MAX_REQUEST_BODY_SIZE` as low as practical for your use case
- Minimize `EXCLUDED_PATHS` to only public endpoints

### Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host address |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `fastapi` | Database name |
| `DB_USER` | `fastapi` | Database username |
| `DB_PASSWORD` | - | Database password (required) |
| `DB_POOL_SIZE` | `20` | Base connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections beyond pool size |
| `DB_POOL_RECYCLE` | `3600` | Connection recycle time in seconds (prevents stale connections) |
| `DB_POOL_PRE_PING` | `true` | Test connections before use (prevents using dead connections) |
| `DB_INIT_MAX_RETRIES` | `5` | Max retries for database initialization on startup |
| `DB_INIT_RETRY_INTERVAL` | `5` | Seconds between database init retries |
| `DEFAULT_PAGE_SIZE` | `20` | Default items per page for paginated endpoints |

**Tuning Guidelines:**
- **Low traffic** (<100 req/s): `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=5`
- **Medium traffic** (100-500 req/s): `DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=10` (default)
- **High traffic** (>500 req/s): `DB_POOL_SIZE=50`, `DB_MAX_OVERFLOW=20`
- Monitor `db_connections_active` Prometheus metric to optimize pool size

### Redis Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_IP` | `localhost` | Redis host address |
| `REDIS_PORT` | `6379` | Redis port |
| `MAIN_REDIS_DB` | `1` | Main Redis database number (rate limiting, caching) |
| `AUTH_REDIS_DB` | `10` | Auth Redis database number (token cache, sessions) |
| `REDIS_MAX_CONNECTIONS` | `50` | Max connections per Redis pool |
| `REDIS_SOCKET_TIMEOUT` | `5` | Socket operation timeout in seconds |
| `REDIS_CONNECT_TIMEOUT` | `5` | Connection establishment timeout in seconds |
| `REDIS_HEALTH_CHECK_INTERVAL` | `30` | Health check frequency in seconds |
| `REDIS_RETRY_ON_TIMEOUT` | `true` | Retry operations on timeout |

**Redis Pool Monitoring:**
- Monitor `redis_pool_connections_in_use` and `redis_pool_connections_available` metrics
- If pool exhaustion occurs frequently, increase `REDIS_MAX_CONNECTIONS`
- Configure Prometheus alerts for pool usage > 80%

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting middleware |
| `RATE_LIMIT_PER_MINUTE` | `60` | HTTP requests per minute per user/IP |
| `RATE_LIMIT_BURST` | `10` | Burst allowance for short-term traffic spikes |
| `RATE_LIMIT_FAIL_MODE` | `open` | Fail mode when Redis unavailable (`open` = allow requests, `closed` = deny requests) |
| `WS_MAX_CONNECTIONS_PER_USER` | `5` | Max concurrent WebSocket connections per user |
| `WS_MESSAGE_RATE_LIMIT` | `100` | WebSocket messages per minute per user |

**Environment-Specific Defaults:**
- **Development**: `RATE_LIMIT_FAIL_MODE=open` (permissive)
- **Staging**: `RATE_LIMIT_FAIL_MODE=open` (forgiving for testing)
- **Production**: `RATE_LIMIT_FAIL_MODE=closed` (strict security)

**Tuning Guidelines:**
- Public APIs: Use lower limits (60/min) with monitoring
- Internal APIs: Higher limits (300/min) acceptable
- WebSocket: `WS_MESSAGE_RATE_LIMIT` depends on real-time requirements

### Audit Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIT_LOG_ENABLED` | `true` | Enable audit logging middleware |
| `AUDIT_LOG_RETENTION_DAYS` | `90` | Audit log retention period (PostgreSQL cleanup) |
| `AUDIT_QUEUE_MAX_SIZE` | `10000` | Max audit log queue size (prevents memory overflow) |
| `AUDIT_BATCH_SIZE` | `100` | Number of logs written per database batch |
| `AUDIT_BATCH_TIMEOUT` | `5` | Seconds to wait before flushing partial batch |

**Queue Overflow Monitoring:**
- Monitor `audit_logs_dropped_total` metric
- If logs are dropping, increase `AUDIT_QUEUE_MAX_SIZE` or `AUDIT_BATCH_SIZE`
- Configure alert: `rate(audit_logs_dropped_total[5m]) > 1` (see Prometheus alerts)

**Compliance Settings:**
- Financial services: `AUDIT_LOG_RETENTION_DAYS=2555` (7 years)
- Healthcare (HIPAA): `AUDIT_LOG_RETENTION_DAYS=2555` (7 years)
- GDPR: `AUDIT_LOG_RETENTION_DAYS=365` (1 year minimum)

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | Env-dependent | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `LOG_FILE_PATH` | `logs/logging_errors.log` | Error log file path (JSON format) |
| `LOG_CONSOLE_FORMAT` | Env-dependent | Console log format (`human` for development, `json` for production) |
| `LOG_EXCLUDED_PATHS` | `/health`, `/metrics` | Paths excluded from access logs (reduces log noise) |

**Environment-Specific Defaults:**
- **Development**: `LOG_LEVEL=DEBUG`, `LOG_CONSOLE_FORMAT=human`
- **Staging**: `LOG_LEVEL=INFO`, `LOG_CONSOLE_FORMAT=json`
- **Production**: `LOG_LEVEL=WARNING`, `LOG_CONSOLE_FORMAT=json`

**Important:**
- Always use `LOG_CONSOLE_FORMAT=json` in production for Grafana Alloy/Loki integration
- Use `LOG_CONSOLE_FORMAT=human` for local development (easier to read)
- Grafana Alloy requires JSON format to parse structured logs correctly

### Circuit Breaker

| Variable | Default | Description |
|----------|---------|-------------|
| `CIRCUIT_BREAKER_ENABLED` | `true` | Enable circuit breaker pattern for external services |
| `KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX` | `5` | Max failures before opening Keycloak circuit breaker |
| `KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT` | `60` | Seconds to wait before half-open (retry) state |
| `REDIS_CIRCUIT_BREAKER_FAIL_MAX` | `3` | Max failures before opening Redis circuit breaker |
| `REDIS_CIRCUIT_BREAKER_TIMEOUT` | `30` | Seconds to wait before half-open (retry) state |

**Tuning Guidelines:**
- **Critical services** (Keycloak): Higher `FAIL_MAX` (5) + longer `TIMEOUT` (60s) = more retries before failing fast
- **Non-critical services** (Redis cache): Lower `FAIL_MAX` (3) + shorter `TIMEOUT` (30s) = fail fast to protect system
- Monitor `circuit_breaker_state` metric (0=closed, 1=open, 2=half_open)
- Configure alerts for open circuit breakers (critical incidents)

**See**: [Circuit Breaker Guide](../guides/circuit-breaker.md) for comprehensive documentation

### Profiling

| Variable | Default | Description |
|----------|---------|-------------|
| `PROFILING_ENABLED` | Env-dependent | Enable Scalene profiling integration |
| `PROFILING_OUTPUT_DIR` | `profiling_reports` | Directory for profiling report output |
| `PROFILING_INTERVAL_SECONDS` | `30` | Profiling sample interval |

**Environment-Specific Defaults:**
- **Development**: `PROFILING_ENABLED=true` (enabled for local testing)
- **Staging**: `PROFILING_ENABLED=true` (performance testing)
- **Production**: `PROFILING_ENABLED=false` (disabled to reduce overhead)

**Usage:**
- Run application with Scalene: `scalene run -- uvicorn app:application`
- Access reports via `/api/profiling/reports` endpoint
- See [Performance Profiling](../guides/monitoring.md#performance-profiling) section

### Keycloak

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_BASE_URL` | `http://localhost:8080` | Keycloak server URL |
| `KEYCLOAK_REALM` | - | Keycloak realm name (required) |
| `KEYCLOAK_CLIENT_ID` | - | OAuth2 client ID (required) |
| `KEYCLOAK_ADMIN_USERNAME` | - | Keycloak admin username (required) |
| `KEYCLOAK_ADMIN_PASSWORD` | - | Keycloak admin password (required) |
| `USER_SESSION_REDIS_KEY_PREFIX` | `user_session:` | Redis key prefix for user session tracking |

## Environment-Specific Configuration

### Development

```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_CONSOLE_FORMAT=human
RATE_LIMIT_PER_MINUTE=1000  # Higher limits for testing
```

### Staging

```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
LOG_CONSOLE_FORMAT=json
RATE_LIMIT_PER_MINUTE=120
```

### Production

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
LOG_CONSOLE_FORMAT=json
RATE_LIMIT_PER_MINUTE=60

# Use strong secrets
SECRET_KEY=<generated-with-openssl-rand>
KEYCLOAK_CLIENT_SECRET=<from-keycloak-admin>

# Use production domains
KEYCLOAK_BASE_URL=https://auth.example.com
ALLOWED_HOSTS=["api.example.com"]
CORS_ORIGINS=["https://app.example.com"]
```

## Keycloak Configuration

### Creating a Realm

1. Access Keycloak admin console: http://localhost:8080
2. Login with admin credentials
3. Create a new realm (e.g., "development")
4. Configure realm settings

### Creating a Client

1. Go to Clients → Create
2. Set Client ID: `fastapi-app`
3. Enable "Client authentication"
4. Set Valid redirect URIs: `http://localhost:8000/*`
5. Set Web origins: `http://localhost:8000`
6. Save and copy the client secret

### Creating Roles

1. Go to Realm roles → Create role
2. Create roles: `admin`, `user`, `viewer`
3. Assign roles to users

### Creating Users

1. Go to Users → Add user
2. Set username and email
3. Go to Credentials tab → Set password
4. Go to Role mapping → Assign roles

## RBAC Configuration

Role-based access control is configured directly in handler code using decorators:

**WebSocket Handlers** (`app/api/ws/handlers/`):
```python
@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=GetAuthorsModel,
    roles=["get-authors"]  # Define required roles here
)
async def get_authors_handler(request: RequestModel) -> ResponseModel:
    ...
```

**HTTP Endpoints** (`app/api/http/`):
```python
from app.dependencies.permissions import require_roles

@router.get(
    "/authors",
    dependencies=[Depends(require_roles("get-authors"))]
)
async def get_authors():
    ...
```

No external configuration file needed - permissions are co-located with handler code.

## Docker Compose Configuration

The `docker-compose.yml` file can be customized for different environments:

### Development

```yaml
services:
  hw-server:
    volumes:
      - .:/app  # Mount code for hot reload
    command: uvicorn app:application --reload
    environment:
      - DEBUG=true
```

### Production

```yaml
services:
  hw-server:
    image: fastapi-app:latest  # Use built image
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - DEBUG=false
```

## Monitoring Configuration

### Prometheus (docker/prometheus/prometheus.yml)

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['hw-server:8000']
```

### Grafana (docker/grafana/provisioning/)

Grafana is pre-configured with:
- Data sources (Prometheus, Loki)
- Dashboards (FastAPI Metrics, Application Logs, Keycloak Metrics)
- Default admin credentials: admin/admin

## Troubleshooting Configuration

### Check Current Configuration

```bash
# Inside the application
uv run python -c "from app.settings import settings; print(settings.model_dump())"

# Or use IPython
make ipython
>>> from app.settings import settings
>>> settings.DATABASE_URL
```

### Validate Environment Files

```bash
# Check if all required variables are set
grep -v '^#' .env | grep -v '^$' | sort

# Validate docker environment files
ls -la docker/.*.env
```

### Common Issues

**Issue**: `DATABASE_URL` not found
```bash
# Solution: Ensure .env file exists
cp .env.example .env
```

**Issue**: Keycloak connection refused
```bash
# Solution: Ensure Keycloak is running
docker ps | grep keycloak
docker logs hw-keycloak
```

**Issue**: Redis connection error
```bash
# Solution: Check Redis is accessible
docker exec hw-redis redis-cli ping
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Build your first endpoints
- [Authentication Guide](../guides/authentication.md) - Configure authentication
- [Security Guide](../deployment/security.md) - Production security
- [Deployment Guide](../deployment/production.md) - Deploy to production
