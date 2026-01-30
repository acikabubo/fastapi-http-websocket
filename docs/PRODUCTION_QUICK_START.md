# Production Quick Start Guide

**TL;DR:** Get your FastAPI application running in production in 30 minutes.

## Prerequisites

- Ubuntu 22.04 server with root/sudo access
- Domain name with DNS access
- GitHub account with GITHUB_TOKEN

---

## Step 1: Prepare Server (5 minutes)

```bash
# SSH into your server
ssh user@your-server-ip

# Clone repository (or copy files)
git clone https://github.com/<username>/fastapi-http-websocket.git /opt/fastapi-app
cd /opt/fastapi-app

# Run automated setup
bash scripts/setup_production.sh
```

**What it does:**
- Installs Docker and Docker Compose
- Creates directory structure
- Generates secure passwords
- Creates `.env.production` with your domain
- Saves credentials to file

**Save the credentials shown at the end!**

---

## Step 2: Configure DNS (5 minutes)

Create these A records in your DNS provider:

```
api.example.com        → <your-server-ip>
auth.example.com       → <your-server-ip>
monitoring.example.com → <your-server-ip>
```

Wait for DNS propagation (check with `nslookup api.example.com`)

---

## Step 3: Get SSL Certificates (5 minutes)

**Option A: Let's Encrypt (Free)** ⭐ **RECOMMENDED**

```bash
# Install Certbot
sudo apt install certbot

# Get certificates (stop any service on port 80 first)
sudo certbot certonly --standalone -d api.example.com
sudo certbot certonly --standalone -d auth.example.com
sudo certbot certonly --standalone -d monitoring.example.com

# Copy certificates
sudo cp -L /etc/letsencrypt/live/api.example.com/fullchain.pem /opt/fastapi-app/ssl/api.example.com.crt
sudo cp -L /etc/letsencrypt/live/api.example.com/privkey.pem /opt/fastapi-app/ssl/api.example.com.key
# Repeat for auth and monitoring

# Fix permissions
sudo chmod 644 /opt/fastapi-app/ssl/*.crt
sudo chmod 600 /opt/fastapi-app/ssl/*.key
```

**Option B: Skip SSL for testing** ⚠️ (Not recommended)

Comment out HTTPS redirect in `nginx.conf` and use HTTP only.

---

## Step 4: Deploy Application (10 minutes)

```bash
cd /opt/fastapi-app

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

# Pull production image
docker pull ghcr.io/<username>/fastapi-http-websocket:latest

# Copy docker-compose and configs from repository
# You should have these files:
ls -la docker-compose.production.yml nginx.conf prometheus.yml alerts.yml loki-config.yml alloy-config.alloy

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f app
```

**Wait 1-2 minutes for services to start**

---

## Step 5: Configure Keycloak (5 minutes)

1. **Access Keycloak:**
   ```
   URL: https://auth.example.com
   Username: admin
   Password: (from CREDENTIALS.txt)
   ```

2. **Create Realm:**
   - Click "Add realm"
   - Name: `production-realm`
   - Click "Create"

3. **Create Client:**
   - Clients → Create
   - Client ID: `fastapi-production`
   - Client Protocol: `openid-connect`
   - Save
   - Settings:
     - Access Type: `public`
     - Valid Redirect URIs: `https://api.example.com/*`
     - Web Origins: `https://api.example.com`
   - Save

4. **Create Roles:**
   - Roles → Add Role
   - Create: `admin`, `get-authors`, `create-author`

5. **Create User:**
   - Users → Add user
   - Username: `testuser`
   - Email: `test@example.com`
   - Save
   - Credentials tab → Set password (Temporary: OFF)
   - Role Mappings → Assign roles

---

## Step 6: Verify Deployment (2 minutes)

```bash
# Test health endpoint
curl https://api.example.com/health

# Expected: {"status": "healthy"}

# Test metrics
curl https://api.example.com/metrics

# Get test token
TOKEN=$(python scripts/get_token.py testuser password | grep -A1 "Access Token" | tail -1 | xargs)

# Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/authors

# Test WebSocket (if wscat installed)
wscat -c "wss://api.example.com/web?Authorization=Bearer%20$TOKEN"
```

---

## Step 7: Configure Monitoring (3 minutes)

1. **Access Grafana:**
   ```
   URL: https://monitoring.example.com
   Username: admin
   Password: (from CREDENTIALS.txt)
   ```

2. **Add Data Sources:**
   - Configuration → Data Sources → Add
   - Prometheus: `http://prometheus:9090`
   - Loki: `http://loki:3100`
   - PostgreSQL: `hw-db:5432` (for audit logs)

3. **Import Dashboards:**
   - Dashboards → Import
   - Upload JSON files from `docker/grafana/provisioning/dashboards/`:
     - `fastapi-metrics.json`
     - `keycloak-metrics.json`
     - `application-logs.json`
     - `audit-logs.json`

