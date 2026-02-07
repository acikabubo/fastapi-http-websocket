SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help start stop

ifeq ($(shell uname), Darwin)
export UID=1000
export GID=1000
else
export UID=$(shell id -u)
export GID=$(shell id -g)
endif

# Docker socket group ID (needed for Traefik/Alloy to access Docker API)
export DOCKER_GID=$(shell getent group docker | cut -d: -f3)

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Docker Services

build: ## Build Docker containers
	docker compose -f docker/docker-compose.yml build

start: ## Start all services (PostgreSQL, Redis, Keycloak, Prometheus, Grafana, Loki)
	docker compose -f docker/docker-compose.yml up -d

stop: ## Stop all Docker services
	docker compose -f docker/docker-compose.yml down

run-server-service-command = \
	docker compose -f docker/docker-compose.yml run --rm --name hw-server --service-ports shell

shell: ## Enter development shell (interactive container with all services)
	- $(run-server-service-command)
	- docker compose -f docker/docker-compose.yml down
	- docker system prune -f

start-server: ## Start hw-server service in background (for log collection via Alloy → Loki → Grafana)
	@echo "Starting hw-server service in background..."
	docker compose -f docker/docker-compose.yml up -d hw-server

stop-server: ## Stop hw-server service
	@echo "Stopping hw-server service..."
	docker compose -f docker/docker-compose.yml stop hw-server
	docker compose -f docker/docker-compose.yml rm -f hw-server

##@ Development

serve: ## Start FastAPI application with hot-reload (local development)
	@echo "Starting FastAPI Backend Server with hot-reload..."
	@uvicorn app:application --host 0.0.0.0 --reload --log-config uvicorn_logging.json

##@ Testing

test: ## Run tests in parallel with pytest-xdist
	@echo "Running tests in parallel with pytest-xdist..."
	@uv run pytest -n auto tests

test-serial: ## Run tests sequentially (without parallelization)
	@echo "Running tests sequentially..."
	@uv run pytest tests

test-coverage: ## Run tests with coverage report (terminal + HTML)
	@echo "Running tests with coverage..."
	@uv run pytest --cov=app --cov-report=term-missing --cov-report=html tests

test-coverage-parallel: ## Run tests in parallel with coverage
	@echo "Running tests in parallel with coverage..."
	@uv run pytest -n auto --cov=app --cov-report=term-missing --cov-report=html tests

test-integration: ## Run integration tests with real Keycloak container (requires Docker, run OUTSIDE container)
	@echo "Running integration tests with testcontainers..."
	@echo "⚠️  IMPORTANT: Run this command OUTSIDE the Docker container (on host machine)"
	@echo "Note: This will start a real Keycloak container (may take 30-60s)"
	@uv run pytest -m integration tests/integration/ -v -s

test-unit: ## Run only unit tests (skip integration, load, and chaos tests)
	@echo "Running unit tests (excluding integration, load, and chaos tests)..."
	@uv run pytest -m "not integration and not load and not chaos" tests

##@ WebSocket Handlers

ws-handlers: ## Display table of PkgID's and related websocket handlers
	@echo "Make table with PkgID's and related websocket handlers"
	@uv run python cli.py ws-handlers

new-ws-handlers: ## Generate new websocket handler (interactive)
	@echo "Generate new websocket handler"
	@uv run python cli.py generate-new-ws-handler

##@ Code Quality

ipython: ## Start IPython interactive shell
	@uv run ipython

code-docs: ## Start pydoc documentation server on port 1234
	@uv run pydoc -n 0.0.0.0 -p 1234

ruff-check: ## Run ruff linter (check only, no fixes)
	uvx ruff check --config=pyproject.toml

##@ Security Scanning

bandit-scan: ## Run Bandit SAST security scanner (generates HTML report)
	@uvx bandit -r /project/app -f html -o .security_reports/bandit_SAST_report.html -x /tests/

skjold-scan: ## Scan dependencies for known vulnerabilities (generates JSON report)
	@uvx skjold audit -s pyup -s gemnasium -o json ./uv.lock > .security_reports/skjold_audit_report.json

dead-code-scan: ## Find dead code with Vulture
	@echo "Running dead code detection..."
	@uvx vulture app/

