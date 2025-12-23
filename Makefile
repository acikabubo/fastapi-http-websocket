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

docs-build:
	@echo "Building documentation static site..."
	@uv run --group docs mkdocs build

docs-deploy:
	@echo "Deploying documentation to GitHub Pages..."
	@uv run --group docs mkdocs gh-deploy --force

docs-install:
	@echo "Installing documentation dependencies..."
	@uv sync --group docs

# Profiling commands
profile-install:
	@echo "Installing profiling dependencies (Scalene)..."
	@uv sync --group profiling

profile:
	@echo "========================================="
	@echo "Starting application with Scalene profiling..."
	@echo "========================================="
	@echo ""
	@echo "📊 Profiling mode enabled"
	@echo "   → Report will be saved to: profiling_reports/profile_$(shell date +%Y%m%d_%H%M%S).html"
	@echo "   → Press Ctrl+C to stop and generate report"
	@echo ""
	@mkdir -p profiling_reports
	@uv run --group profiling scalene \
		--html \
		--outfile profiling_reports/profile_$(shell date +%Y%m%d_%H%M%S).html \
		--cpu-percent-threshold 1 \
		-- uvicorn app:application --host 0.0.0.0 --port 8000

profile-reduced:
	@echo "========================================="
	@echo "Starting application with reduced-overhead profiling..."
	@echo "========================================="
	@echo ""
	@echo "📊 Low-overhead profiling mode"
	@echo "   → Report: profiling_reports/profile_reduced_$(shell date +%Y%m%d_%H%M%S).html"
	@echo ""
	@mkdir -p profiling_reports
	@uv run --group profiling scalene \
		--html \
		--outfile profiling_reports/profile_reduced_$(shell date +%Y%m%d_%H%M%S).html \
		--reduced-profile \
		--cpu-percent-threshold 2 \
		-- uvicorn app:application --host 0.0.0.0 --port 8000

profile-ws:
	@echo "========================================="
	@echo "Profiling WebSocket handlers only..."
	@echo "========================================="
	@echo ""
	@echo "📊 Profiling WebSocket code"
	@echo "   → Focusing on: app/api/ws/"
	@echo "   → Report: profiling_reports/profile_ws_$(shell date +%Y%m%d_%H%M%S).html"
	@echo ""
	@mkdir -p profiling_reports
	@uv run --group profiling scalene \
		--html \
		--outfile profiling_reports/profile_ws_$(shell date +%Y%m%d_%H%M%S).html \
		--profile-only app/api/ws/ \
		--cpu-percent-threshold 1 \
		-- uvicorn app:application --host 0.0.0.0 --port 8000

profile-memory:
	@echo "========================================="
	@echo "Memory profiling mode..."
	@echo "========================================="
	@echo ""
	@echo "📊 Memory-only profiling"
	@echo "   → Report: profiling_reports/profile_memory_$(shell date +%Y%m%d_%H%M%S).html"
	@echo ""
	@mkdir -p profiling_reports
	@uv run --group profiling scalene \
		--html \
		--outfile profiling_reports/profile_memory_$(shell date +%Y%m%d_%H%M%S).html \
		--memory-only \
		-- uvicorn app:application --host 0.0.0.0 --port 8000

profile-cpu:
	@echo "========================================="
	@echo "CPU profiling mode (fastest)..."
	@echo "========================================="
	@echo ""
	@echo "📊 CPU-only profiling"
	@echo "   → Report: profiling_reports/profile_cpu_$(shell date +%Y%m%d_%H%M%S).html"
	@echo ""
	@mkdir -p profiling_reports
	@uv run --group profiling scalene \
		--html \
		--outfile profiling_reports/profile_cpu_$(shell date +%Y%m%d_%H%M%S).html \
		--cpu-only \
		-- uvicorn app:application --host 0.0.0.0 --port 8000

profile-list:
	@echo "Available profiling reports:"
	@echo ""
	@ls -lh profiling_reports/*.html 2>/dev/null || echo "No reports found. Run 'make profile' to generate one."

profile-clean:
	@echo "Cleaning profiling reports..."
	@rm -rf profiling_reports/*.html
	@echo "✓ All profiling reports deleted"
