# Production Deployment Guide

Complete guide for deploying the FastAPI WebSocket application to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Registry Configuration](#docker-registry-configuration)
4. [Database Setup](#database-setup)
5. [Keycloak Configuration](#keycloak-configuration)
6. [Application Deployment](#application-deployment)
7. [Monitoring Setup](#monitoring-setup)
8. [Security Hardening](#security-hardening)
9. [SSL/TLS Configuration](#ssltls-configuration)
10. [Backup and Recovery](#backup-and-recovery)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Server Requirements

**Minimum Specifications:**
- **CPU:** 2 cores
- **RAM:** 4GB
- **Disk:** 20GB SSD
- **OS:** Ubuntu 20.04/22.04 LTS or Debian 11+

**Recommended Specifications:**
- **CPU:** 4+ cores
- **RAM:** 8GB+
- **Disk:** 50GB+ SSD
- **OS:** Ubuntu 22.04 LTS

### Software Requirements

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Install essential tools
sudo apt install -y git curl wget jq htop
```

### Domain and DNS

- Purchase domain name (e.g., `example.com`)
- Configure DNS A records:
  ```
  api.example.com       → <server-ip>
  auth.example.com      → <server-ip>
  monitoring.example.com → <server-ip>
  ```

---

## Environment Setup

### 1. Create Production Environment File

```bash
# On production server
cd /opt
sudo mkdir -p fastapi-app
cd fastapi-app

# Create .env.production
sudo nano .env.production
```

**`.env.production` template:**

```bash
# ========================================
# ENVIRONMENT
# ========================================
ENV=production
LOG_LEVEL=WARNING
LOG_CONSOLE_FORMAT=json
DEBUG=false

# ========================================
# DATABASE CONFIGURATION
# ========================================
DB_USER=fastapi_prod
DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD_HERE
DB_HOST=hw-db
DB_PORT=5432
DB_NAME=fastapi_production

# PostgreSQL settings
POSTGRES_USER=fastapi_prod
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD_HERE
POSTGRES_DB=fastapi_production

# ========================================
# REDIS CONFIGURATION
# ========================================
REDIS_IP=hw-redis
REDIS_PORT=6379
MAIN_REDIS_DB=1
AUTH_REDIS_DB=10
REDIS_MAX_CONNECTIONS=50

# ========================================
# KEYCLOAK CONFIGURATION
# ========================================
KEYCLOAK_REALM=production-realm
KEYCLOAK_CLIENT_ID=fastapi-production
KEYCLOAK_BASE_URL=https://auth.example.com
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=CHANGE_ME_ADMIN_PASSWORD_HERE

# Keycloak database
KC_DB=postgres
KC_DB_URL=jdbc:postgresql://hw-db:5432/keycloak_production
KC_DB_USERNAME=keycloak_prod
KC_DB_PASSWORD=CHANGE_ME_KC_DB_PASSWORD_HERE

# ========================================
# SECURITY SETTINGS
# ========================================
ALLOWED_HOSTS=["api.example.com", "*.example.com"]
ALLOWED_WS_ORIGINS=["https://app.example.com", "https://admin.example.com"]
MAX_REQUEST_BODY_SIZE=1048576
TRUSTED_PROXIES=["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
RATE_LIMIT_FAIL_MODE=closed
WS_MAX_CONNECTIONS_PER_USER=5
WS_MESSAGE_RATE_LIMIT=100

# ========================================
# CIRCUIT BREAKER SETTINGS
# ========================================
CIRCUIT_BREAKER_ENABLED=true
KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX=5
KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT=60
REDIS_CIRCUIT_BREAKER_FAIL_MAX=3
REDIS_CIRCUIT_BREAKER_TIMEOUT=30

# ========================================
# AUDIT LOGGING
# ========================================
AUDIT_LOG_ENABLED=true
AUDIT_QUEUE_MAX_SIZE=10000
AUDIT_BATCH_SIZE=100
AUDIT_BATCH_TIMEOUT=1.0
AUDIT_QUEUE_TIMEOUT=1.0

# ========================================
# MONITORING
# ========================================
PROFILING_ENABLED=false
PROMETHEUS_ENABLED=true
LOKI_URL=http://loki:3100

# ========================================
# APPLICATION SETTINGS
# ========================================
WORKERS=4
MAX_CONNECTIONS=1000
KEEP_ALIVE=5
```

### 2. Secure Environment File

```bash
# Set strict permissions
sudo chmod 600 .env.production
sudo chown root:root .env.production
```

### 3. Generate Strong Passwords

```bash
# Generate random passwords
openssl rand -base64 32  # For DB_PASSWORD
openssl rand -base64 32  # For KEYCLOAK_ADMIN_PASSWORD
openssl rand -base64 32  # For KC_DB_PASSWORD
```

---

## Docker Registry Configuration

### 1. Pull Production Image

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

# Pull latest production image
docker pull ghcr.io/<username>/fastapi-http-websocket:latest
```

### 2. Create docker-compose.production.yml

```yaml
# /opt/fastapi-app/docker-compose.production.yml
version: '3.8'

services:
  # ========================================
  # APPLICATION
  # ========================================
  app:
    image: ghcr.io/<username>/fastapi-http-websocket:latest
    container_name: fastapi-app
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    depends_on:
      hw-db:
        condition: service_healthy
      hw-redis:
        condition: service_healthy
      hw-keycloak:
        condition: service_started
    networks:
      - app-network
    volumes:
      - app-logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ========================================
  # DATABASE
  # ========================================
  hw-db:
    image: postgres:13-alpine
    container_name: hw-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ========================================
  # REDIS
  # ========================================
  hw-redis:
    image: redis:7-alpine
    container_name: hw-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ========================================
  # KEYCLOAK
  # ========================================
  hw-keycloak:
    image: quay.io/keycloak/keycloak:latest
    container_name: hw-keycloak
    restart: unless-stopped
    environment:
      KC_DB: ${KC_DB}
      KC_DB_URL: ${KC_DB_URL}
      KC_DB_USERNAME: ${KC_DB_USERNAME}
      KC_DB_PASSWORD: ${KC_DB_PASSWORD}
      KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN_USERNAME}
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
      KC_HOSTNAME: auth.example.com
      KC_PROXY: edge
      KC_HTTP_ENABLED: true
      KC_METRICS_ENABLED: true
    command: start --optimized
    ports:
      - "8080:8080"
    depends_on:
      hw-db:
        condition: service_healthy
    networks:
      - app-network
    volumes:
      - keycloak-data:/opt/keycloak/data
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ========================================
  # MONITORING - PROMETHEUS
  # ========================================
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - app-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ========================================
  # MONITORING - GRAFANA
  # ========================================
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
      GF_INSTALL_PLUGINS: grafana-clock-panel
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    networks:
      - app-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ========================================
  # LOGGING - LOKI
  # ========================================
  loki:
    image: grafana/loki:latest
    container_name: loki
    restart: unless-stopped
    command: -config.file=/etc/loki/loki-config.yml
    volumes:
      - ./loki-config.yml:/etc/loki/loki-config.yml:ro
      - loki-data:/loki
    ports:
      - "3100:3100"
    networks:
      - app-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ========================================
  # LOGGING - ALLOY (Log Collector)
  # ========================================
  alloy:
    image: grafana/alloy:latest
    container_name: alloy
    restart: unless-stopped
    command:
      - run
      - /etc/alloy/config.alloy
      - --storage.path=/var/lib/alloy/data
    volumes:
      - ./alloy-config.alloy:/etc/alloy/config.alloy:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - alloy-data:/var/lib/alloy/data
    ports:
      - "12345:12345"
    networks:
      - app-network
    depends_on:
      - loki
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ========================================
  # REVERSE PROXY - NGINX
  # ========================================
  nginx:
    image: nginx:alpine
    container_name: nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx-logs:/var/log/nginx
    depends_on:
      - app
      - grafana
      - hw-keycloak
    networks:
      - app-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  app-network:
    driver: bridge

volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local
  keycloak-data:
    driver: local
  prometheus-data:
    driver: local
  grafana-data:
    driver: local
  loki-data:
    driver: local
  alloy-data:
    driver: local
  app-logs:
    driver: local
  nginx-logs:
    driver: local
```

---

## Database Setup

### 1. Initialize Databases

```bash
# Start only database
docker-compose -f docker-compose.production.yml up -d hw-db

# Wait for database to be ready
docker-compose -f docker-compose.production.yml exec hw-db pg_isready -U fastapi_prod

# Create Keycloak database
docker-compose -f docker-compose.production.yml exec hw-db psql -U fastapi_prod -c "CREATE DATABASE keycloak_production;"
docker-compose -f docker-compose.production.yml exec hw-db psql -U fastapi_prod -c "CREATE USER keycloak_prod WITH PASSWORD 'CHANGE_ME_KC_DB_PASSWORD_HERE';"
docker-compose -f docker-compose.production.yml exec hw-db psql -U fastapi_prod -c "GRANT ALL PRIVILEGES ON DATABASE keycloak_production TO keycloak_prod;"
```

### 2. Run Database Migrations

```bash
# Start app container temporarily
docker-compose -f docker-compose.production.yml run --rm app bash

# Inside container - run migrations
alembic upgrade head

# Exit container
exit
```

### 3. Database Backup Configuration

Create backup script:

```bash
# /opt/fastapi-app/scripts/backup_db.sh
#!/bin/bash
BACKUP_DIR="/opt/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup main database
docker-compose -f /opt/fastapi-app/docker-compose.production.yml exec -T hw-db \
  pg_dump -U fastapi_prod fastapi_production | gzip > "$BACKUP_DIR/fastapi_$DATE.sql.gz"

# Backup Keycloak database
docker-compose -f /opt/fastapi-app/docker-compose.production.yml exec -T hw-db \
  pg_dump -U keycloak_prod keycloak_production | gzip > "$BACKUP_DIR/keycloak_$DATE.sql.gz"

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Setup cron job:

```bash
# Make script executable
chmod +x /opt/fastapi-app/scripts/backup_db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line:
0 2 * * * /opt/fastapi-app/scripts/backup_db.sh >> /var/log/db_backup.log 2>&1
```

---

## Keycloak Configuration

### 1. Initial Keycloak Setup

```bash
# Start Keycloak
docker-compose -f docker-compose.production.yml up -d hw-keycloak

# Access Keycloak admin console
# https://auth.example.com
# Login with KEYCLOAK_ADMIN credentials
```

### 2. Create Production Realm

1. **Create Realm:**
   - Click "Add realm"
   - Name: `production-realm`
   - Enabled: ON

2. **Configure Realm Settings:**
   - Login → Email as username: OFF
   - Login → User registration: OFF (or ON if public registration needed)
   - Tokens → Access Token Lifespan: 5 minutes
   - Tokens → Refresh Token Max Reuse: 0

### 3. Create Client

1. **Create Client:**
   - Client ID: `fastapi-production`
   - Client Protocol: `openid-connect`
   - Access Type: `public`
   - Valid Redirect URIs: `https://api.example.com/*`
   - Web Origins: `https://api.example.com`

2. **Client Scopes:**
   - Add roles scope
   - Add email scope
   - Add profile scope

### 4. Create Roles

```
Roles to create:
- admin
- get-authors
- create-author
- update-author
- delete-author
- view-books
- create-book
- update-book
- delete-book
```

### 5. Create Users

1. **Create Admin User:**
   - Username: `admin`
   - Email: `admin@example.com`
   - Email Verified: ON
   - Credentials → Set Password (temporary: OFF)
   - Role Mappings → Assign `admin` role

2. **Create Regular Users:**
   - Repeat process for each user
   - Assign appropriate roles

---

## Application Deployment

### 1. Deploy All Services

```bash
cd /opt/fastapi-app

# Pull latest images
docker-compose -f docker-compose.production.yml pull

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f app
```

### 2. Verify Deployment

```bash
# Check application health
curl http://localhost:8000/health

# Check Prometheus metrics
curl http://localhost:8000/metrics

# Test WebSocket connection
wscat -c "ws://localhost:8000/web?Authorization=Bearer <token>"
```

### 3. Configure Auto-Start on Boot

```bash
# Create systemd service
sudo nano /etc/systemd/system/fastapi-app.service
```

**Service file content:**

```ini
[Unit]
Description=FastAPI Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/fastapi-app
ExecStart=/usr/bin/docker-compose -f docker-compose.production.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.production.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi-app.service
sudo systemctl start fastapi-app.service
sudo systemctl status fastapi-app.service
```

---

## Monitoring Setup

### 1. Grafana Configuration

Access Grafana: `http://monitoring.example.com:3000`

1. **Login:** admin / (GRAFANA_ADMIN_PASSWORD)
2. **Add Data Sources:**
   - Prometheus: http://prometheus:9090
   - Loki: http://loki:3100
   - PostgreSQL: hw-db:5432 (for audit logs)

3. **Import Dashboards:**
   - Copy dashboard JSON files from `docker/grafana/provisioning/dashboards/`
   - Import via Grafana UI

### 2. Prometheus Alerts

Alerts are configured in `alerts.yml` and automatically loaded.

**Key alerts:**
- High error rate (>5%)
- Database down
- Redis down
- High WebSocket rejections
- Audit log dropping

### 3. Log Aggregation

Logs are automatically collected by Alloy and sent to Loki.

**View logs in Grafana:**
- Go to Explore
- Select Loki data source
- Query: `{service="fastapi-app"}`

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

### 2. Fail2Ban for SSH

```bash
# Install Fail2Ban
sudo apt install fail2ban

# Configure
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local

# Enable and start
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Docker Security

```bash
# Enable Docker Content Trust (image signing)
export DOCKER_CONTENT_TRUST=1

# Limit container resources
# Add to docker-compose.production.yml:
# services:
#   app:
#     deploy:
#       resources:
#         limits:
#           cpus: '2'
#           memory: 2G
```

### 4. Application Security Checklist

- [x] DEBUG mode disabled (ENV=production)
- [x] Strong passwords in .env.production
- [x] ALLOWED_HOSTS configured
- [x] ALLOWED_WS_ORIGINS restricted
- [x] Rate limiting enabled
- [x] CORS properly configured
- [x] Security headers middleware enabled
- [x] Request size limits enforced
- [x] Audit logging enabled
- [x] JWT tokens expire (5 minutes)
- [x] HTTPS only (no HTTP)
- [x] Database credentials secured

---

## SSL/TLS Configuration

### 1. Obtain SSL Certificates

**Option A: Let's Encrypt (Free)**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificates
sudo certbot certonly --standalone -d api.example.com
sudo certbot certonly --standalone -d auth.example.com
sudo certbot certonly --standalone -d monitoring.example.com

# Certificates stored in:
# /etc/letsencrypt/live/api.example.com/fullchain.pem
# /etc/letsencrypt/live/api.example.com/privkey.pem
```

**Option B: Custom Certificates**

Place certificates in `/opt/fastapi-app/ssl/`:
```
ssl/
  ├── api.example.com.crt
  ├── api.example.com.key
  ├── auth.example.com.crt
  ├── auth.example.com.key
  ├── monitoring.example.com.crt
  └── monitoring.example.com.key
```

### 2. Configure Nginx

Create `/opt/fastapi-app/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ws_limit:10m rate=5r/s;

    # Upstream backends
    upstream fastapi_backend {
        server app:8000;
    }

    upstream keycloak_backend {
        server hw-keycloak:8080;
    }

    upstream grafana_backend {
        server grafana:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name api.example.com auth.example.com monitoring.example.com;
        return 301 https://$host$request_uri;
    }

    # API Server
    server {
        listen 443 ssl http2;
        server_name api.example.com;

        ssl_certificate /etc/nginx/ssl/api.example.com.crt;
        ssl_certificate_key /etc/nginx/ssl/api.example.com.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 1M;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;

        # API endpoints
        location / {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://fastapi_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket endpoint
        location /web {
            limit_req zone=ws_limit burst=10 nodelay;
            proxy_pass http://fastapi_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 86400;
        }
    }

    # Keycloak Server
    server {
        listen 443 ssl http2;
        server_name auth.example.com;

        ssl_certificate /etc/nginx/ssl/auth.example.com.crt;
        ssl_certificate_key /etc/nginx/ssl/auth.example.com.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location / {
            proxy_pass http://keycloak_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # Grafana Monitoring
    server {
        listen 443 ssl http2;
        server_name monitoring.example.com;

        ssl_certificate /etc/nginx/ssl/monitoring.example.com.crt;
        ssl_certificate_key /etc/nginx/ssl/monitoring.example.com.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location / {
            proxy_pass http://grafana_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 3. Reload Nginx

```bash
# Test configuration
docker-compose -f docker-compose.production.yml exec nginx nginx -t

# Reload Nginx
docker-compose -f docker-compose.production.yml restart nginx
```

### 4. Auto-Renew Certificates (Let's Encrypt)

```bash
# Add cron job for auto-renewal
crontab -e

# Add line (runs twice daily):
0 0,12 * * * certbot renew --quiet && docker-compose -f /opt/fastapi-app/docker-compose.production.yml restart nginx
```

---

## Backup and Recovery

### 1. Backup Strategy

**What to backup:**
- Database (PostgreSQL)
- Redis data (if persistence enabled)
- Keycloak data
- Application logs
- Environment configuration
- SSL certificates

### 2. Automated Backup Script

```bash
#!/bin/bash
# /opt/fastapi-app/scripts/full_backup.sh

BACKUP_ROOT="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$DATE"

mkdir -p "$BACKUP_DIR"

# Backup databases
docker-compose -f /opt/fastapi-app/docker-compose.production.yml exec -T hw-db \
  pg_dumpall -U fastapi_prod | gzip > "$BACKUP_DIR/databases.sql.gz"

# Backup Redis
docker-compose -f /opt/fastapi-app/docker-compose.production.yml exec -T hw-redis \
  redis-cli SAVE
cp /opt/fastapi-app/redis-data/dump.rdb "$BACKUP_DIR/redis_dump.rdb"

# Backup configuration
cp /opt/fastapi-app/.env.production "$BACKUP_DIR/env.production"
cp -r /opt/fastapi-app/ssl "$BACKUP_DIR/ssl"

# Backup application logs
cp -r /opt/fastapi-app/app-logs "$BACKUP_DIR/logs"

# Create tarball
tar -czf "$BACKUP_ROOT/backup_$DATE.tar.gz" -C "$BACKUP_ROOT" "$DATE"
rm -rf "$BACKUP_DIR"

# Upload to S3 (optional)
# aws s3 cp "$BACKUP_ROOT/backup_$DATE.tar.gz" s3://my-backups/fastapi/

# Keep only last 30 days
find "$BACKUP_ROOT" -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

### 3. Recovery Procedure

```bash
# Stop services
docker-compose -f docker-compose.production.yml down

# Restore database
gunzip < backup_databases.sql.gz | docker-compose -f docker-compose.production.yml exec -T hw-db psql -U fastapi_prod

# Restore Redis
cp backup_redis_dump.rdb /opt/fastapi-app/redis-data/dump.rdb

# Restore configuration
cp backup_env.production /opt/fastapi-app/.env.production

# Start services
docker-compose -f docker-compose.production.yml up -d
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check logs
docker-compose -f docker-compose.production.yml logs app

# Common issues:
# - Database connection failed → Check DB_HOST, DB_PASSWORD
# - Keycloak connection failed → Check KEYCLOAK_BASE_URL
# - Missing environment variable → Review .env.production
```

### High Memory Usage

```bash
# Check container memory
docker stats

# Limit container resources
# Edit docker-compose.production.yml:
# services:
#   app:
#     deploy:
#       resources:
#         limits:
#           memory: 2G
```

### Database Connection Pool Exhausted

```bash
# Increase pool size in settings
# Edit .env.production:
# DB_POOL_SIZE=20
# DB_MAX_OVERFLOW=10
```

### WebSocket Connections Dropping

```bash
# Check nginx timeout
# Edit nginx.conf:
# proxy_read_timeout 86400;

# Check application logs
docker-compose -f docker-compose.production.yml logs app | grep -i websocket
```

---

## Update Deployment

### Rolling Update (Zero Downtime)

```bash
# Pull latest image
docker pull ghcr.io/<username>/fastapi-http-websocket:latest

# Recreate containers
docker-compose -f docker-compose.production.yml up -d --force-recreate --no-deps app

# Verify
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs -f app
```

### Rollback

```bash
# Use previous image tag
docker pull ghcr.io/<username>/fastapi-http-websocket:main-<previous-sha>
docker tag ghcr.io/<username>/fastapi-http-websocket:main-<previous-sha> ghcr.io/<username>/fastapi-http-websocket:latest
docker-compose -f docker-compose.production.yml up -d --force-recreate --no-deps app
```

---

## Production Checklist

Before going live:

- [ ] All passwords changed from defaults
- [ ] SSL certificates installed and configured
- [ ] Firewall rules configured
- [ ] Database backups automated
- [ ] Monitoring dashboards configured
- [ ] Log retention policy set
- [ ] Rate limiting tested
- [ ] Health checks responding
- [ ] Grafana alerts configured
- [ ] DNS records pointing to server
- [ ] Keycloak realm and users created
- [ ] Application tested end-to-end
- [ ] Documentation reviewed
- [ ] Emergency contact list prepared
- [ ] Rollback procedure tested

---

## Support and Maintenance

### Daily Tasks
- Check Grafana dashboards for anomalies
- Review error logs

### Weekly Tasks
- Review disk space usage
- Check backup success
- Review security scan results

### Monthly Tasks
- Update Docker images
- Review and rotate logs
- Security audit
- Performance review

---

## Additional Resources

- [Docker Registry Documentation](DOCKER_REGISTRY.md)
- [Build Testing Guide](DOCKER_BUILD_TESTING.md)
- [Application Documentation](../README.md)
- [CLAUDE.md](../CLAUDE.md)
