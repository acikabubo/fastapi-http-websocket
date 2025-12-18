# Documentation

This directory contains all project documentation organized by category.

## 📚 Quick Links

### Getting Started
- [Main README](../README.md) - Project overview and quick start
- [Authentication Quick Start](guides/QUICKSTART_AUTH.md) - Get up and running with auth

### Deployment & Production
- [Production Deployment Guide](deployment/PRODUCTION_DEPLOYMENT.md) - Complete production setup
- [Docker Deployment Guide](deployment/DOCKER.md) - Docker best practices and optimization

### Security
- [Security Guide](security/SECURITY_GUIDE.md) - Comprehensive security best practices

### Operations & Maintenance
- [Monitoring Guide](operations/MONITORING.md) - Observability, metrics, and dashboards
- [Troubleshooting Guide](operations/TROUBLESHOOTING.md) - Common issues and solutions
- [Backup & Recovery Guide](operations/BACKUP_RECOVERY.md) - Backup strategies and disaster recovery

### Development Guides
- [Testing Guide](guides/TESTING.md) - How to test the application
- [Authentication Guide](guides/AUTHENTICATION.md) - Working with Keycloak auth
- [User Action Logging](guides/USER_ACTION_LOGGING.md) - Audit logging system
- [Database Migrations](DATABASE_MIGRATIONS.md) - Alembic migration guide

### API Documentation
- [HTTP API Guide](HTTP_API.md) - HTTP endpoint documentation
- [WebSocket API Guide](WEBSOCKET_API.md) - WebSocket handler documentation

### Architecture & Design
- [Project Architecture](architecture/OVERVIEW.md) - System architecture overview
- [Design Patterns Guide](architecture/DESIGN_PATTERNS_GUIDE.md) - Repository, Command, DI patterns
- [Patterns Quick Reference](architecture/PATTERNS_QUICK_REFERENCE.md) - Quick pattern lookup
- [Sequence Diagrams](architecture/SEQUENCE_DIAGRAMS.md) - Request flow visualizations
- [RBAC Alternatives](architecture/RBAC_ALTERNATIVES.md) - Permission system design options
- [ADR-001: Package-Based WebSocket Routing](architecture/ADR-001-package-based-websocket-routing.md)

### Code Quality
- [Docstring Guide](DOCSTRING_GUIDE.md) - Documentation standards

### Improvements & Planning
- [Codebase Improvements](improvements/CODEBASE_IMPROVEMENTS.md) - Comprehensive improvement report
- [Refactoring Summary](archive/REFACTORING_SUMMARY.md) - Historical refactoring notes

### For Claude Code
- [CLAUDE.md](../CLAUDE.md) - Instructions for AI assistant

---

## 📁 Directory Structure

```
docs/
├── README.md                                   # This file
├── DATABASE_MIGRATIONS.md                      # Alembic migration guide
├── DOCSTRING_GUIDE.md                          # Documentation standards
├── HTTP_API.md                                 # HTTP endpoint documentation
├── MIGRATIONS_QUICK_REFERENCE.md               # Migration quick reference
├── WEBSOCKET_API.md                            # WebSocket handler documentation
├── architecture/                               # Architecture documentation
│   ├── ADR-001-package-based-websocket-routing.md
│   ├── ADR_TEMPLATE.md                        # Architecture Decision Records
│   ├── DESIGN_PATTERNS_GUIDE.md               # Repository, Command, DI patterns
│   ├── OVERVIEW.md                            # System architecture
│   ├── PATTERNS_QUICK_REFERENCE.md            # Quick pattern lookup
│   ├── RBAC_ALTERNATIVES.md                   # RBAC design options
│   └── SEQUENCE_DIAGRAMS.md                   # Request flow visualizations
├── deployment/                                 # Production deployment
│   ├── PRODUCTION_DEPLOYMENT.md               # Complete production setup
│   └── DOCKER.md                              # Docker best practices
├── security/                                   # Security documentation
│   └── SECURITY_GUIDE.md                      # Security best practices
├── operations/                                 # Operations & maintenance
│   ├── MONITORING.md                          # Observability and metrics
│   ├── TROUBLESHOOTING.md                     # Common issues and solutions
│   └── BACKUP_RECOVERY.md                     # Backup strategies and DR
├── guides/                                     # How-to guides
│   ├── AUTHENTICATION.md                      # Auth setup and usage
│   ├── QUICKSTART_AUTH.md                     # Quick auth reference
│   ├── TESTING.md                             # Testing guide
│   └── USER_ACTION_LOGGING.md                 # Audit logging system
├── improvements/                               # Improvement tracking
│   └── CODEBASE_IMPROVEMENTS.md               # Comprehensive review
└── archive/                                    # Historical documents
    ├── AUTHENTICATION_REFACTORING.md          # Auth refactoring notes
    └── REFACTORING_SUMMARY.md                 # Refactoring summary
```

---

## 📖 Documentation Guidelines

### When to Add New Documentation

- **Architecture docs** - System design, component interactions, architectural decisions
- **Guides** - Step-by-step instructions, tutorials, how-tos
- **Improvements** - Analysis, proposals, roadmaps
- **Archive** - Completed refactorings, historical context

### Documentation Standards

1. **Use clear headers** - H1 for title, H2 for sections
2. **Include examples** - Code snippets with comments
3. **Link related docs** - Create navigation between documents
4. **Date important docs** - Add creation/update dates to time-sensitive docs
5. **Keep it DRY** - Reference other docs instead of duplicating

### Maintenance

- Review and update docs when code changes significantly
- Archive outdated docs rather than deleting them
- Update this README when adding new documentation
