# Development Setup

## Prerequisites

- Python 3.13+
- Docker & Docker Compose
- Git
- uv (Python package manager)

## Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/fastapi-http-websocket.git
cd fastapi-http-websocket

# Install dependencies
uv sync

# Start services (PostgreSQL, Redis, Keycloak)
make start

# Run migrations
make migrate

# Start development server
make serve
```

## Detailed Setup

See [Installation Guide](../getting-started/installation.md) for complete instructions.

## Development Tools

```bash
# Code quality
make ruff-check      # Linting
make dead-code-scan  # Find unused code
uvx mypy app/        # Type checking

# Testing
uv run pytest                    # Run all tests
uv run pytest tests/test_foo.py  # Run specific test

# Database
make migration msg="Add field"  # Create migration
make migrate                     # Apply migrations
make rollback                   # Rollback last migration
```

## IDE Setup

### VSCode

Install recommended extensions:
- Python
- Pylance
- Ruff
- SQLTools

### PyCharm

Configure interpreter to use uv virtual environment.

## Related

- [Installation Guide](../getting-started/installation.md)
- [Testing Guide](testing.md)
- [Code Quality](code-quality.md)