---

## Production Checklist

After deployment, verify:

- [x] Application responds: `curl https://api.example.com/health`
- [x] HTTPS works (no certificate errors)
- [x] Keycloak login works
- [x] Authentication works (get token, call API)
- [x] WebSocket connects successfully
- [x] Grafana dashboards show data
- [x] Prometheus metrics available
- [x] Logs appear in Loki
- [x] Credentials saved in password manager
- [x] Backups configured (see below)

---

## Quick Operations

### View Logs
```bash
# Application logs
docker-compose -f docker-compose.production.yml logs -f app

# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f hw-keycloak
```

### Restart Service
```bash
# Restart application only
docker-compose -f docker-compose.production.yml restart app

# Restart all services
docker-compose -f docker-compose.production.yml restart
```

### Update Application
```bash
# Pull latest image
docker pull ghcr.io/<username>/fastapi-http-websocket:latest

# Recreate app container
docker-compose -f docker-compose.production.yml up -d --force-recreate --no-deps app
```

### Backup Database
```bash
# Run backup script
bash scripts/backup_db.sh

# Manual backup
docker-compose -f docker-compose.production.yml exec hw-db \
  pg_dump -U fastapi_prod fastapi_production | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Check Resource Usage
```bash
# All containers
docker stats

# Specific container
docker stats fastapi-app
```

---

## Common Issues

### Port Already in Use
```bash
# Check what's using port 80/443
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443

# Stop conflicting service
sudo systemctl stop apache2  # or nginx
```

### Certificate Errors
```bash
# Verify certificate files exist
ls -la /opt/fastapi-app/ssl/

# Check nginx config
docker-compose -f docker-compose.production.yml exec nginx nginx -t

# Restart nginx
docker-compose -f docker-compose.production.yml restart nginx
```

### Database Connection Failed
```bash
# Check database is running
docker-compose -f docker-compose.production.yml ps hw-db

# Check database logs
docker-compose -f docker-compose.production.yml logs hw-db

# Verify credentials in .env.production
cat .env.production | grep DB_
```

### Keycloak Not Starting
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs hw-keycloak

# Common issues:
# - Database connection (check KC_DB_URL, KC_DB_PASSWORD)
# - Port conflict (check 8080 is free)
# - Missing Keycloak database (create manually)
```

---

## Security Hardening

**After basic deployment works:**

1. **Configure Firewall:**
   ```bash
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw enable
   ```

2. **Enable Fail2Ban:**
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   ```

3. **Auto-Renew SSL:**
   ```bash
   # Add to crontab
   0 0,12 * * * certbot renew --quiet && docker-compose -f /opt/fastapi-app/docker-compose.production.yml restart nginx
   ```

4. **Configure Backups:**
   ```bash
   # Add to crontab (daily at 2 AM)
   0 2 * * * /opt/fastapi-app/scripts/backup_db.sh >> /var/log/db_backup.log 2>&1
   ```

---

## Monitoring URLs

Once deployed, access these URLs:

- **Application:** https://api.example.com
- **API Docs:** https://api.example.com/docs
- **Metrics:** https://api.example.com/metrics
- **Keycloak:** https://auth.example.com
- **Grafana:** https://monitoring.example.com
- **Prometheus:** https://monitoring.example.com:9090 (internal)

---

## Getting Help

**Logs:**
```bash
# Application
docker-compose -f docker-compose.production.yml logs app | tail -100

# Errors only
docker-compose -f docker-compose.production.yml logs app | grep -i error
```

**Health Check:**
```bash
# All services
docker-compose -f docker-compose.production.yml ps

# Check endpoints
curl https://api.example.com/health
```

**Full Documentation:**
- [Complete Production Guide](PRODUCTION_DEPLOYMENT.md)
- [Docker Registry Setup](DOCKER_REGISTRY.md)
- [Build Testing](DOCKER_BUILD_TESTING.md)

---

## Estimated Timeline

- **Server Prep:** 5 minutes
- **DNS Configuration:** 5 minutes
- **SSL Certificates:** 5 minutes
- **Deploy Application:** 10 minutes
- **Configure Keycloak:** 5 minutes
- **Verify + Monitor:** 5 minutes

**Total: ~30-35 minutes** ⏱️

---

## What's Included

Your production environment includes:

✅ FastAPI application with WebSocket support
✅ PostgreSQL database with automated backups
✅ Redis caching and rate limiting
✅ Keycloak authentication server
✅ Prometheus metrics collection
✅ Grafana monitoring dashboards
✅ Loki log aggregation
✅ Nginx reverse proxy with SSL
✅ Automatic SSL certificate renewal
✅ Health checks and auto-restart
✅ Audit logging to database
✅ Circuit breakers for resilience

---

**Ready to deploy? Start with Step 1! 🚀**