dead-code-fix: ## Remove unused imports with ruff and re-scan
	@echo "Removing unused imports with ruff..."
	@uvx ruff check app/ --fix
	@echo "Re-running dead code scan..."
	@uvx vulture app/

outdated-pkgs-scan: ## Scan for outdated Python packages
	@echo "Scanning for outdated python packages!"
	@python /project/scripts/scan_for_outdated_pkgs.py

##@ Database Migrations

migrate: ## Apply all pending database migrations
	@echo "Applying database migrations..."
	@uv run alembic upgrade head

migration: ## Generate new migration (usage: make migration msg='description')
	@test -n "$(msg)" || (echo "Usage: make migration msg='description'"; exit 1)
	@echo "Generating new migration: $(msg)"
	@uv run alembic revision --autogenerate -m "$(msg)"

rollback: ## Rollback the last database migration
	@echo "Rolling back last migration..."
	@uv run alembic downgrade -1

migration-history: ## Show migration history
	@echo "Migration history:"
	@uv run alembic history --verbose

migration-current: ## Show current migration version
	@echo "Current migration version:"
	@uv run alembic current

migration-stamp: ## Stamp database at specific revision (usage: make migration-stamp rev='revision_id')
	@test -n "$(rev)" || (echo "Usage: make migration-stamp rev='revision_id'"; exit 1)
	@echo "Stamping database at revision: $(rev)"
	@uv run alembic stamp $(rev)

test-migrations: ## Test migrations (upgrade/downgrade cycle)
	@echo "Testing database migrations (upgrade/downgrade)..."
	@uv run python scripts/test_migrations.py

##@ Documentation

docs-install: ## Install MkDocs documentation dependencies
	@echo "Installing documentation dependencies..."
	@uv sync --group docs

docs-serve: ## Start MkDocs documentation server (http://localhost:8001)
	@echo "========================================="
	@echo "Starting MkDocs documentation server..."
	@echo "========================================="
	@echo ""
	@echo "📚 Access documentation at:"
	@echo "   → http://localhost:8001 (direct)"
	@echo "   → http://docs.localhost (via Traefik)"
	@echo ""
	@echo "Press Ctrl+C to stop the server"
	@echo ""
	@uv run --group docs mkdocs serve --dev-addr=0.0.0.0:8001

docs-build: ## Build documentation static site
	@echo "Building documentation static site..."
	@uv run --group docs mkdocs build

docs-deploy: ## Deploy documentation to GitHub Pages
	@echo "Deploying documentation to GitHub Pages..."
	@uv run --group docs mkdocs gh-deploy --force

##@ Profiling (Scalene)

profile-install: ## Install Scalene profiling dependencies
	@echo "Installing profiling dependencies (Scalene)..."
	@uv sync --group profiling

profile: ## Start application with Scalene profiling
	@echo "========================================="
	@echo "Starting application with Scalene profiling..."
	@echo "========================================="
	@echo ""
	@echo "📊 Profiling mode enabled"
	@echo "   → Profile saved to: scalene-profile.json"
	@echo "   → View report: make profile-view"
	@echo "   → Press Ctrl+C to stop profiling"
	@echo ""
	@uv run --group profiling scalene run run_server.py

profile-view: ## Open Scalene profile in browser
	@echo "Opening Scalene profile in browser..."
	@uv run --group profiling scalene view

profile-view-cli: ## Display Scalene profile in terminal
	@echo "Displaying Scalene profile in terminal..."
	@uv run --group profiling scalene view --cli

profile-clean: ## Clean profiling data
	@echo "Cleaning profiling data..."
	@rm -f scalene-profile.json
	@echo "✓ Profile data deleted"

##@ Protocol Buffers

protobuf-install: ## Install protobuf dependencies
	@echo "Installing protobuf dependencies..."
	@uv sync --group protobuf

protobuf-generate: ## Generate Python code from .proto files
	@echo "Generating Python code from .proto files..."
	@mkdir -p app/schemas/proto
	@uv run --group protobuf python -m grpc_tools.protoc \
		-I=proto \
		--python_out=app/schemas/proto \
		--pyi_out=app/schemas/proto \
		proto/websocket.proto
	@echo "✓ Protobuf code generated in app/schemas/proto/"

protobuf-clean: ## Clean generated protobuf code
	@echo "Cleaning generated protobuf code..."
	@rm -rf app/schemas/proto
	@echo "✓ Protobuf code cleaned"
