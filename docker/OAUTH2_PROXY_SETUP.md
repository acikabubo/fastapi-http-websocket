# OAuth2 Proxy Setup for Keycloak Authentication

This setup protects services that don't natively support OAuth/OIDC (Prometheus, Loki, Alloy) using OAuth2 Proxy with Keycloak.

## Architecture

```
User Request → Traefik → OAuth2 Proxy (ForwardAuth) → Keycloak → Target Service
```

1. User accesses protected service (e.g., http://prometheus.localhost)
2. Traefik intercepts request and forwards to OAuth2 Proxy via `oauth2-auth` middleware
3. OAuth2 Proxy checks for valid session cookie
4. If no valid session, redirects to Keycloak login
5. After successful login, OAuth2 Proxy sets session cookie and allows access
6. Subsequent requests use the cookie for authentication

## Protected Services

The following services are now protected by Keycloak authentication:

- **Prometheus**: http://prometheus.localhost (metrics and monitoring)
- **Loki**: http://loki.localhost (log aggregation)
- **Grafana Alloy**: http://alloy.localhost (observability collector)

## Unprotected Services

These services remain publicly accessible:

- **FastAPI**: http://api.localhost (has its own authentication)
- **Keycloak**: http://auth.localhost (identity provider)
- **Grafana**: http://grafana.localhost (has its own OAuth integration)
- **Traefik Dashboard**: http://traefik.localhost (consider adding auth in production)

## Configuration Files

### 1. OAuth2 Proxy Configuration (`.oauth2_proxy_env`)

Key settings:
- **Provider**: `oidc` (OpenID Connect)
- **Issuer URL**: `http://hw-keycloak:8080/realms/HW-App`
- **Client ID**: `oauth2-proxy`
- **Client Secret**: `oauth2-proxy-secret-change-in-production`
- **Cookie Domain**: `.localhost` (shared across all .localhost subdomains)
- **Session Duration**: 24 hours with 1-hour refresh

### 2. Keycloak Client (`realm-export.json`)

OAuth2 Proxy client configured with:
- **Client ID**: `oauth2-proxy`
- **Redirect URIs**:
  - `http://oauth.localhost/oauth2/callback`
  - `http://prometheus.localhost/oauth2/callback`
  - `http://loki.localhost/oauth2/callback`
  - `http://alloy.localhost/oauth2/callback`
- **Protocol Mappers**: Groups and email mappers for user info

### 3. Traefik ForwardAuth Middleware (`traefik/dynamic/middleware.yml`)

```yaml
oauth2-auth:
  forwardAuth:
    address: "http://oauth2-proxy:4180/oauth2/auth"
    trustForwardHeader: true
    authResponseHeaders:
      - "X-Auth-Request-User"
      - "X-Auth-Request-Email"
      - "X-Auth-Request-Access-Token"
```

Applied to services via labels:
```yaml
- "traefik.http.routers.prometheus.middlewares=oauth2-auth@file,secure-headers@file"
```

## How to Test

1. **Start all services**:
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

2. **Access a protected service** (e.g., Prometheus):
   ```bash
   open http://prometheus.localhost
   ```

3. **Expected flow**:
   - Redirects to Keycloak login at http://auth.localhost
   - Enter credentials (admin/admin or test user)
   - Redirects back to Prometheus with authenticated session
   - Cookie `_oauth2_proxy` is set for `.localhost` domain

4. **Verify authentication**:
   - Check that you can access Prometheus, Loki, and Alloy without re-logging in
   - Cookie is shared across all .localhost subdomains

## Logout

To logout from all protected services:
```bash
open http://oauth.localhost/oauth2/sign_out
```

This will:
1. Clear the OAuth2 Proxy session cookie
2. Redirect to Keycloak logout endpoint
3. Clear Keycloak session

## Security Considerations

### Development Settings (Current)

- ✅ Cookie secure: `false` (allows HTTP for local development)
- ✅ Cookie domain: `.localhost` (shared across subdomains)
- ✅ Email domains: `*` (allows all email addresses)
- ⚠️ Client secret: Change in production!
- ⚠️ Cookie secret: Change in production!

### Production Recommendations

1. **Enable HTTPS**:
   ```env
   OAUTH2_PROXY_COOKIE_SECURE=true
   ```

2. **Restrict email domains**:
   ```env
   OAUTH2_PROXY_EMAIL_DOMAINS=yourcompany.com
   ```

3. **Use groups for authorization**:
   ```env
   OAUTH2_PROXY_ALLOWED_GROUPS=admin,monitoring
   ```

4. **Change secrets**:
   - Generate new client secret in Keycloak
   - Generate new cookie secret: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

5. **Consider rate limiting** on OAuth2 Proxy endpoint

6. **Enable session encryption**:
   ```env
   OAUTH2_PROXY_SESSION_STORE_TYPE=redis
   OAUTH2_PROXY_REDIS_CONNECTION_URL=redis://hw-redis:6379
   ```

## Troubleshooting

### Issue: Redirect loop or "Invalid parameter: redirect_uri"

**Solution**: Update Keycloak OAuth2 Proxy client via admin console:
1. Go to http://auth.localhost
2. Login to Administration Console
3. Select HW-App realm → Clients → oauth2-proxy
4. Update redirect URIs to match `.oauth2_proxy_env` configuration
5. Save changes

### Issue: "403 Forbidden" after login

**Solution**: Check allowed groups/emails:
- Verify user has required groups in Keycloak
- Check `OAUTH2_PROXY_ALLOWED_GROUPS` setting
- Check logs: `docker logs hw-oauth2-proxy`

### Issue: Cookie not working across services

**Solution**: Verify cookie domain:
- Must be `.localhost` (with leading dot)
- Check browser cookies for `_oauth2_proxy`
- Cookie should be valid for all `*.localhost` domains

### Issue: Session expires too quickly

**Solution**: Adjust session duration:
```env
OAUTH2_PROXY_COOKIE_EXPIRE=24h
OAUTH2_PROXY_COOKIE_REFRESH=1h
```

## Advanced: Custom Authorization

To restrict access based on user attributes:

### 1. By Email Domain
```env
OAUTH2_PROXY_EMAIL_DOMAINS=company.com,partner.com
```

### 2. By Keycloak Group
```env
OAUTH2_PROXY_ALLOWED_GROUPS=monitoring,admin
```

Groups are mapped via the `groups` protocol mapper in Keycloak client.

### 3. By Custom Header
OAuth2 Proxy forwards user info in headers:
- `X-Auth-Request-User`: Username
- `X-Auth-Request-Email`: Email address
- `X-Auth-Request-Access-Token`: JWT token

Services can read these headers for fine-grained authorization.

## Monitoring OAuth2 Proxy

### Logs
```bash
docker logs -f hw-oauth2-proxy
```

### Health Check
```bash
curl http://oauth.localhost/ping
```

### Metrics (Prometheus)
OAuth2 Proxy doesn't expose Prometheus metrics by default. To enable:
```env
OAUTH2_PROXY_METRICS_ADDRESS=0.0.0.0:9000
```

Then scrape at `http://oauth2-proxy:9000/metrics`.

## References

- [OAuth2 Proxy Documentation](https://oauth2-proxy.github.io/oauth2-proxy/)
- [Traefik ForwardAuth Middleware](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
- [Keycloak OIDC Configuration](https://www.keycloak.org/docs/latest/server_admin/#_oidc)
