# Architecture

Learn about the system architecture, design patterns, and technical decisions.

## Contents

- [Overview](overview.md) - System architecture and component interactions
- [Design Patterns](design-patterns.md) - Repository, Command, and Dependency Injection patterns
- [Request Flow](request-flow.md) - HTTP and WebSocket request processing
- [RBAC System](rbac.md) - Role-based access control implementation

## Architecture Diagram

```mermaid
graph TB
    Client[Client] -->|HTTP/WS| Traefik[Traefik]
    Traefik --> App[FastAPI App]
    App --> PG[(PostgreSQL)]
    App --> Redis[(Redis)]
    App --> KC[Keycloak]
```

See [Overview](overview.md) for detailed architecture documentation.
