# Troubleshooting Guide

This guide provides solutions to common issues encountered when deploying and operating the FastAPI HTTP/WebSocket application.

## Table of Contents

- [Deployment Issues](#deployment-issues)
- [Service Connectivity](#service-connectivity)
- [Authentication & Authorization](#authentication--authorization)
- [Performance Issues](#performance-issues)
- [Database Problems](#database-problems)
- [Redis Issues](#redis-issues)
- [Traefik Routing](#traefik-routing)
- [Docker Container Issues](#docker-container-issues)
- [WebSocket Connection Problems](#websocket-connection-problems)
- [Rate Limiting Issues](#rate-limiting-issues)
- [Log Analysis](#log-analysis)
- [Emergency Procedures](#emergency-procedures)

## Deployment Issues

### Container Fails to Start

**Symptoms:**
- Container exits immediately after starting
- `docker ps` shows container not running
- Exit code non-zero

**Diagnosis:**
```bash
# Check container logs
docker logs hw-server

# Check exit code
docker inspect hw-server --format='{{.State.ExitCode}}'

# Check recent events
docker events --since 10m
```

**Common Causes & Solutions:**

1. **Missing Environment Variables:**
   ```bash
   # Check if .env files exist
   ls -la .env.production docker/.srv_env docker/.pg_env docker/.kc_env

   # Verify required variables are set
   docker exec hw-server printenv | grep -E "DATABASE_URL|KEYCLOAK_BASE_URL|REDIS_IP"
   ```

   **Fix:** Ensure all required variables are set in environment files.

2. **Port Already in Use:**
   ```bash
   # Check what's using the port
   sudo netstat -tulpn | grep :8000
   ```

   **Fix:** Stop conflicting service or change port mapping.

3. **Volume Permission Issues:**
   ```bash
   # Check volume permissions
   docker exec hw-server ls -la /app

   # Fix ownership
   sudo chown -R 1000:1000 /path/to/volumes
   ```

### Database Migration Failures

**Symptoms:**
- Migration command fails
- "Target database is not up to date" error
- Duplicate column/table errors

**Diagnosis:**
```bash
# Check current migration version
docker exec hw-server alembic current

# View migration history
docker exec hw-server alembic history

# Check for pending migrations
docker exec hw-server alembic heads
```

**Solutions:**

1. **Database Out of Sync:**
   ```bash
   # Check which migrations are applied
   docker exec hw-db psql -U prod_user -d fastapi_prod \
     -c "SELECT * FROM alembic_version;"

   # Stamp database at current code version
   docker exec hw-server alembic stamp head

   # Or downgrade and re-apply
   docker exec hw-server alembic downgrade -1
   docker exec hw-server alembic upgrade head
   ```

2. **Migration Conflicts:**
   ```bash
   # Check for multiple heads
   docker exec hw-server alembic heads

   # Merge branches if needed
   docker exec hw-server alembic merge <revision1> <revision2>
   ```

3. **Failed Partial Migration:**
   ```bash
   # Manual rollback
   docker exec hw-db psql -U prod_user -d fastapi_prod \
     -c "BEGIN; -- manually undo changes; COMMIT;"

   # Update alembic_version table
   docker exec hw-db psql -U prod_user -d fastapi_prod \
     -c "UPDATE alembic_version SET version_num='<previous_revision>';"
   ```

### SSL Certificate Issues

**Symptoms:**
- "Certificate verify failed" errors
- HTTPS connections rejected
- Let's Encrypt challenge fails

**Diagnosis:**
```bash
# Check Traefik logs
docker logs hw-traefik | grep -i certificate

# Check certificate status
docker exec hw-traefik ls -la /letsencrypt/

# Test certificate
curl -vI https://api.example.com 2>&1 | grep -A 10 "SSL certificate"
```

**Solutions:**

1. **Let's Encrypt Rate Limiting:**
   - Wait for rate limit reset (weekly limit: 50 certs per domain)
   - Use staging environment for testing:
     ```yaml
     # traefik.yml
     certificatesResolvers:
       letsencrypt:
         acme:
           caServer: https://acme-staging-v02.api.letsencrypt.org/directory
     ```

2. **DNS Not Propagated:**
   ```bash
   # Check DNS resolution
   nslookup api.example.com
   dig api.example.com

   # Wait for DNS propagation (up to 48 hours)
   ```

3. **Port 80 Not Accessible:**
   ```bash
   # Check firewall
   sudo ufw status
   sudo iptables -L -n | grep 80

   # Test port 80 access
   curl -I http://api.example.com/.well-known/acme-challenge/test
   ```

## Service Connectivity

### Cannot Connect to Application

**Symptoms:**
- "Connection refused" errors
- "No route to host"
- Timeout errors

**Diagnosis:**
```bash
# Check if service is running
docker ps | grep hw-server

# Check if port is listening
docker exec hw-server netstat -tulpn | grep 8000

# Check health status
curl http://localhost:8000/health

# Check Traefik routing
curl http://localhost:8080/api/http/routers
```

**Solutions:**

1. **Service Not Running:**
   ```bash
   # Restart service
   docker-compose -f docker/docker-compose.yml restart hw-server

   # Check startup logs
   docker logs hw-server --tail 50
   ```

2. **Network Issues:**
   ```bash
   # Check network configuration
   docker network inspect hw-network

   # Test connectivity between containers
   docker exec hw-server ping hw-db
   docker exec hw-server nc -zv hw-redis 6379
   ```

3. **Firewall Blocking:**
   ```bash
   # Check firewall rules
   sudo ufw status

   # Allow necessary ports
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

### Inter-Service Communication Fails

**Symptoms:**
- Application cannot reach database
- Redis connection errors
- Keycloak unreachable

**Diagnosis:**
```bash
# Check all services are on same network
docker network inspect hw-network | jq '.[0].Containers'

# Test DNS resolution
docker exec hw-server nslookup hw-db
docker exec hw-server nslookup hw-redis

# Test port connectivity
docker exec hw-server nc -zv hw-db 5432
docker exec hw-server nc -zv hw-redis 6379
docker exec hw-server nc -zv hw-keycloak 8080
```

**Solutions:**

1. **Services Not on Same Network:**
   ```yaml
   # Ensure all services have same network in docker-compose.yml
   services:
     hw-server:
       networks:
         - hw-network
     hw-db:
       networks:
         - hw-network
   ```

2. **Wrong Service Names:**
   ```bash
   # Use container names, not localhost
   # ❌ Wrong: DATABASE_URL=postgresql://localhost:5432/db
   # ✅ Correct: DATABASE_URL=postgresql://hw-db:5432/db
   ```

3. **Restart All Services:**
   ```bash
   docker-compose -f docker/docker-compose.yml down
   docker-compose -f docker/docker-compose.yml up -d
   ```

## Authentication & Authorization

### Keycloak Authentication Fails

**Symptoms:**
- "Invalid token" errors
- "Unauthorized" (401) responses
- "Token signature verification failed"

**Diagnosis:**
```bash
# Check Keycloak is running
docker logs hw-keycloak | tail -50

# Test Keycloak health
curl http://localhost:8080/health

# Verify token endpoint
curl http://localhost:8080/realms/production/.well-known/openid-configuration

# Check application logs for auth errors
docker logs hw-server | grep -i "auth\|token\|keycloak"
```

**Solutions:**

1. **Token Expired:**
   ```bash
   # Check token expiration settings in Keycloak
   # Admin Console → Realm Settings → Tokens
   # Access Token Lifespan: 5 minutes (default)
   # Refresh Token Lifespan: 30 minutes (default)

   # Get new token
   curl -X POST http://localhost:8080/realms/production/protocol/openid-connect/token \
     -d "client_id=fastapi-app" \
     -d "client_secret=YOUR_SECRET" \
     -d "grant_type=password" \
     -d "username=user@example.com" \
     -d "password=password"
   ```

2. **Wrong Keycloak Configuration:**
   ```bash
   # Verify environment variables
   docker exec hw-server printenv | grep KEYCLOAK

   # Should match:
   # KEYCLOAK_BASE_URL=http://hw-keycloak:8080
   # KEYCLOAK_REALM=production
   # KEYCLOAK_CLIENT_ID=fastapi-app
   ```

3. **Client Secret Mismatch:**
   ```bash
   # Get client secret from Keycloak
   # Admin Console → Clients → fastapi-app → Credentials

   # Update in .env.production
   KEYCLOAK_CLIENT_SECRET=<secret-from-keycloak>

   # Restart application
   docker-compose restart hw-server
   ```

### Permission Denied Errors

**Symptoms:**
- "Permission denied" (403) responses
- "Insufficient permissions" errors
- User cannot access expected endpoints

**Diagnosis:**
```bash
# Check user roles in Keycloak
# Admin Console → Users → <user> → Role Mappings

# Check actions.json for required roles
cat actions.json | jq '.roles'

# Check application logs
docker logs hw-server | grep -i "permission\|rbac"
```

**Solutions:**

1. **User Missing Required Role:**
   ```bash
   # Add role to user in Keycloak
   # Admin Console → Users → <user> → Role Mappings → Assign role

   # Or via kcadm.sh
   docker exec hw-keycloak /opt/keycloak/bin/kcadm.sh \
     add-roles -r production --uusername user@example.com --rolename admin
   ```

2. **Wrong Role in actions.json:**
   ```json
   // Check actions.json
   {
     "roles": ["admin", "user", "guest"],
     "http": {
       "/api/authors": {
         "POST": "admin"  // Requires admin role
       }
     }
   }

   // Update if needed and restart
   docker-compose restart hw-server
   ```

3. **Token Not Decoded Properly:**
   ```bash
   # Check token contents
   echo "eyJhbGc..." | cut -d'.' -f2 | base64 -d | jq

   # Verify 'realm_access.roles' field exists
   ```

## Performance Issues

### Slow Response Times

**Symptoms:**
- API requests take > 1 second
- WebSocket messages delayed
- Timeout errors

**Diagnosis:**
```bash
# Check application metrics
curl http://localhost:8000/metrics | grep http_request_duration

# Check database query performance
docker exec hw-db psql -U prod_user -d fastapi_prod \
  -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check CPU/memory usage
docker stats hw-server hw-db hw-redis

# Check network latency
docker exec hw-server ping hw-db
docker exec hw-server time nc -zv hw-db 5432
```

**Solutions:**

1. **Database Query Optimization:**
   ```sql
   -- Enable pg_stat_statements
   CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

   -- Find slow queries
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;

   -- Add indexes
   CREATE INDEX idx_author_name ON author(name);
   CREATE INDEX idx_book_author_id ON book(author_id);
   ```

2. **Increase Connection Pool:**
   ```bash
   # In .env.production
   DB_POOL_SIZE=30  # Increase from 20
   DB_MAX_OVERFLOW=20  # Increase from 10

   # Restart application
   docker-compose restart hw-server
   ```

3. **Scale Horizontally:**
   ```yaml
   # docker-compose.yml
   services:
     hw-server:
       deploy:
         replicas: 3  # Run 3 instances
   ```

4. **Enable Caching:**
   ```python
   # Add Redis caching for expensive queries
   from app.storage.redis import RRedis

   async def get_popular_authors():
       cache_key = "popular_authors"
       cached = await redis.get(cache_key)
       if cached:
           return json.loads(cached)

       authors = await fetch_from_db()
       await redis.setex(cache_key, 300, json.dumps(authors))
       return authors
   ```

### High Memory Usage

**Symptoms:**
- OOM (Out of Memory) errors
- Container restarts
- Memory usage > 90%

**Diagnosis:**
```bash
# Check memory usage
docker stats hw-server --no-stream

# Check container memory limit
docker inspect hw-server | jq '.[0].HostConfig.Memory'

# Check Python memory usage
docker exec hw-server python -c "import psutil; print(psutil.virtual_memory())"
```

**Solutions:**

1. **Increase Memory Limit:**
   ```yaml
   # docker-compose.yml
   services:
     hw-server:
       deploy:
         resources:
           limits:
             memory: 4G  # Increase from 2G
   ```

2. **Check for Memory Leaks:**
   ```python
   # Use memory profiler
   from memory_profiler import profile

   @profile
   def problematic_function():
       ...

   # Run and check output
   docker exec hw-server python -m memory_profiler app.py
   ```

3. **Reduce Workers:**
   ```bash
   # CMD in Dockerfile or docker-compose command
   CMD ["uvicorn", "app:application", "--workers", "2"]  # Reduce from 4
   ```

## Database Problems

### Cannot Connect to Database

**Symptoms:**
- "could not connect to server" errors
- "FATAL: password authentication failed"
- "database does not exist"

**Diagnosis:**
```bash
# Check PostgreSQL is running
docker ps | grep hw-db

# Check PostgreSQL logs
docker logs hw-db | tail -50

# Test connection from application container
docker exec hw-server psql -h hw-db -U prod_user -d fastapi_prod -c "SELECT 1;"

# Check connection string
docker exec hw-server printenv DATABASE_URL
```

**Solutions:**

1. **Database Not Ready:**
   ```bash
   # Wait for database to be healthy
   docker-compose -f docker/docker-compose.yml up -d hw-db

   # Check health status
   docker inspect hw-db --format='{{.State.Health.Status}}'

   # Wait and retry
   sleep 10
   docker-compose restart hw-server
   ```

2. **Wrong Credentials:**
   ```bash
   # Verify credentials match
   # .env.production: DATABASE_URL=postgresql://prod_user:PASSWORD@hw-db:5432/fastapi_prod
   # docker/.pg_env: POSTGRES_USER=prod_user, POSTGRES_PASSWORD=PASSWORD

   # Reset password if needed
   docker exec hw-db psql -U postgres \
     -c "ALTER USER prod_user WITH PASSWORD 'new_password';"
   ```

3. **Database Does Not Exist:**
   ```bash
   # Create database
   docker exec hw-db psql -U postgres -c "CREATE DATABASE fastapi_prod;"

   # Or recreate database container
   docker-compose down hw-db
   docker volume rm postgres-hw-data
   docker-compose up -d hw-db
   ```

### Database Locks/Deadlocks

**Symptoms:**
- "deadlock detected" errors
- Queries hanging indefinitely
- "could not obtain lock" errors

**Diagnosis:**
```sql
-- Check active locks
SELECT locktype, relation::regclass, mode, granted, pid
FROM pg_locks
WHERE NOT granted;

-- Check blocking queries
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

**Solutions:**

1. **Kill Blocking Query:**
   ```sql
   -- Terminate blocking process
   SELECT pg_terminate_backend(<blocking_pid>);
   ```

2. **Prevent Long Transactions:**
   ```python
   # Use short-lived transactions
   async with async_session() as session:
       async with session.begin():
           # Keep transaction scope small
           await session.execute(stmt)
           # Don't do expensive operations here
   ```

3. **Set Statement Timeout:**
   ```sql
   -- Set timeout for long-running queries
   ALTER DATABASE fastapi_prod SET statement_timeout = '30s';
   ```

## Redis Issues

### Cannot Connect to Redis

**Symptoms:**
- "Connection refused" errors
- "NOAUTH Authentication required"
- Rate limiting not working

**Diagnosis:**
```bash
# Check Redis is running
docker ps | grep hw-redis

# Test connection
docker exec hw-redis redis-cli ping

# Test from application container
docker exec hw-server redis-cli -h hw-redis ping

# Check Redis logs
docker logs hw-redis | tail -50
```

**Solutions:**

1. **Redis Not Running:**
   ```bash
   # Restart Redis
   docker-compose restart hw-redis

   # Check health
   docker exec hw-redis redis-cli ping
   ```

2. **Authentication Required:**
   ```bash
   # Check if Redis requires password
   docker exec hw-redis redis-cli CONFIG GET requirepass

   # If yes, ensure REDIS_PASSWORD is set in .env.production
   REDIS_PASSWORD=your_redis_password

   # Test with password
   docker exec hw-redis redis-cli -a your_redis_password ping
   ```

3. **Wrong Redis DB:**
   ```bash
   # Check which DB application is using
   docker exec hw-server printenv | grep REDIS

   # Should be:
   # MAIN_REDIS_DB=0
   # AUTH_REDIS_DB=1
   ```

### Redis Memory Issues

**Symptoms:**
- "OOM command not allowed" errors
- Redis crashes
- High memory usage

**Diagnosis:**
```bash
# Check Redis memory usage
docker exec hw-redis redis-cli INFO memory

# Check max memory setting
docker exec hw-redis redis-cli CONFIG GET maxmemory
```

**Solutions:**

1. **Increase Max Memory:**
   ```bash
   # docker/redis/redis.conf
   maxmemory 2gb

   # Or set at runtime
   docker exec hw-redis redis-cli CONFIG SET maxmemory 2gb

   # Restart Redis
   docker-compose restart hw-redis
   ```

2. **Configure Eviction Policy:**
   ```bash
   # docker/redis/redis.conf
   maxmemory-policy allkeys-lru  # Evict least recently used keys

   # Or set at runtime
   docker exec hw-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
   ```

3. **Clear Unused Keys:**
   ```bash
   # Find keys by pattern
   docker exec hw-redis redis-cli KEYS "rate_limit:*"

   # Clear old keys (be careful!)
   docker exec hw-redis redis-cli FLUSHDB
   ```

## Traefik Routing

### 404 Not Found Errors

**Symptoms:**
- Traefik returns 404 for valid endpoints
- "Service not found" errors

**Diagnosis:**
```bash
# Check Traefik dashboard
curl http://localhost:8080/api/http/routers | jq

# Check container labels
docker inspect hw-server | jq '.[0].Config.Labels'

# Check Traefik logs
docker logs hw-traefik | grep -i error
```

**Solutions:**

1. **Missing Labels:**
   ```yaml
   # docker-compose.yml
   services:
     hw-server:
       labels:
         - "traefik.enable=true"
         - "traefik.http.routers.fastapi.rule=Host(`api.example.com`)"
         - "traefik.http.routers.fastapi.entrypoints=websecure"
         - "traefik.http.services.fastapi.loadbalancer.server.port=8000"
   ```

2. **Restart Traefik:**
   ```bash
   docker-compose restart hw-traefik

   # Verify routing rules
   curl http://localhost:8080/api/http/routers
   ```

3. **Check Service Discovery:**
   ```bash
   # Ensure service is on same network as Traefik
   docker network inspect hw-network | jq '.[0].Containers'
   ```

### SSL/TLS Redirect Loop

**Symptoms:**
- Browser shows "too many redirects"
- Infinite redirect between HTTP and HTTPS

**Solutions:**

```yaml
# docker-compose.yml - Ensure Traefik knows it's behind a proxy
services:
  hw-server:
    labels:
      - "traefik.http.middlewares.secure-headers.headers.sslproxyheaders.X-Forwarded-Proto=https"
      - "traefik.http.routers.fastapi.middlewares=secure-headers"
```

## Docker Container Issues

### Container Keeps Restarting

**Symptoms:**
- Container in restart loop
- `docker ps` shows "Restarting" status

**Diagnosis:**
```bash
# Check restart count
docker inspect hw-server | jq '.[0].RestartCount'

# Check last exit code
docker inspect hw-server | jq '.[0].State.ExitCode'

# View all logs (before restart)
docker logs hw-server --timestamps
```

**Solutions:**

1. **Application Crash:**
   ```bash
   # Check for Python exceptions
   docker logs hw-server | grep -i "exception\|error\|traceback"

   # Run container interactively to debug
   docker run -it --rm --entrypoint /bin/bash hw-server
   ```

2. **Health Check Failing:**
   ```bash
   # Test health check manually
   docker exec hw-server curl -f http://localhost:8000/health

   # Adjust health check parameters
   # In Dockerfile:
   HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
     CMD curl -f http://localhost:8000/health || exit 1
   ```

3. **Resource Limits:**
   ```bash
   # Check if hitting resource limits
   docker stats hw-server --no-stream

   # Increase limits in docker-compose.yml
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 4G
   ```

### Volume Permission Issues

**Symptoms:**
- "Permission denied" errors when writing files
- Cannot create directories

**Solutions:**

```bash
# Fix volume ownership
docker exec --user root hw-server chown -R appuser:appuser /app

# Or set ownership on host
sudo chown -R 1000:1000 /path/to/volume

# Ensure user ID matches
docker exec hw-server id
# uid=1000(appuser) gid=1000(appuser)
```

## WebSocket Connection Problems

### WebSocket Connection Rejected

**Symptoms:**
- "Connection closed: 1006"
- "Connection closed: 1008 (policy violation)"
- Cannot establish WebSocket connection

**Diagnosis:**
```bash
# Check application logs
docker logs hw-server | grep -i websocket

# Test WebSocket connection
wscat -c ws://localhost:8000/web?access_token=TOKEN

# Check Traefik WebSocket configuration
curl http://localhost:8080/api/http/routers | jq '.[] | select(.name=="fastapi")'
```

**Solutions:**

1. **Missing Access Token:**
   ```bash
   # WebSocket requires token in query string
   wscat -c "ws://localhost:8000/web?access_token=YOUR_JWT_TOKEN"
   ```

2. **Connection Limit Reached:**
   ```bash
   # Check active connections in Redis
   docker exec hw-redis redis-cli SCARD "ws_connections:user123"

   # Increase limit in .env.production
   WS_MAX_CONNECTIONS_PER_USER=10  # Increase from 5

   # Restart application
   docker-compose restart hw-server
   ```

3. **Traefik Not Forwarding WebSocket:**
   ```yaml
   # docker-compose.yml
   services:
     hw-server:
       labels:
         # Ensure WebSocket headers are preserved
         - "traefik.http.routers.fastapi.rule=Host(`api.example.com`)"
         # Traefik v3 handles WebSocket automatically, but verify:
         - "traefik.http.services.fastapi.loadbalancer.passhostheader=true"
   ```

### WebSocket Messages Not Received

**Symptoms:**
- Messages sent but no response
- Connection stays open but silent

**Diagnosis:**
```bash
# Check application logs for message processing
docker logs hw-server | grep "pkg_id\|req_id"

# Check rate limiting
docker logs hw-server | grep "rate limit"

# Test with wscat
wscat -c "ws://localhost:8000/web?access_token=TOKEN"
> {"pkg_id": 1, "req_id": "test-123", "data": {}}
```

**Solutions:**

1. **Invalid Message Format:**
   ```json
   // Correct format
   {
     "pkg_id": 1,
     "req_id": "550e8400-e29b-41d4-a716-446655440000",
     "data": {}
   }
   ```

2. **Handler Not Registered:**
   ```bash
   # Check registered handlers
   make ws-handlers

   # Or check logs at startup
   docker logs hw-server | grep "Registered handler"
   ```

3. **Rate Limit Hit:**
   ```bash
   # Check rate limit settings
   docker exec hw-server printenv WS_MESSAGE_RATE_LIMIT

   # Increase if needed
   WS_MESSAGE_RATE_LIMIT=200  # In .env.production
   ```

## Rate Limiting Issues

### False Positive Rate Limits

**Symptoms:**
- Users getting 429 errors incorrectly
- Rate limit triggers too quickly

**Diagnosis:**
```bash
# Check rate limit settings
docker exec hw-server printenv | grep RATE_LIMIT

# Check Redis rate limit keys
docker exec hw-redis redis-cli KEYS "rate_limit:*"

# Check specific user's rate limit
docker exec hw-redis redis-cli GET "rate_limit:user:user123"
```

**Solutions:**

1. **Increase Rate Limits:**
   ```bash
   # .env.production
   RATE_LIMIT_PER_MINUTE=120  # Increase from 60
   RATE_LIMIT_BURST=20  # Increase from 10
   WS_MESSAGE_RATE_LIMIT=200  # Increase from 100

   # Restart application
   docker-compose restart hw-server
   ```

2. **Clear Rate Limit Keys:**
   ```bash
   # Clear specific user
   docker exec hw-redis redis-cli DEL "rate_limit:user:user123"

   # Clear all rate limit keys (careful!)
   docker exec hw-redis redis-cli KEYS "rate_limit:*" | \
     xargs docker exec hw-redis redis-cli DEL
   ```

3. **Exclude Specific Endpoints:**
   ```python
   # app/middlewares/rate_limit.py
   EXCLUDED_PATHS = [
       r"^/health$",
       r"^/metrics$",
       r"^/docs$",
       r"^/internal/.*",  # Add internal endpoints
   ]
   ```

## Log Analysis

### Finding Errors in Logs

**Common LogQL Queries:**

```bash
# Recent errors
{service="shell"} | json | level="ERROR"

# Authentication failures
{service="shell"} | json | logger=~"app.auth.*" |~ "(?i)(failed|invalid|denied)"

# Database errors
{service="shell"} | json |~ "(?i)(database|postgres|sqlalchemy)" | level="ERROR"

# Slow queries (requires duration_ms field)
{service="shell"} | json | duration_ms > 1000

# WebSocket errors
{service="shell"} | json | logger=~"app.api.ws.*" | level="ERROR"

# Rate limit violations
{service="shell"} | json |~ "(?i)(rate limit|429|too many requests)"

# Specific user activity
{service="shell"} | json | user_id="user123"

# Specific endpoint
{service="shell"} | json | endpoint=~"/api/authors.*"
```

### Analyzing Performance Issues

```bash
# HTTP request duration
{service="shell"} | json | logfmt | line_format "{{.method}} {{.endpoint}} {{.duration_ms}}ms"

# Database query performance
{service="shell"} | json |~ "(?i)query" | line_format "{{.message}} {{.duration_ms}}ms"

# Top error messages
{service="shell"} | json | level="ERROR" | line_format "{{.message}}" | count by message
```

## Emergency Procedures

### Application Down

**Immediate Actions:**

1. **Check service health:**
   ```bash
   docker ps | grep hw-
   curl http://localhost:8000/health
   ```

2. **Restart failed services:**
   ```bash
   docker-compose -f docker/docker-compose.yml restart hw-server
   ```

3. **Check recent logs:**
   ```bash
   docker logs hw-server --tail 100
   docker logs hw-traefik --tail 100
   ```

4. **If restart fails, rollback:**
   ```bash
   git log --oneline -5
   git checkout <previous-working-commit>
   docker-compose down
   docker-compose up -d
   ```

### Database Corruption

**Immediate Actions:**

1. **Stop application:**
   ```bash
   docker-compose stop hw-server
   ```

2. **Check database integrity:**
   ```bash
   docker exec hw-db pg_dump -U prod_user fastapi_prod > emergency_backup.sql
   ```

3. **Restore from backup:**
   ```bash
   docker exec hw-db psql -U postgres -c "DROP DATABASE fastapi_prod;"
   docker exec hw-db psql -U postgres -c "CREATE DATABASE fastapi_prod;"
   docker exec -i hw-db psql -U prod_user fastapi_prod < latest_backup.sql
   ```

4. **Restart application:**
   ```bash
   docker-compose start hw-server
   ```

### Security Incident

**Immediate Actions:**

1. **Isolate affected services:**
   ```bash
   # Disconnect from network
   docker network disconnect hw-network hw-server
   ```

2. **Review audit logs:**
   ```bash
   docker logs hw-server | grep -i "suspicious\|attack\|unauthorized"
   ```

3. **Block malicious IPs (if applicable):**
   ```bash
   sudo ufw deny from <malicious-ip>
   ```

4. **Rotate credentials:**
   ```bash
   # Generate new secrets
   openssl rand -hex 32

   # Update .env.production
   # Restart services
   docker-compose restart
   ```

### Complete System Failure

**Recovery Steps:**

1. **Document current state:**
   ```bash
   docker ps -a > system_state.txt
   docker logs hw-server > logs_server.txt
   docker logs hw-db > logs_db.txt
   ```

2. **Stop all services:**
   ```bash
   docker-compose -f docker/docker-compose.yml down
   ```

3. **Restore from backups:**
   ```bash
   # Restore database
   docker volume rm postgres-hw-data
   docker volume create postgres-hw-data
   docker-compose up -d hw-db
   docker exec -i hw-db psql -U prod_user fastapi_prod < backup.sql

   # Restore Redis data if needed
   docker volume rm redis-hw-data
   docker volume create redis-hw-data
   ```

4. **Start services gradually:**
   ```bash
   docker-compose up -d hw-db hw-redis
   sleep 10
   docker-compose up -d hw-keycloak
   sleep 10
   docker-compose up -d hw-server
   docker-compose up -d hw-traefik
   ```

5. **Verify system health:**
   ```bash
   curl http://localhost:8000/health
   docker ps
   docker-compose logs --tail 50
   ```

## Getting Help

If issues persist after trying these solutions:

1. **Check application logs in Grafana:**
   - http://localhost:3000/d/application-logs
   - Filter by service, level, endpoint

2. **Review metrics in Prometheus:**
   - http://localhost:9090
   - Check for anomalies

3. **Consult documentation:**
   - [Monitoring Guide](MONITORING.md)
   - [Backup/Recovery Guide](BACKUP_RECOVERY.md)
   - [Security Guide](../security/SECURITY_GUIDE.md)

4. **Contact support:**
   - GitHub Issues: https://github.com/acikabubo/fastapi-http-websocket/issues
   - Internal documentation: Confluence/Wiki
   - On-call rotation: PagerDuty

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Troubleshooting](https://www.postgresql.org/docs/current/maintenance.html)
- [Redis Troubleshooting](https://redis.io/docs/management/optimization/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
