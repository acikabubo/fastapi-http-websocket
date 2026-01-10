# BasicAuth Protection for Observability Services

This document describes the HTTP Basic Authentication setup for protecting Prometheus, Loki, and Grafana Alloy services.

## Overview

BasicAuth middleware is configured in Traefik to protect observability services that don't have native authentication:
- **Prometheus** (http://prometheus.localhost)
- **Loki** (http://loki.localhost)
- **Grafana Alloy** (http://alloy.localhost)

## Credentials

**Default credentials (DEVELOPMENT ONLY):**
- **Username**: `admin`
- **Password**: `admin`

⚠️ **IMPORTANT**: These are development credentials. **CHANGE THEM IN PRODUCTION!**

## How It Works

1. User accesses a protected service (e.g., http://prometheus.localhost)
2. Traefik `observability-auth` middleware intercepts the request
3. Browser shows HTTP Basic Authentication popup
4. User enters credentials
5. Traefik validates credentials against `.htpasswd` file
6. If valid, request is forwarded to the service

## Configuration Files

### 1. Password File
**Location**: `docker/traefik/dynamic/.htpasswd`

Contains MD5-hashed passwords in Apache htpasswd format:
```
admin:$apr1$C47cBCz9$HDhEFmZKTYEn.aQHoYLNo1
```

### 2. Traefik Middleware
**Location**: `docker/traefik/dynamic/middleware.yml`

Defines the `observability-auth` BasicAuth middleware:
```yaml
observability-auth:
  basicAuth:
    usersFile: "/etc/traefik/dynamic/.htpasswd"
```

### 3. Service Configuration
**Location**: `docker/docker-compose.yml`

Services apply the middleware via Traefik labels:
```yaml
- "traefik.http.routers.prometheus.middlewares=observability-auth@file,secure-headers@file"
- "traefik.http.routers.loki.middlewares=observability-auth@file,secure-headers@file"
- "traefik.http.routers.alloy.middlewares=observability-auth@file,secure-headers@file"
```

## Protected Services

| Service | URL | BasicAuth | Notes |
|---------|-----|-----------|-------|
| Prometheus | http://prometheus.localhost | ✅ Required | Metrics & monitoring |
| Loki | http://loki.localhost | ✅ Required | Log aggregation (API only, no UI) |
| Grafana Alloy | http://alloy.localhost | ✅ Required | Observability collector |
| **Grafana** | http://grafana.localhost | ❌ Not protected | Has its own authentication |
| **FastAPI** | http://api.localhost | ❌ Not protected | Has Keycloak authentication |

## Testing

### Command Line Tests

**Test without credentials (should return 401 Unauthorized):**
```bash
curl -I http://prometheus.localhost/
curl -I http://loki.localhost/
curl -I http://alloy.localhost/
```

**Test with credentials (should return 200/302 OK):**
```bash
curl -I -u admin:admin http://prometheus.localhost/
curl -I -u admin:admin http://loki.localhost/
curl -I -u admin:admin http://alloy.localhost/
```

### Browser Test

1. Navigate to http://prometheus.localhost
2. Browser shows authentication popup
3. Enter username: `admin`, password: `admin`
4. Prometheus UI loads successfully

## Changing Passwords

### Method 1: Generate New Password Hash (Recommended)

```bash
# Generate new password hash
docker run --rm httpd:2.4-alpine htpasswd -nbm admin newpassword > docker/traefik/dynamic/.htpasswd

# Restart Traefik to reload configuration
docker-compose -f docker/docker-compose.yml restart traefik
```

### Method 2: Add Multiple Users

```bash
# Add first user
docker run --rm httpd:2.4-alpine htpasswd -nbm admin adminpass > docker/traefik/dynamic/.htpasswd

# Add more users (append with >>)
docker run --rm httpd:2.4-alpine htpasswd -nbm developer devpass >> docker/traefik/dynamic/.htpasswd
docker run --rm httpd:2.4-alpine htpasswd -nbm readonly readonlypass >> docker/traefik/dynamic/.htpasswd

# Restart Traefik
docker-compose -f docker/docker-compose.yml restart traefik
```

### Method 3: Use BCrypt (More Secure)

```bash
# Generate BCrypt hash (more secure than MD5)
docker run --rm httpd:2.4-alpine htpasswd -nbB admin strongpassword > docker/traefik/dynamic/.htpasswd

# Restart Traefik
docker-compose -f docker/docker-compose.yml restart traefik
```

## Production Recommendations

### Security Best Practices

1. **Change Default Credentials Immediately**
   ```bash
   docker run --rm httpd:2.4-alpine htpasswd -nbB admin $(openssl rand -base64 16) > docker/traefik/dynamic/.htpasswd
   ```

2. **Use Strong Passwords**
   - Minimum 16 characters
   - Mix of uppercase, lowercase, numbers, symbols
   - Use a password manager

3. **Use BCrypt Instead of MD5**
   - BCrypt is more secure than MD5
   - Use `-B` flag instead of `-m` when generating passwords

4. **Restrict Access by IP (Optional)**
   Add IP whitelist middleware for additional security:
   ```yaml
   observability-ip-whitelist:
     ipWhiteList:
       sourceRange:
         - "10.0.0.0/8"      # Internal network
         - "192.168.0.0/16"  # Local network
   ```

5. **Enable HTTPS**
   - BasicAuth sends credentials in Base64 encoding (not encrypted)
   - Always use HTTPS in production
   - Configure TLS in Traefik for proper encryption

6. **Rotate Passwords Regularly**
   - Change passwords every 90 days
   - Remove old/unused accounts

7. **Consider Upgrading to OAuth2**
   - For better security, consider OAuth2 Proxy with Keycloak (see issue #124)
   - BasicAuth is a simple solution but not ideal for production SSO

### Environment Variables for Secrets

Instead of hardcoding passwords, consider using Docker secrets or environment variables:

```yaml
# docker-compose.yml
services:
  traefik:
    secrets:
      - htpasswd

secrets:
  htpasswd:
    file: ./secrets/.htpasswd
```

## Troubleshooting

### Issue: Still Getting 401 with Correct Credentials

**Solution 1**: Verify password hash format
```bash
# Check .htpasswd file
cat docker/traefik/dynamic/.htpasswd

# Regenerate if corrupted
docker run --rm httpd:2.4-alpine htpasswd -nbm admin admin > docker/traefik/dynamic/.htpasswd
docker-compose -f docker/docker-compose.yml restart traefik
```

**Solution 2**: Check file is mounted correctly
```bash
# Verify file exists in container
docker exec hw-traefik ls -la /etc/traefik/dynamic/.htpasswd
docker exec hw-traefik cat /etc/traefik/dynamic/.htpasswd
```

### Issue: 404 Not Found

**Solution**: Ensure `.htpasswd` is in the correct location
```bash
# File must be in docker/traefik/dynamic/.htpasswd
# NOT in docker/traefik/.htpasswd
mv docker/traefik/.htpasswd docker/traefik/dynamic/.htpasswd
docker-compose -f docker/docker-compose.yml restart traefik
```

### Issue: No Authentication Popup in Browser

**Solution**: Clear browser cache and cookies
```bash
# Or test with curl
curl -v http://prometheus.localhost/
# Should show: Www-Authenticate: Basic realm="traefik"
```

### Issue: Grafana Also Requires BasicAuth

**Solution**: Verify Grafana router does NOT have `observability-auth` middleware
```bash
# Check docker-compose.yml
grep "grafana.middlewares" docker/docker-compose.yml
# Should NOT contain "observability-auth@file"
```

## Monitoring

### Check Who's Accessing Services

Traefik logs show BasicAuth attempts:
```bash
docker logs hw-traefik 2>&1 | grep -i "basicauth\|401"
```

### Failed Login Attempts

Monitor for suspicious activity:
```bash
# Watch for repeated 401s (possible brute force)
docker logs -f hw-traefik 2>&1 | grep "401 Unauthorized"
```

## References

- [Traefik BasicAuth Middleware Documentation](https://doc.traefik.io/traefik/middlewares/http/basicauth/)
- [Apache htpasswd Documentation](https://httpd.apache.org/docs/current/programs/htpasswd.html)
- Issue #123: Add BasicAuth protection for observability services
- Issue #124: Future OAuth2 Proxy investigation

## Migration Path

This BasicAuth setup is a **simple, immediate solution**. For production environments requiring SSO and better security:

1. **Short-term** (current): BasicAuth with strong passwords
2. **Medium-term**: Add IP whitelisting + HTTPS
3. **Long-term**: Migrate to OAuth2 Proxy with Keycloak (issue #124)

BasicAuth provides adequate protection while keeping the solution simple and maintainable.
