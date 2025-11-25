# Documentation

This directory contains all project documentation organized by category.

## 📚 Quick Links

### Getting Started
- [Main README](../README.md) - Project overview and quick start
- [Authentication Quick Start](guides/QUICKSTART_AUTH.md) - Get up and running with auth

### Development Guides
- [Testing Guide](guides/TESTING.md) - How to test the application
- [Authentication Guide](guides/AUTHENTICATION.md) - Working with Keycloak auth

### Architecture & Design
- [Project Architecture](architecture/OVERVIEW.md) - System architecture overview
- [RBAC Alternatives](architecture/RBAC_ALTERNATIVES.md) - Permission system design options

### Improvements & Planning
- [Codebase Improvements](improvements/CODEBASE_IMPROVEMENTS.md) - Comprehensive improvement report
- [Refactoring Summary](archive/REFACTORING_SUMMARY.md) - Historical refactoring notes

### For Claude Code
- [CLAUDE.md](../CLAUDE.md) - Instructions for AI assistant

---

## 📁 Directory Structure

```
docs/
├── README.md                          # This file
├── architecture/                      # Architecture documentation
│   ├── OVERVIEW.md                   # System architecture
│   └── RBAC_ALTERNATIVES.md          # RBAC design options
├── guides/                            # How-to guides
│   ├── AUTHENTICATION.md             # Auth setup and usage
│   ├── QUICKSTART_AUTH.md            # Quick auth reference
│   └── TESTING.md                    # Testing guide
├── improvements/                      # Improvement tracking
│   └── CODEBASE_IMPROVEMENTS.md      # Comprehensive review
└── archive/                           # Historical documents
    ├── AUTHENTICATION_REFACTORING.md # Auth refactoring notes
    └── REFACTORING_SUMMARY.md        # Refactoring summary
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
