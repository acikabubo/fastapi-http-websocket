# Development Guide

This guide covers running the application, Docker development, and WebSocket handler management.

## Table of Contents

- [Running the Application](#running-the-application)
- [Docker Development](#docker-development)
- [WebSocket Handler Management](#websocket-handler-management)
- [WebSocket Protocol Documentation](#websocket-protocol-documentation)
- [Related Documentation](#related-documentation)

## Running the Application

### Start the Server

```bash
# Start the server with hot-reload
make serve

# Or using uvicorn directly
uvicorn app:application --host 0.0.0.0 --reload
```

## Docker Development

### Build and Run

```bash
# Build containers
make build

# Start services (PostgreSQL, Redis, Keycloak, etc.)
make start

# Stop services
make stop

# Enter development shell
make shell
```

## WebSocket Handler Management

### Show Handlers

```bash
# Show table of PkgIDs and their handlers
make ws-handlers
```

### Generate New Handler

```bash
# Generate a new WebSocket handler (uses f-string code generator)
make new-ws-handlers

# Or use the generator directly with options:
python generate_ws_handler.py handler_name PKG_ID_NAME [options]

# With JSON schema validation
python generate_ws_handler.py create_author CREATE_AUTHOR --schema

# With pagination
python generate_ws_handler.py get_authors GET_AUTHORS --paginated

# With RBAC roles
python generate_ws_handler.py delete_author DELETE_AUTHOR --roles admin delete-author

# Overwrite existing file
python generate_ws_handler.py handler_name PKG_ID --overwrite
```

## WebSocket Protocol Documentation

For client developers implementing WebSocket clients, see the comprehensive protocol specification at `docs_site/guides/websocket-protocol.md`:

- Connection URL format and authentication
- Message format (JSON and Protobuf)
- Status codes (RSPCode) and error handling
- Available Package IDs (PkgID) with schemas
- Connection lifecycle and sequence diagrams
- Rate limiting and best practices
- Troubleshooting guide

This documentation is also available online at: https://acikabubo.github.io/fastapi-http-websocket/guides/websocket-protocol/

## Related Documentation

- [Git Workflow Guide](git-workflow.md) - Git workflow, issue management, worktree syncing
- [Architecture Guide](architecture-guide.md) - Design patterns, components, request flow
- [Testing Guide](testing-guide.md) - Test infrastructure, fixtures, load/chaos tests
- [Code Quality Guide](code-quality-guide.md) - Linting, type checking, pre-commit hooks
- [Configuration Guide](configuration-guide.md) - Settings, environment variables, validation
- [Database Guide](database-guide.md) - Sessions, migrations, pagination, relationships
- [Monitoring Guide](monitoring-guide.md) - Prometheus, alerts, logging, dashboards
