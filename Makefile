SHELL := /bin/bash
.PHONY: start stop

ifeq ($(shell uname), Darwin)
export UID=1000
export GID=1000
else
export UID=$(shell id -u)
export GID=$(shell id -g)
endif

build:
	docker compose -f docker/docker-compose.yml build

# Start all services: PostgreSQL, Redis, Keycloak, Prometheus, Grafana
start:
	docker compose -f docker/docker-compose.yml up -d

stop:
	docker compose -f docker/docker-compose.yml down

run-server-service-command = \
	docker compose -f docker/docker-compose.yml run --rm --name hw-server --service-ports shell

shell:
	- $(run-server-service-command)
	- docker compose -f docker/docker-compose.yml down
	- docker system prune -f

# Start hw-server service in background (for log collection via Alloy → Loki → Grafana)
start-server:
	@echo "Starting hw-server service in background..."
	docker compose -f docker/docker-compose.yml up -d hw-server

# Stop hw-server service
stop-server:
	@echo "Stopping hw-server service..."
	docker compose -f docker/docker-compose.yml stop hw-server
	docker compose -f docker/docker-compose.yml rm -f hw-server

# @fastapi run app
serve:
	@echo "Staring DHC Scada Backend Server..."
	@uvicorn app:application --host 0.0.0.0 --reload --log-config uvicorn_logging.json

test:
	@echo "Running tests with pytest..."
	@uv run pytest tests

test-coverage:
	@echo "Running tests with coverage..."
	@uv run pytest --cov=app --cov-report=term-missing --cov-report=html tests

# To execute this commands first need to be executed `make shell`
ws-handlers:
	@echo "Make table with PkgID's and related websocket handlers"
	@uv run python cli.py ws-handlers

new-ws-handlers:
	@echo "Generate new websocket handler"
	@uv run python cli.py generate-new-ws-handler

code-docs:
	@uv run pydoc -n 0.0.0.0 -p 1234

ipython:
	@uv run ipython

ruff-check:
	uvx ruff check --config=pyproject.toml

# Local/develop dependency and security checking
bandit-scan:
	@uvx bandit -r /project/app -f html -o .security_reports/bandit_SAST_report.html -x /tests/

skjold-scan:
	@uvx skjold audit -s pyup -s gemnasium -o json ./uv.lock > .security_reports/skjold_audit_report.json

dead-code-scan:
	@uvx vulture app/

outdated-pkgs-scan:
	@echo "Scanning for outdated python packages!"
	@python /project/scripts/scan_for_outdated_pkgs.py

# Database migration commands
migrate:
	@echo "Applying database migrations..."
	@uv run alembic upgrade head

migration:
	@test -n "$(msg)" || (echo "Usage: make migration msg='description'"; exit 1)
	@echo "Generating new migration: $(msg)"
	@uv run alembic revision --autogenerate -m "$(msg)"

rollback:
	@echo "Rolling back last migration..."
	@uv run alembic downgrade -1

migration-history:
	@echo "Migration history:"
	@uv run alembic history --verbose

migration-current:
	@echo "Current migration version:"
	@uv run alembic current

migration-stamp:
	@test -n "$(rev)" || (echo "Usage: make migration-stamp rev='revision_id'"; exit 1)
	@echo "Stamping database at revision: $(rev)"
	@uv run alembic stamp $(rev)

test-migrations:
	@echo "Testing database migrations (upgrade/downgrade)..."
	@uv run python scripts/test_migrations.py

# Documentation commands
docs-serve:
	@echo "Serving documentation at http://127.0.0.1:8000"
	@uv run --group docs mkdocs serve

docs-build:
	@echo "Building documentation static site..."
	@uv run --group docs mkdocs build

docs-deploy:
	@echo "Deploying documentation to GitHub Pages..."
	@uv run --group docs mkdocs gh-deploy --force

docs-install:
	@echo "Installing documentation dependencies..."
	@uv sync --group docs
