# Configuration Guide

This guide covers application configuration, settings, environment variables, and startup validation.

## Table of Contents

- [Constants Module](#constants-module)
- [Settings Structure](#settings-structure)
- [Environment Variables](#environment-variables)
- [Environment-Specific Configuration](#environment-specific-configuration)
- [Startup Validation](#startup-validation)
- [Related Documentation](#related-documentation)

## Constants Module

**Location**: `app/constants.py`

Application-wide constants are defined to eliminate magic numbers and improve code clarity. Constants are organized by category:

### Categories

- **Audit Logging**: `AUDIT_QUEUE_MAX_SIZE`, `AUDIT_BATCH_SIZE`, `AUDIT_BATCH_TIMEOUT_SECONDS`
- **Database**: `DB_MAX_RETRIES`, `DB_RETRY_DELAY_SECONDS`, `DEFAULT_PAGE_SIZE`, `MAX_PAGE_SIZE`
- **Redis**: `REDIS_DEFAULT_PORT`, `REDIS_SOCKET_TIMEOUT_SECONDS`, `REDIS_CONNECT_TIMEOUT_SECONDS`, `REDIS_HEALTH_CHECK_INTERVAL_SECONDS`, `REDIS_MAX_CONNECTIONS`, `REDIS_MESSAGE_TIMEOUT_SECONDS`
- **Background Tasks**: `TASK_SLEEP_INTERVAL_SECONDS`, `TASK_ERROR_BACKOFF_SECONDS`
- **Rate Limiting**: `DEFAULT_RATE_LIMIT_PER_MINUTE`, `DEFAULT_RATE_LIMIT_BURST`, `DEFAULT_WS_MAX_CONNECTIONS_PER_USER`, `DEFAULT_WS_MESSAGE_RATE_LIMIT`
- **WebSocket**: `WS_POLICY_VIOLATION_CODE`, `WS_CLOSE_TIMEOUT_SECONDS`
- **Keycloak/Auth**: `KC_SESSION_EXPIRY_BUFFER_SECONDS`

## Settings Structure

**Location**: `app/settings/`

Settings are organized into a modular package structure with nested configuration groups. The settings support **two access patterns**:

1. **Flat access** (original, backward compatible): `app_settings.DB_HOST`
2. **Nested access** (new, recommended): `app_settings.database.HOST`

### Structure

- `app/settings/__init__.py` - Main Settings class with flat env vars
- `app/settings/models.py` - Nested BaseModel classes for grouping

### Nested Configuration Groups

```python
from app.settings import app_settings

# Database settings
app_settings.database.USER          # or app_settings.DB_USER
app_settings.database.PASSWORD      # or app_settings.DB_PASSWORD
app_settings.database.HOST          # or app_settings.DB_HOST
app_settings.database.url           # Computed property (DATABASE_URL)

# Redis settings
app_settings.redis.IP               # or app_settings.REDIS_IP
app_settings.redis.PORT             # or app_settings.REDIS_PORT
app_settings.redis.MAIN_DB          # or app_settings.MAIN_REDIS_DB

# Keycloak settings
app_settings.keycloak.REALM         # or app_settings.KEYCLOAK_REALM
app_settings.keycloak.CLIENT_ID     # or app_settings.KEYCLOAK_CLIENT_ID

# Security settings (with nested rate_limit)
app_settings.security.ALLOWED_HOSTS
app_settings.security.rate_limit.ENABLED     # or app_settings.RATE_LIMIT_ENABLED
app_settings.security.rate_limit.PER_MINUTE  # or app_settings.RATE_LIMIT_PER_MINUTE

# WebSocket settings
app_settings.websocket.MAX_CONNECTIONS_PER_USER  # or app_settings.WS_MAX_CONNECTIONS_PER_USER
app_settings.websocket.ALLOWED_ORIGINS           # or app_settings.ALLOWED_WS_ORIGINS

# Logging settings (with nested audit)
app_settings.logging.LEVEL                     # or app_settings.LOG_LEVEL
app_settings.logging.CONSOLE_FORMAT            # or app_settings.LOG_CONSOLE_FORMAT
app_settings.logging.audit.ENABLED             # or app_settings.AUDIT_LOG_ENABLED
app_settings.logging.audit.QUEUE_MAX_SIZE      # or app_settings.AUDIT_QUEUE_MAX_SIZE

# Circuit breaker settings (with nested keycloak/redis)
app_settings.circuit_breaker.ENABLED
app_settings.circuit_breaker.keycloak.FAIL_MAX  # or app_settings.KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX
app_settings.circuit_breaker.redis.TIMEOUT      # or app_settings.REDIS_CIRCUIT_BREAKER_TIMEOUT

# Profiling settings
app_settings.profiling.ENABLED          # or app_settings.PROFILING_ENABLED
app_settings.profiling.OUTPUT_DIR       # or app_settings.PROFILING_OUTPUT_DIR
```

### Benefits of Nested Access

- Better IDE autocomplete (`app_settings.database.` shows all database settings)
- Logical grouping (related settings together)
- Type hints for nested models
- Backward compatible (flat access still works)

### Adding New Settings

1. Add env var to `Settings` class in `app/settings/__init__.py` (flat field)
2. Add field to appropriate nested model in `app/settings/models.py`
3. Add mapping in corresponding `@property` method
4. Both access patterns will work automatically

## Environment Variables

All settings are loaded from environment variables with their original flat names:
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `REDIS_IP`, `REDIS_PORT`, `MAIN_REDIS_DB`, `AUTH_REDIS_DB`
- `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_BASE_URL`
- `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MINUTE`
- `WS_MAX_CONNECTIONS_PER_USER`, `WS_MESSAGE_RATE_LIMIT`
- `LOG_LEVEL`, `LOG_CONSOLE_FORMAT`
- `AUDIT_LOG_ENABLED`, `AUDIT_QUEUE_MAX_SIZE`
- `PROFILING_ENABLED`, `PROFILING_OUTPUT_DIR`

**No breaking changes** - all existing env var names are preserved!

## Environment-Specific Configuration

The application supports multiple deployment environments with automatic configuration defaults. The `ENV` setting (from `app.settings.Environment` enum) determines environment-specific behavior.

### Supported Environments

- `dev` - Development environment (default)
- `staging` - Staging/testing environment
- `production` - Production environment

### Environment Configuration Files

- `.env.dev.example` - Development environment template
- `.env.staging.example` - Staging environment template
- `.env.production.example` - Production environment template

### Environment-Specific Defaults

| Setting | DEV | STAGING | PRODUCTION |
|---------|-----|---------|------------|
| `LOG_LEVEL` | DEBUG | INFO | WARNING |
| `LOG_CONSOLE_FORMAT` | human | json | json |
| `RATE_LIMIT_FAIL_MODE` | open | open | closed |
| `PROFILING_ENABLED` | true | true | false |

### Setting the Environment

```bash
# Development (default)
ENV=dev

# Staging
ENV=staging

# Production
ENV=production
```

### Environment-Specific Behavior

**1. Production Environment** (`ENV=production`):
   - Rate limiting fails closed (denies requests when Redis unavailable)
   - JSON logging for Grafana Alloy/Loki integration
   - WARNING log level (minimal logging)
   - Profiling disabled by default

**2. Staging Environment** (`ENV=staging`):
   - Production-like settings with some debugging enabled
   - INFO log level for moderate logging
   - JSON logging for log aggregation
   - Profiling enabled for performance testing

**3. Development Environment** (`ENV=dev`):
   - Permissive settings for local development
   - DEBUG log level for verbose logging
   - Human-readable console logging
   - Profiling enabled for local testing

### Helper Properties

```python
from app.settings import app_settings

if app_settings.is_production:
    # Production-only logic
    pass

if app_settings.is_staging:
    # Staging-only logic
    pass

if app_settings.is_development:
    # Development-only logic
    pass
```

### Configuration Priority

Environment-specific defaults are applied **only if** the setting is not explicitly provided via environment variables. This allows overriding defaults when needed:

```bash
# Override production default (WARNING) with INFO
ENV=production
LOG_LEVEL=INFO  # Explicitly set, overrides production default
```

### Example Usage

```bash
# Development
cp .env.dev.example .env
# Edit .env with your local Keycloak credentials
ENV=dev

# Staging deployment
cp .env.staging.example .env
# Update all CHANGE_ME values
ENV=staging

# Production deployment
cp .env.production.example .env
# CRITICAL: Review and update ALL settings
ENV=production
```

## Startup Validation

**Location**: `app/startup_validation.py`

The application implements **fail-fast validation** to ensure it does not start with invalid configuration or unavailable dependencies. All validations run during application startup, before accepting any requests.

### Validation Functions

**1. `validate_settings()`** - Validates required environment variables:
   - Keycloak settings: `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_BASE_URL`, `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`
   - Database settings: `DB_USER`, `DB_PASSWORD`

**2. `validate_database_connection()`** - Tests database connectivity:
   - Attempts connection to PostgreSQL
   - Executes simple health check query (`SELECT 1`)
   - Raises `StartupValidationError` if connection fails

**3. `validate_redis_connection()`** - Tests Redis connectivity:
   - Attempts connection to Redis
   - Executes PING command to verify connection
   - Raises `StartupValidationError` if connection fails

**4. `run_all_validations()`** - Orchestrates all validation checks:
   - Runs settings validation first (no external dependencies)
   - Then validates database connection
   - Finally validates Redis connection
   - Application will not start if any validation fails

### Integration with Lifespan

Startup validation runs automatically in the `lifespan()` context manager before any other initialization:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Run startup validations (fail-fast if configuration is invalid)
    from app.startup_validation import run_all_validations
    await run_all_validations()

    # Continue with normal startup (database, background tasks, etc.)
    ...
```

### Error Messages

When validation fails:

```
ERROR - Startup validation failed: KEYCLOAK_REALM environment variable is required
ERROR - Application will not start. Fix the configuration errors and try again.
```

### Benefits

- ✅ **Fail-fast principle**: Application won't start with invalid configuration
- ✅ **Clear error messages**: Actionable feedback for missing/invalid settings
- ✅ **Early detection**: Catch configuration errors before accepting requests
- ✅ **Service availability checks**: Verify database and Redis are reachable

### Testing

Comprehensive tests in `tests/test_startup_validation.py` cover:
- Missing environment variables
- Invalid configuration validation
- Database connection failures
- Redis connection failures
- Validation orchestration

## Related Documentation

- [Git Workflow Guide](git-workflow.md) - Git workflow, issue management, worktree syncing
- [Architecture Guide](architecture-guide.md) - Design patterns, components, request flow
- [Development Guide](development-guide.md) - Running the app, Docker, WebSocket handlers
- [Testing Guide](testing-guide.md) - Test infrastructure, fixtures, load/chaos tests
- [Code Quality Guide](code-quality-guide.md) - Linting, type checking, pre-commit hooks
- [Database Guide](database-guide.md) - Sessions, migrations, pagination, relationships
- [Monitoring Guide](monitoring-guide.md) - Prometheus, alerts, logging, dashboards
