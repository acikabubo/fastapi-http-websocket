# Documentation

This directory contains comprehensive guides for {{cookiecutter.project_name}}.

## Guides

### Core Documentation
- **[Advanced Features](guides/ADVANCED_FEATURES.md)** - Optional production-ready optimizations
  - Protocol Buffers for efficient WebSocket messaging
  - Scalene performance profiling
  - Implementation guides and best practices

- **[Monitoring & Observability](guides/MONITORING.md)** - Complete monitoring stack setup
  - Prometheus metrics collection
  - Grafana dashboards (FastAPI, Keycloak, Audit Logs)
  - Loki centralized logging with Grafana Alloy
  - LogQL query examples

{% if cookiecutter.enable_audit_logging == 'yes' %}- **[User Action Logging](guides/USER_ACTION_LOGGING.md)** - Audit logging system
  - Setup and configuration
  - Recording user actions
  - Querying audit logs
  - Compliance and security monitoring
{% endif %}

## Quick Links

### Getting Started
- [Main README](../README.md) - Quick start and architecture overview
- [Project Structure](../README.md#project-structure) - Code organization
- [WebSocket API](../README.md#websocket-api) - Request/response formats

### Development
- [Creating WebSocket Handlers](../README.md#creating-websocket-handlers)
- [Database Pagination](../README.md#database-pagination)
- [RBAC Permissions](../README.md#rbac-permissions)
- [Code Quality Tools](../README.md#code-quality)

### Operations
- [Configuration](../README.md#configuration) - Environment variables
- [Docker Development](../README.md#docker-development) - Container setup
- [Security Scanning](../README.md#security-scanning) - SAST and dependency checks

## Contributing

When adding new documentation:
1. Place guides in `docs/guides/` directory
2. Update this README with links to new guides
3. Reference from main README if relevant to quick start
4. Use clear headers and code examples
5. Include cookiecutter placeholders where appropriate
