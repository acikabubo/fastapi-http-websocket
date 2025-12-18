# Security Guide

Comprehensive security best practices and hardening guidelines for production deployment of the FastAPI HTTP/WebSocket application.

## Table of Contents

- [Security Principles](#security-principles)
- [Authentication & Authorization](#authentication--authorization)
- [Network Security](#network-security)
- [Data Security](#data-security)
- [Application Security](#application-security)
- [Infrastructure Security](#infrastructure-security)
- [Monitoring & Auditing](#monitoring--auditing)
- [Incident Response](#incident-response)
- [Compliance](#compliance)

## Security Principles

### Defense in Depth

Implement multiple layers of security:

1. **Network Layer**: Firewall, VPC, network segmentation
2. **Transport Layer**: TLS/SSL encryption
3. **Application Layer**: Authentication, authorization, input validation
4. **Data Layer**: Encryption at rest, secure backups
5. **Monitoring Layer**: Intrusion detection, audit logging

### Least Privilege

- Users/services should have minimum permissions needed
- Database users with specific grants only
- Container capabilities dropped to minimum
- File system mounted read-only where possible

### Security by Default

- Authentication required by default
- Rate limiting enabled
- Secure headers enforced
- Debug mode disabled in production

## Authentication & Authorization

### Key cloak Configuration

#### Production Realm Setup

```bash
# 1. Create production realm
Realm Name: production
Display Name: Production Environment
Enabled: ON

# 2. Security Settings
Realm Settings → Security Defenses:
- Brute Force Detection: ON
- Permanent Lockout: ON
- Max Login Failures: 5
- Wait Increment: 60 seconds
- Quick Login Check: 1000ms
- Minimum Quick Login Wait: 60 seconds

# 3. Token Settings
Realm Settings → Tokens:
- Access Token Lifespan: 5 minutes
- Access Token Lifespan For Implicit Flow: 15 minutes
- Client Login Timeout: 5 minutes
- Login Action Timeout: 5 minutes
- Refresh Token Max Reuse: 0
- SSO Session Idle: 30 minutes
- SSO Session Max: 10 hours
```

#### Client Configuration

```bash
# FastAPI Client
Client ID: fastapi-app
Client Protocol: openid-connect
Access Type: confidential
Standard Flow Enabled: ON
Direct Access Grants Enabled: OFF  # Disable for production
Service Accounts Enabled: OFF
Authorization Enabled: ON

# Valid Redirect URIs (strict)
https://api.example.com/*
# DO NOT use wildcards like https://* in production

# Web Origins
https://api.example.com

# Advanced Settings
Proof Key for Code Exchange Code Challenge Method: S256  # Enable PKCE
```

#### Role-Based Access Control (RBAC)

**`actions.json` Configuration**:

```json
{
  "roles": ["admin", "user", "viewer", "service"],
  "ws": {
    "1": "user",
    "2": "admin",
    "3": "user",
    "4": "admin",
    "5": "admin",
    "6": "viewer"
  },
  "http": {
    "/authors": {
      "GET": "viewer",
      "POST": "admin",
      "PUT": "admin",
      "DELETE": "admin"
    },
    "/books": {
      "GET": "viewer",
      "POST": "user",
      "PUT": "user",
      "DELETE": "admin"
    },
    "/users": {
      "GET": "admin",
      "POST": "admin",
      "PUT": "admin",
      "DELETE": "admin"
    },
    "/metrics": "admin",
    "/health": "*"  # Public endpoint
  }
}
```

**Best Practices**:

1. **Principle of Least Privilege**: Assign minimum role needed
2. **Regular Audits**: Review role assignments quarterly
3. **Service Accounts**: Create dedicated roles for service-to-service auth
4. **Temporary Elevation**: Use time-limited admin access

### Token Security

#### JWT Validation

```python
# app/auth.py - Already implemented
class AuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        # 1. Extract token from header/query
        # 2. Decode and verify signature
        # 3. Check expiration
        # 4. Verify audience
        # 5. Validate issuer
        # 6. Check not-before (nbf) claim
        # 7. Verify token wasn't revoked
```

#### Token Storage

**❌ DON'T**:
- Store tokens in localStorage (vulnerable to XSS)
- Log tokens
- Send tokens in URL parameters (except WebSocket initial connection)
- Store tokens in cookies without HttpOnly flag

**✅ DO**:
- Use HttpOnly, Secure cookies for web apps
- Store tokens in memory for SPAs
- Implement token refresh flow
- Use short-lived access tokens (5-15 min)
- Use long-lived refresh tokens with rotation

#### Token Revocation

```python
# Implement token blacklist in Redis
from app.storage.redis import RRedis

async def revoke_token(token_jti: str, exp: int):
    """Revoke a token by adding to blacklist."""
    redis = RRedis()
    ttl = exp - int(time.time())
    await redis.setex(f"revoked_token:{token_jti}", ttl, "1")

async def is_token_revoked(token_jti: str) -> bool:
    """Check if token is revoked."""
    redis = RRedis()
    return await redis.exists(f"revoked_token:{token_jti}")
```

## Network Security

### Firewall Rules

```bash
# Allow only necessary ports
ufw default deny incoming
ufw default allow outgoing

# HTTP/HTTPS (Traefik)
ufw allow 80/tcp
ufw allow 443/tcp

# SSH (restrict to specific IPs)
ufw allow from 1.2.3.4 to any port 22

# Enable firewall
ufw enable
```

### TLS/SSL Configuration

#### Traefik TLS Settings

```yaml
# docker/traefik/traefik.yml
entryPoints:
  websecure:
    address: ":443"
    http:
      tls:
        options: default
        certResolver: letsencrypt
        domains:
          - main: example.com
            sans:
              - "*.example.com"

# TLS Options
tls:
  options:
    default:
      minVersion: VersionTLS12
      maxVersion: VersionTLS13
      cipherSuites:
        - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
        - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
        - TLS_AES_256_GCM_SHA384
        - TLS_CHACHA20_POLY1305_SHA256
      sniStrict: true
```

#### Certificate Management

```bash
# Let's Encrypt auto-renewal
# Traefik handles this automatically

# Check certificate expiration
echo | openssl s_client -servername api.example.com -connect api.example.com:443 2>/dev/null | openssl x509 -noout -dates

# Monitor expiration in Prometheus
ssl_certificate_expiry{domain="api.example.com"} < 604800  # 7 days
```

### Network Segmentation

```yaml
# docker-compose.yml
networks:
  # Public network - accessible from internet
  public:
    driver: bridge

  # Private network - internal services only
  private:
    driver: bridge
    internal: true  # No external access

services:
  traefik:
    networks:
      - public  # Internet-facing

  hw-server:
    networks:
      - public   # Accessible via Traefik
      - private  # Can access backend services

  hw-db:
    networks:
      - private  # Not accessible from internet

  hw-redis:
    networks:
      - private  # Not accessible from internet
```

## Data Security

### Database Security

#### PostgreSQL Hardening

**`docker/.pg_env.production`**:
```bash
# Strong password (32+ characters)
POSTGRES_PASSWORD=CHANGE_ME_LONG_RANDOM_STRING

# SSL Mode
PGSSLMODE=require
PGSSLCERT=/path/to/client-cert.pem
PGSSLKEY=/path/to/client-key.pem
PGSSLROOTCERT=/path/to/ca-cert.pem
```

**Connection String**:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
```

**PostgreSQL Configuration** (`postgresql.conf`):
```conf
# Authentication
ssl = on
ssl_cert_file = '/var/lib/postgresql/server.crt'
ssl_key_file = '/var/lib/postgresql/server.key'
ssl_ca_file = '/var/lib/postgresql/root.crt'

# Network
listen_addresses = '127.0.0.1,172.25.0.0/16'  # Only internal network

# Logging
log_connections = on
log_disconnections = on
log_statement = 'ddl'  # Log DDL statements
log_line_prefix = '%t [%p]: user=%u,db=%d,app=%a,client=%h '

# Security
password_encryption = scram-sha-256
```

**Database User Permissions**:
```sql
-- Create application user with minimal permissions
CREATE USER app_user WITH PASSWORD 'STRONG_PASSWORD';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE production TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Revoke dangerous permissions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE postgres FROM PUBLIC;
```

#### SQL Injection Prevention

**✅ Always Use Parameterized Queries** (SQLAlchemy/SQLModel does this automatically):

```python
# ✅ SAFE: Parameterized query
stmt = select(Author).where(Author.name == user_input)
result = await session.execute(stmt)

# ❌ NEVER DO THIS: String concatenation
query = f"SELECT * FROM authors WHERE name = '{user_input}'"
```

**Input Validation with Pydantic**:
```python
from pydantic import BaseModel, validator

class AuthorCreate(BaseModel):
    name: str
    bio: str | None = None

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v) > 100:
            raise ValueError('Name must be 1-100 characters')
        if not v.replace(' ', '').isalnum():
            raise ValueError('Name must be alphanumeric')
        return v
```

### Redis Security

**`docker/redis/redis.conf`**:
```conf
# Bind to internal network only
bind 127.0.0.1 172.25.0.1

# Require password
requirepass STRONG_REDIS_PASSWORD

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_SECRET_NAME"
rename-command SHUTDOWN ""
rename-command DEBUG ""

# Enable SSL/TLS
port 0  # Disable unencrypted port
tls-port 6379
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt

# Memory limits
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence (if needed)
save 900 1
save 300 10
save 60 10000
```

**Application Configuration**:
```python
# app/storage/redis.py
redis_client = Redis(
    host=settings.REDIS_IP,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    ssl=True,  # Enable SSL in production
    ssl_cert_reqs='required',
    ssl_ca_certs='/path/to/ca.crt',
    socket_connect_timeout=5,
    socket_timeout=5,
    decode_responses=True,
)
```

### Encryption at Rest

#### Database Encryption

```bash
# PostgreSQL transparent data encryption (TDE)
# Requires PostgreSQL with encryption support

# File-level encryption with dm-crypt/LUKS
cryptsetup luksFormat /dev/sdb
cryptsetup open /dev/sdb postgres_encrypted
mkfs.ext4 /dev/mapper/postgres_encrypted
mount /dev/mapper/postgres_encrypted /var/lib/postgresql/data
```

#### Secrets Management

**AWS Secrets Manager**:
```python
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='us-east-1')

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise Exception(f"Error retrieving secret: {e}")

# Usage
db_password = get_secret('prod/db/password')
```

**HashiCorp Vault**:
```python
import hvac

client = hvac.Client(url='https://vault.example.com:8200')
client.auth.approle.login(
    role_id='app-role-id',
    secret_id='app-secret-id',
)

# Read secret
secret = client.secrets.kv.v2.read_secret_version(
    path='production/database',
)
db_password = secret['data']['data']['password']
```

## Application Security

### Input Validation

**Pydantic Models** (already implemented):
```python
from pydantic import BaseModel, Field, validator
from typing import Literal

class CreateAuthorInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=1000)
    status: Literal['active', 'inactive'] = 'active'

    @validator('name')
    def sanitize_name(cls, v):
        # Remove potentially dangerous characters
        import re
        v = re.sub(r'[<>\"\'&]', '', v)
        return v.strip()
```

### Output Encoding

**XSS Prevention**:
```python
from html import escape

# Escape user-generated content before rendering
safe_bio = escape(author.bio)
```

**Response Headers**:
```python
# app/middlewares/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # XSS Protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTPS Enforcement
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # CSP
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.example.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss://api.example.com; "
            "frame-ancestors 'none'"
        )

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=()"
        )

        return response
```

### Rate Limiting

Already implemented in `app/middlewares/rate_limit.py` and `app/utils/rate_limiter.py`.

**Production Configuration**:
```bash
# .env.production
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60  # 1 request per second
RATE_LIMIT_BURST=10
WS_MAX_CONNECTIONS_PER_USER=5
WS_MESSAGE_RATE_LIMIT=100
```

**DDoS Protection**:
- Use Cloudflare or AWS WAF
- Enable Traefik rate limiting as additional layer
- Monitor `rate_limit_hits_total` metric for abuse

### CORS Configuration

```python
# app/__init__.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.example.com",
        "https://admin.example.com"
    ],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)
```

### WebSocket Security

**Authentication**:
```python
# Already implemented in app/api/ws/websocket.py
class PackageAuthWebSocketEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket: WebSocket):
        # 1. Extract token from query params
        # 2. Validate token with Keycloak
        # 3. Check rate limits
        # 4. Accept or reject connection
```

**Message Validation**:
```python
# Already implemented in app/routing.py
class PackageRouter:
    async def handle_request(self, request: RequestModel, user: UserModel):
        # 1. Validate JSON schema
        # 2. Check RBAC permissions
        # 3. Rate limit messages
        # 4. Sanitize input
```

## Infrastructure Security

### Docker Security

See [DOCKER.md](../deployment/DOCKER.md) for detailed Docker security practices.

**Key Points**:
- Run as non-root user
- Read-only root filesystem
- Drop all capabilities
- Use security options (no-new-privileges)
- Scan images for vulnerabilities

### Secrets in Docker

**Never in Dockerfile or docker-compose.yml**:
```yaml
# ❌ NEVER DO THIS
environment:
  - DB_PASSWORD=plaintext_password

# ✅ Use env_file
env_file:
  - .env.production  # Not committed to git

# ✅ Or Docker secrets (Swarm)
secrets:
  - db_password
```

### Vulnerability Scanning

```bash
# Scan Docker images
docker scan fastapi-app:latest

# Scan Python dependencies
make skjold-scan

# SAST scanning
make bandit-scan

# Check for outdated packages
make outdated-pkgs-scan
```

## Monitoring & Auditing

### Audit Logging

Already implemented in `app/models/user_action.py`.

**What to Log**:
- Authentication attempts (success/failure)
- Authorization failures
- Database modifications (CREATE, UPDATE, DELETE)
- Admin actions
- Configuration changes
- API access patterns
- Rate limit violations

**Log Retention**:
```sql
-- Automated cleanup (run daily)
DELETE FROM user_action_logs
WHERE timestamp < NOW() - INTERVAL '90 days';
```

**Log Analysis**:
```logql
# Grafana Loki queries
{service="shell"} | json | action="login" | status="failed"
{service="shell"} | json | action="delete" | user_role="admin"
{service="shell"} | json |~ "(?i)(permission denied|unauthorized)"
```

### Security Monitoring

**Prometheus Alerts**:
```yaml
# prometheus/alerts/security.yml
groups:
  - name: security
    rules:
      - alert: HighFailedLoginRate
        expr: rate(auth_attempts_total{status="failed"}[5m]) > 10
        for: 5m
        annotations:
          summary: "High rate of failed login attempts"
          description: "{{ $value }} failed logins per second"

      - alert: RateLimitAbuse
        expr: rate(rate_limit_hits_total[5m]) > 100
        for: 5m
        annotations:
          summary: "Potential DDoS attack or abuse"

      - alert: UnauthorizedAccess
        expr: increase(http_requests_total{status_code="403"}[5m]) > 50
        annotations:
          summary: "High rate of unauthorized access attempts"
```

## Incident Response

### Security Incident Playbook

**1. Detection & Analysis (0-30 minutes)**:
- [ ] Alert received (failed logins, data breach, etc.)
- [ ] Verify incident is real (not false positive)
- [ ] Assess scope and severity
- [ ] Activate incident response team

**2. Containment (30-60 minutes)**:
- [ ] Isolate affected systems
- [ ] Block malicious IPs at firewall
- [ ] Revoke compromised credentials
- [ ] Disable compromised accounts
- [ ] Take snapshots/backups of affected systems

**3. Eradication (1-4 hours)**:
- [ ] Identify root cause
- [ ] Remove malware/backdoors
- [ ] Patch vulnerabilities
- [ ] Update firewall rules
- [ ] Force password resets if needed

**4. Recovery (4-24 hours)**:
- [ ] Restore from clean backups if needed
- [ ] Verify system integrity
- [ ] Gradual service restoration
- [ ] Enhanced monitoring

**5. Post-Incident (1-7 days)**:
- [ ] Document timeline
- [ ] Root cause analysis
- [ ] Update security procedures
- [ ] Notify affected users (if required)
- [ ] Improve detection/prevention

### Emergency Contacts

```yaml
# incident_contacts.yml
primary:
  - name: Security Lead
    phone: +1-xxx-xxx-xxxx
    email: security@example.com

escalation:
  - name: CTO
    phone: +1-xxx-xxx-xxxx
    email: cto@example.com

external:
  - name: Incident Response Firm
    phone: +1-xxx-xxx-xxxx
    email: ir@firm.com
```

### Evidence Preservation

```bash
# Preserve logs
docker logs hw-server > incident-logs-$(date +%Y%m%d-%H%M%S).log

# Preserve memory dump
docker exec hw-server gcore $(docker exec hw-server pidof python)

# Preserve disk image
docker commit hw-server incident-snapshot-$(date +%Y%m%d)

# Preserve network traffic
tcpdump -i any -w incident-traffic-$(date +%Y%m%d).pcap
```

## Compliance

### GDPR Compliance

**Data Minimization**:
- Only collect necessary data
- Delete data when no longer needed
- Implement data retention policies

**Right to Access**:
```python
@router.get("/users/{user_id}/data")
async def get_user_data(user_id: str):
    """Export all user data (GDPR compliance)."""
    # Return all data associated with user
```

**Right to be Forgotten**:
```python
@router.delete("/users/{user_id}/gdpr-delete")
async def gdpr_delete_user(user_id: str):
    """Permanently delete all user data."""
    # Delete from all tables
    # Anonymize audit logs
```

### SOC 2 Compliance

**Access Controls**:
- [ ] MFA for admin accounts
- [ ] Principle of least privilege
- [ ] Regular access reviews

**Change Management**:
- [ ] Code review required
- [ ] Deployment approval process
- [ ] Rollback procedures documented

**Monitoring**:
- [ ] Centralized logging
- [ ] Audit trail of all changes
- [ ] Security alerts configured

## Security Checklist

### Pre-Deployment

- [ ] All default passwords changed
- [ ] Secrets stored in vault (not in code)
- [ ] SSL/TLS certificates valid
- [ ] Firewall rules configured
- [ ] Database encryption enabled
- [ ] Redis authentication enabled
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Security headers configured
- [ ] Audit logging enabled
- [ ] Vulnerability scan passed
- [ ] Penetration testing completed

### Post-Deployment

- [ ] Monitor security alerts
- [ ] Review audit logs daily
- [ ] Apply security patches weekly
- [ ] Rotate credentials monthly
- [ ] Review access controls quarterly
- [ ] Penetration testing annually

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Keycloak Security Guide](https://www.keycloak.org/docs/latest/server_admin/#security)
