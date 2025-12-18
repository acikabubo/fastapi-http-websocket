# Installation

This guide will walk you through setting up the FastAPI HTTP/WebSocket template for local development.

## Prerequisites

Ensure you have the following installed:

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.13+ | Application runtime |
| **Docker** | 24.0+ | Containerization |
| **Docker Compose** | v2+ | Service orchestration |
| **uv** | latest | Python package manager |
| **Git** | latest | Version control |

### Install uv (Python Package Manager)

```bash
# Install uv
pip install uv

# Verify installation
uv --version
```

## Clone the Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/fastapi-http-websocket.git
cd fastapi-http-websocket

# Or if using as a template
cookiecutter gh:yourusername/fastapi-http-websocket
```

## Install Python Dependencies

```bash
# Sync all dependencies
uv sync

# Sync with dev dependencies
uv sync --all-groups

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate  # Windows
```

## Start Infrastructure Services

The application requires several infrastructure services. Start them with Docker Compose:

```bash
# Start all services in background
make start

# Or using docker-compose directly
docker compose -f docker/docker-compose.yml up -d
```

This will start:

- **PostgreSQL** (port 5432) - Main database
- **Redis** (port 6379) - Cache and rate limiting
- **Keycloak** (port 8080) - Authentication server
- **Prometheus** (port 9090) - Metrics collection
- **Grafana** (port 3000) - Dashboards and visualization
- **Loki** (port 3100) - Log aggregation
- **Grafana Alloy** - Log collection agent
- **Traefik** (ports 80/443/8080) - Reverse proxy

### Verify Services

```bash
# Check all services are running
docker ps

# Check service health
curl http://localhost:8000/health  # Application (after starting)
curl http://localhost:8080/health  # Keycloak
curl http://localhost:9090/-/healthy  # Prometheus
```

## Initialize the Database

Run database migrations to set up the schema:

```bash
# Run migrations
make migrate

# Or using alembic directly
uv run alembic upgrade head

# Verify current migration
make migration-current
```

## Configure Keycloak

Keycloak is pre-configured with a realm export, but you need to verify the configuration:

1. **Access Keycloak Admin Console**: http://localhost:8080
2. **Login** with credentials from `docker/.kc_env`:
   - Username: `admin`
   - Password: `admin` (change in production!)
3. **Verify Realm**: Check that the `development` realm exists
4. **Verify Client**: Check that the `fastapi-app` client is configured

## Environment Configuration

Create your environment file from the example:

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env  # or your preferred editor
```

### Key Environment Variables

```bash
# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi

# Redis
REDIS_IP=localhost
REDIS_PORT=6379
MAIN_REDIS_DB=0
AUTH_REDIS_DB=1

# Keycloak
KEYCLOAK_BASE_URL=http://localhost:8080
KEYCLOAK_REALM=development
KEYCLOAK_CLIENT_ID=fastapi-app
KEYCLOAK_CLIENT_SECRET=your-client-secret

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
WS_MAX_CONNECTIONS_PER_USER=5
```

## Start the Application

### Option 1: Using Make (Recommended)

```bash
# Start with auto-reload
make serve
```

### Option 2: Using Uvicorn Directly

```bash
# Start application
uv run uvicorn app:application --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Using Docker Shell

```bash
# Enter development container
make shell

# Inside container
uvicorn app:application --host 0.0.0.0 --reload
```

## Verify Installation

### Check Application Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development"
}
```

### Access API Documentation

Open in your browser:

- **OpenAPI/Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Access Monitoring Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
  - FastAPI Metrics dashboard
  - Application Logs dashboard
  - Keycloak Metrics dashboard
- **Prometheus**: http://localhost:9090
- **Traefik Dashboard**: http://localhost:8080

## Development Tools

### Pre-commit Hooks

Install pre-commit hooks for code quality:

```bash
# Install pre-commit
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

### Code Quality Checks

```bash
# Run linter
make ruff-check

# Run security scan
make bandit-scan

# Check for dead code
make dead-code-scan

# Run tests
make test

# Run tests with coverage
make test-coverage
```

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker compose -f docker/docker-compose.yml logs

# Restart services
make stop
make start
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check database logs
docker logs hw-db

# Recreate database
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d hw-db
make migrate
```

### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Stop conflicting process or change port
uvicorn app:application --port 8001
```

### Redis Connection Issues

```bash
# Test Redis connection
docker exec hw-redis redis-cli ping

# Check Redis logs
docker logs hw-redis
```

## Next Steps

Now that you have everything installed:

1. **[Quick Start Guide](quickstart.md)** - Create your first endpoints
2. **[Configuration Guide](configuration.md)** - Customize your setup
3. **[Authentication Guide](../guides/authentication.md)** - Set up auth

## Clean Up

When you're done developing:

```bash
# Stop all services
make stop

# Remove all containers and volumes
docker compose -f docker/docker-compose.yml down -v

# Clean up Docker resources
docker system prune -f
```

## Additional Resources

- [Development Guide](../development/setup.md)
- [Testing Guide](../development/testing.md)
- [Docker Deployment](../deployment/docker.md)
- [Troubleshooting Guide](../deployment/troubleshooting.md)
