# FastAPI HTTP/WebSocket Project Template

This is a Cookiecutter template for creating FastAPI applications with both HTTP and WebSocket support, role-based access control (RBAC), Keycloak authentication, and PostgreSQL database integration.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Dual Protocol Support**: HTTP REST endpoints and WebSocket handlers
- **Authentication**: Keycloak integration with JWT token validation
- **Authorization**: Role-based access control (RBAC) system
- **Database**: PostgreSQL with SQLModel (async SQLAlchemy)
- **Caching**: Redis integration for session management and caching
- **Package Router**: Custom routing system for WebSocket requests
- **Docker Support**: Containerized development environment
- **Testing**: Comprehensive test suite with pytest
- **Code Quality**: Pre-commit hooks with ruff, mypy, bandit, and more
- **Type Safety**: Full type hints with strict mypy checking
- **Documentation**: 80%+ docstring coverage requirement

## Prerequisites

Before using this template, ensure you have the following installed:

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- [Cookiecutter](https://github.com/cookiecutter/cookiecutter) - Project templating tool
- Docker and Docker Compose (for containerized development)
- Git

### Installing Prerequisites

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install cookiecutter
uv tool install cookiecutter
```

## Quick Start

### 1. Generate a New Project

From the parent directory of this template:

```bash
cookiecutter fastapi-http-websocket/.worktree
```

Or directly from the Git repository:

```bash
cookiecutter https://github.com/acikabubo/fastapi-http-websocket.git --directory=.worktree --checkout project-template-develop
```

### 2. Answer Template Questions

You'll be prompted for the following information:

- **project_name**: Your project name (e.g., "My Awesome API")
- **project_description**: A brief description of your project
- **project_slug**: Auto-generated from project_name (e.g., "my_awesome_api")
- **module_name**: The main module name (default: "src")

Example:
```
project_name [Project]: My Awesome API
project_description []: A powerful FastAPI application with WebSocket support
project_slug [my_awesome_api]:
module_name [src]:
```

### 3. Navigate to Your New Project

```bash
cd my_awesome_api
```

### 4. Initialize the Project

The template includes a post-generation hook that automatically:
- Initializes a Git repository
- Creates the initial commit
- Sets up the project structure

### 5. Set Up the Development Environment

#### Option A: Local Development

```bash
# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start the development server
make serve
```

#### Option B: Docker Development

```bash
# Build and start all services
make build
make start

# Enter the development shell
make shell

# Inside the container, run the server
uvicorn src:application --host 0.0.0.0 --reload
```

## Project Structure

After generation, your project will have the following structure:

```
my_awesome_api/
├── src/                          # Main application module
│   ├── __init__.py              # Application factory
│   ├── api/
│   │   ├── http/                # HTTP endpoint handlers
│   │   └── ws/                  # WebSocket handlers
│   │       ├── consumers/       # WebSocket endpoint classes
│   │       ├── handlers/        # WebSocket message handlers
│   │       ├── constants.py     # PkgID and response codes
│   │       └── validation.py    # Request validation
│   ├── auth.py                  # Authentication backend
│   ├── managers/                # Singleton managers
│   │   ├── keycloak_manager.py
│   │   ├── rbac_manager.py
│   │   └── websocket_connection_manager.py
│   ├── middlewares/             # Custom middleware
│   ├── models/                  # Database models
│   ├── routing.py               # Package router
│   ├── schemas/                 # Pydantic schemas
│   ├── settings.py              # Configuration
│   ├── storage/                 # Database and Redis
│   ├── tasks/                   # Background tasks
│   └── utils/                   # Utility functions
├── tests/                       # Test suite
├── docker/                      # Docker configuration
├── actions.json                 # RBAC role definitions
├── Makefile                     # Development commands
├── pyproject.toml              # Project configuration
└── README.md                    # Project documentation
```

## Configuration

The template uses environment variables for configuration. Key settings include:

### Database
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `POSTGRES_HOST`, `POSTGRES_PORT`

### Redis
- `REDIS_IP`, `MAIN_REDIS_DB`, `AUTH_REDIS_DB`

### Keycloak
- `KEYCLOAK_BASE_URL`, `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`
- `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`

### Application
- `ACTIONS_FILE_PATH`: Path to RBAC configuration (default: `actions.json`)
- `EXCLUDED_PATHS`: Regex patterns for paths excluded from authentication

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/test_websocket.py

# Run with coverage
uv run pytest --cov=src
```

### Code Quality

```bash
# Run linter
make ruff-check

# Format code
uvx ruff format

# Type checking
uvx mypy src/

# Check docstring coverage
uvx interrogate src/

# Find dead code
make dead-code-scan

# Spell checking
uvx typos
```

### Security Scanning

```bash
# SAST scanning
make bandit-scan

# Dependency vulnerability scanning
make skjold-scan

# Check outdated packages
make outdated-pkgs-scan
```

### Adding WebSocket Handlers

```bash
# Generate a new handler from template
make new-ws-handlers

# View all registered handlers
make ws-handlers
```

## Architecture Overview

### HTTP Request Flow
1. Request hits FastAPI endpoint
2. `AuthenticationMiddleware` authenticates via Keycloak
3. `PermAuthHTTPMiddleware` checks RBAC permissions
4. Request reaches endpoint handler

### WebSocket Request Flow
1. Client connects to `/web` endpoint
2. Authentication via Keycloak token in query params
3. Client sends JSON: `{"pkg_id": <int>, "req_id": "<uuid>", "data": {...}}`
4. `PackageRouter` validates, checks permissions, dispatches to handler
5. Handler returns `ResponseModel` sent back to client

### Key Components

- **PackageRouter**: Central routing for WebSocket requests
- **AuthBackend**: JWT token validation
- **RBACManager**: Permission checking against `actions.json`
- **WebSocketConnectionManager**: Manages active connections
- **SingletonMeta**: Thread-safe singleton pattern for managers

## RBAC Configuration

Edit `actions.json` to define roles and permissions:

```json
{
  "roles": ["admin", "user", "get-authors"],
  "ws": {
    "100": "get-authors",
    "101": "admin"
  },
  "http": {
    "/api/users": {
      "GET": "user",
      "POST": "admin"
    }
  }
}
```

## Docker Services

The template includes Docker Compose configuration for:

- **PostgreSQL**: Database server
- **Redis**: Caching and session storage
- **Keycloak**: Authentication server
- **App**: Your FastAPI application

## Pre-commit Hooks

All commits are validated against:

- **ruff**: Linting and formatting (79 char line length)
- **mypy**: Strict type checking
- **interrogate**: ≥80% docstring coverage
- **typos**: Spell checking
- **bandit**: Security scanning
- **skjold**: Dependency vulnerability checks

## Customization

After generating your project:

1. **Update `actions.json`**: Define your roles and permissions
2. **Add models**: Create database models in `src/models/`
3. **Add HTTP endpoints**: Create routers in `src/api/http/`
4. **Add WebSocket handlers**: Create handlers in `src/api/ws/handlers/`
5. **Configure environment**: Update `.env` with your settings
6. **Update README**: Customize the generated README for your project

## Troubleshooting

### Common Issues

**Import errors after generation:**
```bash
uv sync  # Reinstall dependencies
```

**Database connection errors:**
```bash
make start  # Ensure Docker services are running
```

**Tests failing:**
```bash
# Check if all services are running
docker-compose ps

# Restart services if needed
make stop && make start
```

## Contributing to the Template

To contribute improvements to this template:

1. Clone the repository
2. Make changes in the `.worktree/` directory
3. Test by generating a new project
4. Submit a pull request to the `project-template-develop` branch

## Support

For issues, questions, or contributions:

- **Repository**: https://github.com/acikabubo/fastapi-http-websocket
- **Issues**: https://github.com/acikabubo/fastapi-http-websocket/issues
- **Template Branch**: `project-template-develop`

## License

This template is provided as-is for creating FastAPI projects with HTTP and WebSocket support.

---

**Generated with**: Cookiecutter
**Template Version**: 1.0.0
**Last Updated**: 2025-11-27
