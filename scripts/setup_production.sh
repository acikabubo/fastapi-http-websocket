#!/bin/bash
# Production Environment Setup Script
# Run this on your production server to configure the environment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "========================================="
echo "   FastAPI Production Setup"
echo "========================================="
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Please do not run this script as root${NC}"
    echo "   Run as regular user with sudo access"
    exit 1
fi

# Function to generate random password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Check prerequisites
echo -e "\n${BLUE}📋 Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker not found. Installing...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✅ Docker installed${NC}"
else
    echo -e "${GREEN}✅ Docker installed${NC}"
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker Compose plugin not found. Installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    echo -e "${GREEN}✅ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✅ Docker Compose installed${NC}"
fi

# Create directory structure
echo -e "\n${BLUE}📁 Creating directory structure...${NC}"
sudo mkdir -p /opt/fastapi-app/{ssl,scripts,config}
sudo mkdir -p /opt/backups/{postgres,full}
sudo chown -R $USER:$USER /opt/fastapi-app
sudo chown -R $USER:$USER /opt/backups
echo -e "${GREEN}✅ Directories created${NC}"

# Generate passwords
echo -e "\n${BLUE}🔐 Generating secure passwords...${NC}"
DB_PASSWORD=$(generate_password)
KEYCLOAK_ADMIN_PASSWORD=$(generate_password)
KC_DB_PASSWORD=$(generate_password)
GRAFANA_ADMIN_PASSWORD=$(generate_password)

echo -e "${GREEN}✅ Passwords generated${NC}"

# Get user input
echo -e "\n${BLUE}📝 Configuration${NC}"
read -p "Enter your domain (e.g., example.com): " DOMAIN
read -p "Enter GitHub username (for Docker registry): " GITHUB_USER
read -p "Enter database name [fastapi_production]: " DB_NAME
DB_NAME=${DB_NAME:-fastapi_production}

# Create .env.production
echo -e "\n${BLUE}📄 Creating .env.production...${NC}"
cat > /opt/fastapi-app/.env.production << EOF
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
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=hw-db
DB_PORT=5432
DB_NAME=${DB_NAME}

# PostgreSQL settings
POSTGRES_USER=fastapi_prod
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=${DB_NAME}

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
KEYCLOAK_BASE_URL=https://auth.${DOMAIN}
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD}

# Keycloak database
KC_DB=postgres
KC_DB_URL=jdbc:postgresql://hw-db:5432/keycloak_production
KC_DB_USERNAME=keycloak_prod
KC_DB_PASSWORD=${KC_DB_PASSWORD}

# ========================================
# SECURITY SETTINGS
# ========================================
ALLOWED_HOSTS=["api.${DOMAIN}", "*.${DOMAIN}"]
ALLOWED_WS_ORIGINS=["https://app.${DOMAIN}", "https://admin.${DOMAIN}"]
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

# Grafana
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}

# ========================================
# APPLICATION SETTINGS
# ========================================
WORKERS=4
MAX_CONNECTIONS=1000
KEEP_ALIVE=5
EOF

chmod 600 /opt/fastapi-app/.env.production
echo -e "${GREEN}✅ .env.production created${NC}"

# Save credentials to secure file
CREDENTIALS_FILE="/opt/fastapi-app/CREDENTIALS.txt"
cat > ${CREDENTIALS_FILE} << EOF
========================================
   FastAPI Production Credentials
========================================
Generated: $(date)

Database:
  User: fastapi_prod
  Password: ${DB_PASSWORD}
  Database: ${DB_NAME}

Keycloak:
  Admin User: admin
  Admin Password: ${KEYCLOAK_ADMIN_PASSWORD}
  URL: https://auth.${DOMAIN}

Keycloak Database:
  User: keycloak_prod
  Password: ${KC_DB_PASSWORD}

Grafana:
  Admin User: admin
  Admin Password: ${GRAFANA_ADMIN_PASSWORD}
  URL: https://monitoring.${DOMAIN}

Docker Registry:
  URL: ghcr.io/${GITHUB_USER}/fastapi-http-websocket

========================================
IMPORTANT: Store this file securely!
========================================
EOF

chmod 400 ${CREDENTIALS_FILE}
echo -e "${GREEN}✅ Credentials saved to ${CREDENTIALS_FILE}${NC}"

# Display credentials
echo -e "\n${YELLOW}"
echo "========================================="
echo "   Generated Credentials"
echo "========================================="
cat ${CREDENTIALS_FILE}
echo -e "${NC}"

# Instructions
echo -e "\n${BLUE}"
echo "========================================="
echo "   Next Steps"
echo "========================================="
echo -e "${NC}"

echo -e "
${GREEN}1. Configure DNS:${NC}
   Create A records pointing to this server:
   - api.${DOMAIN}
   - auth.${DOMAIN}
   - monitoring.${DOMAIN}

${GREEN}2. Obtain SSL Certificates:${NC}
   Option A - Let's Encrypt (Free):
   ${YELLOW}sudo certbot certonly --standalone -d api.${DOMAIN}${NC}
   ${YELLOW}sudo certbot certonly --standalone -d auth.${DOMAIN}${NC}
   ${YELLOW}sudo certbot certonly --standalone -d monitoring.${DOMAIN}${NC}

   Option B - Custom certificates:
   Place in /opt/fastapi-app/ssl/

${GREEN}3. Pull Docker Image:${NC}
   ${YELLOW}docker login ghcr.io${NC}
   ${YELLOW}docker pull ghcr.io/${GITHUB_USER}/fastapi-http-websocket:latest${NC}

${GREEN}4. Copy Configuration Files:${NC}
   Copy from your repository:
   - docker-compose.production.yml
   - nginx.conf
   - prometheus.yml
   - alerts.yml
   - loki-config.yml
   - alloy-config.alloy

${GREEN}5. Start Services:${NC}
   ${YELLOW}cd /opt/fastapi-app${NC}
   ${YELLOW}docker-compose -f docker-compose.production.yml up -d${NC}

${GREEN}6. Configure Keycloak:${NC}
   - Access: https://auth.${DOMAIN}
   - Login with admin credentials above
   - Create 'production-realm'
   - Create 'fastapi-production' client
   - Create roles and users

${GREEN}7. Configure Monitoring:${NC}
   - Access: https://monitoring.${DOMAIN}
   - Login with Grafana admin credentials
   - Import dashboards from repository

${GREEN}8. Verify Deployment:${NC}
   ${YELLOW}curl https://api.${DOMAIN}/health${NC}
   ${YELLOW}curl https://api.${DOMAIN}/metrics${NC}

${YELLOW}⚠️  IMPORTANT:${NC}
   - Credentials saved in: ${CREDENTIALS_FILE}
   - Store credentials in password manager
   - Delete CREDENTIALS.txt after saving securely
   - Review and update .env.production as needed
"

echo -e "${BLUE}
========================================
   Setup Complete!
========================================
${NC}

For detailed documentation, see:
  - /opt/fastapi-app/docs/PRODUCTION_DEPLOYMENT.md
  - /opt/fastapi-app/docs/DOCKER_REGISTRY.md
"
