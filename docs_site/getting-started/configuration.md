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
# Application Settings
# ========================================
ENVIRONMENT=development  # development, staging, production
DEBUG=true
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ========================================
# Database Configuration
# ========================================
DATABASE_URL=postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# ========================================
# Redis Configuration
# ========================================
REDIS_IP=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Leave empty for no auth in development
MAIN_REDIS_DB=0
AUTH_REDIS_DB=1
REDIS_MAX_CONNECTIONS=50

# ========================================
# Keycloak Configuration
# ========================================
KEYCLOAK_BASE_URL=http://localhost:8080
KEYCLOAK_REALM=development
KEYCLOAK_CLIENT_ID=fastapi-app
KEYCLOAK_CLIENT_SECRET=your-client-secret-here

KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# ========================================
# Security
# ========================================
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

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
LOKI_URL=http://localhost:3100

# ========================================
# Logging
# ========================================
LOG_CONSOLE_FORMAT=human  # human or json
AUDIT_QUEUE_MAX_SIZE=10000
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

### Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `DB_POOL_SIZE` | 20 | Connection pool size |
| `DB_MAX_OVERFLOW` | 10 | Max overflow connections |

### Redis Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_IP` | localhost | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `MAIN_REDIS_DB` | 0 | Main Redis database number |
| `AUTH_REDIS_DB` | 1 | Auth Redis database number |
| `REDIS_MAX_CONNECTIONS` | 50 | Max Redis connections |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | 60 | HTTP requests per minute |
| `RATE_LIMIT_BURST` | 10 | Burst allowance |
| `WS_MAX_CONNECTIONS_PER_USER` | 5 | Max WebSocket connections per user |
| `WS_MESSAGE_RATE_LIMIT` | 100 | WebSocket messages per minute |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_CONSOLE_FORMAT` | human | Log format (human/json) |
| `AUDIT_QUEUE_MAX_SIZE` | 10000 | Audit log queue size |

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
