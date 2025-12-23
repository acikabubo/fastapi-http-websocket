# Docker Deployment Guide

This guide covers Docker-specific deployment configurations, best practices, and optimization techniques for the FastAPI HTTP/WebSocket application.

## Table of Contents

- [Dockerfile Best Practices](#dockerfile-best-practices)
- [Multi-Stage Builds](#multi-stage-builds)
- [Docker Compose Production](#docker-compose-production)
- [Image Optimization](#image-optimization)
- [Security Hardening](#security-hardening)
- [Health Checks](#health-checks)
- [Resource Limits](#resource-limits)
- [Networking](#networking)

## Dockerfile Best Practices

### Production Dockerfile

Create `docker/Dockerfile.production`:

```dockerfile
# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create wheel directory
WORKDIR /wheels

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ============================================
# Stage 2: Runtime - Minimal production image
# ============================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install Python packages from wheels
RUN pip install --no-cache --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app:application", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-config", "/app/uvicorn_logging.json"]
```

### Key Features

1. **Multi-stage build**: Separates build and runtime dependencies (smaller image)
2. **Non-root user**: Runs as `appuser` (UID 1000) for security
3. **Minimal base**: Uses `slim` variant to reduce attack surface
4. **Health check**: Built-in Docker health monitoring
5. **Optimized layers**: Leverages Docker layer caching

## Multi-Stage Builds

### Why Multi-Stage?

- **Smaller images**: Build dependencies (gcc, build-essential) not in final image
- **Faster deployment**: Less data to push/pull
- **Better security**: Fewer packages = smaller attack surface

### Build Process

```bash
# Build production image
docker build -f docker/Dockerfile.production -t fastapi-app:1.0.0 .

# Check image size
docker images fastapi-app:1.0.0

# Expected: ~300-400MB (vs ~800MB+ without multi-stage)
```

### Layer Optimization

```dockerfile
# ❌ BAD: Changes to code trigger full rebuild
COPY . .
RUN pip install -r requirements.txt

# ✅ GOOD: Dependencies cached separately
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

## Docker Compose Production

### Production Compose File

Create `docker/docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  hw-server:
    image: fastapi-app:${VERSION:-latest}
    container_name: hw-server-prod
    hostname: hw-server

    networks:
      - hw-network

    # No exposed ports - only accessible via Traefik
    expose:
      - "8000"

    # Production volume (code built into image)
    volumes:
      - /var/log/fastapi:/app/logs

    # Run as non-root user
    user: "1000:1000"

    env_file:
      - ../.env.production
      - .srv_env.production

    # Resource limits
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    depends_on:
      hw-db:
        condition: service_healthy
      hw-redis:
        condition: service_healthy
      hw-keycloak:
        condition: service_healthy
      traefik:
        condition: service_healthy

    restart: unless-stopped

    # Security options
    security_opt:
      - no-new-privileges:true

    # Read-only root filesystem (logs volume is writable)
    read_only: true
    tmpfs:
      - /tmp

    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  hw-db:
    image: postgres:13
    container_name: hw-db-prod

    networks:
      - hw-network

    # Only expose to internal network
    expose:
      - "5432"

    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./backups:/backups

    env_file:
      - .pg_env.production

    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

    restart: unless-stopped

    # PostgreSQL tuning
    command: >
      postgres
      -c shared_buffers=2GB
      -c effective_cache_size=6GB
      -c maintenance_work_mem=512MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c work_mem=16MB
      -c min_wal_size=1GB
      -c max_wal_size=4GB
      -c max_connections=100

  hw-redis:
    image: redis:7-alpine
    container_name: hw-redis-prod

    networks:
      - hw-network

    expose:
      - "6379"

    volumes:
      - redis-data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf:ro

    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

    command: redis-server /usr/local/etc/redis/redis.conf

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s

    restart: unless-stopped

networks:
  hw-network:
    name: hw-network-prod
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16

volumes:
  postgres-data:
    name: postgres-prod-data
  redis-data:
    name: redis-prod-data
  prometheus-data:
    name: prometheus-prod-data
  grafana-data:
    name: grafana-prod-data
  loki-data:
    name: loki-prod-data
  traefik-certificates:
    name: traefik-prod-certs
```

## Image Optimization

### Size Reduction Techniques

1. **Use Alpine base images** (where possible):
   ```dockerfile
   FROM python:3.11-alpine
   # But beware: Some packages need build dependencies
   ```

2. **Multi-stage builds** (as shown above)

3. **Remove build artifacts**:
   ```dockerfile
   RUN pip install -r requirements.txt \
       && pip cache purge \
       && rm -rf /root/.cache
   ```

4. **Minimize layers**:
   ```dockerfile
   # ❌ BAD: 3 layers
   RUN apt-get update
   RUN apt-get install -y curl
   RUN rm -rf /var/lib/apt/lists/*

   # ✅ GOOD: 1 layer
   RUN apt-get update && apt-get install -y curl \
       && rm -rf /var/lib/apt/lists/*
   ```

5. **Use .dockerignore**:
   ```
   # .dockerignore
   __pycache__
   *.pyc
   *.pyo
   *.pyd
   .Python
   env/
   venv/
   .git
   .gitignore
   .env
   .env.*
   docker-compose*.yml
   Dockerfile*
   README.md
   tests/
   docs/
   .pytest_cache
   .coverage
   htmlcov/
   ```

### Build Cache Optimization

```bash
# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker build -t fastapi-app:latest .

# Use cache from registry
docker build --cache-from fastapi-app:latest -t fastapi-app:1.0.1 .
```

## Security Hardening

### 1. Non-Root User

```dockerfile
# Create user with specific UID
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set ownership
COPY --chown=appuser:appuser . .

# Switch to user
USER appuser
```

### 2. Read-Only Root Filesystem

```yaml
# docker-compose.yml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### 3. Drop Capabilities

```yaml
services:
  app:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if binding to port < 1024
```

### 4. Security Options

```yaml
services:
  app:
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
      - seccomp:unconfined  # Only if needed
```

### 5. Secrets Management

```yaml
# Use Docker secrets (Swarm mode)
services:
  app:
    secrets:
      - db_password
      - api_key

secrets:
  db_password:
    external: true
  api_key:
    external: true
```

```python
# Read secrets in app
with open('/run/secrets/db_password', 'r') as f:
    db_password = f.read().strip()
```

## Health Checks

### Application Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### FastAPI Health Endpoint

```python
# app/api/http/health.py
from fastapi import APIRouter, Response, status
from app.storage.db import async_session
from app.storage.redis import RRedis

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Checks:
    - Application is running
    - Database connection
    - Redis connection
    """
    checks = {
        "status": "healthy",
        "checks": {}
    }

    # Database check
    try:
        async with async_session() as session:
            await session.execute("SELECT 1")
        checks["checks"]["database"] = "healthy"
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["checks"]["database"] = f"unhealthy: {str(e)}"

    # Redis check
    try:
        redis = RRedis()
        await redis.ping()
        checks["checks"]["redis"] = "healthy"
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["checks"]["redis"] = f"unhealthy: {str(e)}"

    status_code = status.HTTP_200_OK if checks["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        content=json.dumps(checks),
        status_code=status_code,
        media_type="application/json"
    )
```

### Monitoring Health Status

```bash
# Check container health
docker ps --filter health=healthy
docker ps --filter health=unhealthy

# Inspect health status
docker inspect --format='{{json .State.Health}}' hw-server | jq
```

## Resource Limits

### Memory Limits

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G  # Hard limit
        reservations:
          memory: 1G  # Minimum guaranteed
```

### CPU Limits

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'  # Max 2 CPUs
        reservations:
          cpus: '1.0'  # Min 1 CPU
```

### Monitoring Resource Usage

```bash
# Real-time stats
docker stats

# Specific container
docker stats hw-server

# Export stats
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" > stats.txt
```

## Networking

### Bridge Network (Default)

```yaml
networks:
  hw-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16
```

### Custom Network Settings

```yaml
services:
  app:
    networks:
      hw-network:
        ipv4_address: 172.25.0.10
        aliases:
          - api
          - fastapi-app
```

### Network Isolation

```yaml
# Public network (Traefik)
networks:
  public:
    external: true

# Private network (backend services)
networks:
  private:
    internal: true  # No external access

services:
  traefik:
    networks:
      - public

  app:
    networks:
      - public
      - private

  db:
    networks:
      - private  # Only accessible from app
```

## Logging

### JSON Logging Driver

```yaml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "production,fastapi"
```

### Centralized Logging

```yaml
# Use Loki driver (requires plugin)
services:
  app:
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        loki-external-labels: "job=fastapi,environment=production"
```

## Build and Deploy Workflow

### CI/CD Pipeline Example

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          docker build -f docker/Dockerfile.production \
            -t ghcr.io/user/fastapi-app:${{ github.sha }} \
            -t ghcr.io/user/fastapi-app:latest .

      - name: Push to registry
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push ghcr.io/user/fastapi-app:${{ github.sha }}
          docker push ghcr.io/user/fastapi-app:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          ssh user@prod-server "cd /app && \
            export VERSION=${{ github.sha }} && \
            docker-compose -f docker-compose.prod.yml pull && \
            docker-compose -f docker-compose.prod.yml up -d"
```

## Troubleshooting

### Common Issues

**Issue: Container exits immediately**
```bash
# Check logs
docker logs hw-server

# Check exit code
docker inspect hw-server --format='{{.State.ExitCode}}'
```

**Issue: Permission denied**
```bash
# Check user
docker exec hw-server whoami

# Check file ownership
docker exec hw-server ls -la /app
```

**Issue: Out of memory**
```bash
# Check memory usage
docker stats hw-server

# Increase limit in docker-compose.yml
```

**Issue: Cannot connect to service**
```bash
# Check network
docker network inspect hw-network

# Check if service is running
docker-compose ps
```

## Best Practices Summary

✅ **DO**:
- Use multi-stage builds
- Run as non-root user
- Set resource limits
- Implement health checks
- Use .dockerignore
- Pin base image versions
- Use BuildKit
- Scan images for vulnerabilities

❌ **DON'T**:
- Run as root
- Store secrets in images
- Use `latest` tag in production
- Ignore security updates
- Over-allocate resources
- Skip health checks

## Additional Resources

- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Compose Production](https://docs.docker.com/compose/production/)
