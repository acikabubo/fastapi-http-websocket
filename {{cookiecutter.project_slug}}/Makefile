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

start:
	docker compose -f docker/docker-compose.yml up -d
stop:
	docker compose -f docker/docker-compose.yml down

run-server-service-command = \
	docker compose -f docker/docker-compose.yml run --rm --name {{cookiecutter.project_slug}}-server --service-ports shell
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

start:
	docker compose -f docker/docker-compose.yml up -d
stop:
	docker compose -f docker/docker-compose.yml down

run-server-service-command = \
	docker compose -f docker/docker-compose.yml run --rm --name {{cookiecutter.project_slug}}-server --service-ports shell

shell:
	- $(run-server-service-command)
	- docker compose -f docker/docker-compose.yml down
	- docker system prune -f

# @fastapi run app
serve:
	@echo "Staring {{cookiecutter.project_name}} Backend Server..."
	@uvicorn {{cookiecutter.module_name}}:application --host 0.0.0.0 --reload --log-config uvicorn_logging.json

test:
	@echo "Running tests with pytest..."
	@uv run pytest tests

# To execute this commands first need to be executed `make shell`
ws-handlers:
	@echo "Make table with PkgID's and related websocket handlers"
	@python cli.py ws-handlers

new-ws-handlers:
	@echo "Generate new websocket handler"
	@python cli.py generate-new-ws-handler

code-docs:
	pydoc -n 0.0.0.0 -p 8080

ruff-check:
	uvx ruff check --config=pyproject.toml

# Local/develop dependency and security checking
bandit-scan:
	@uvx bandit -r /{{cookiecutter.project_slug}}/{{cookiecutter.project_name}} -f html -o .security_reports/bandit_SAST_report.html -x /tests/

skjold-scan:
	@uvx skjold audit -s pyup -s gemnasium -o json ./uv.lock > .security_reports/skjold_audit_report.json

dead-code-scan:
	@uvx vulture {{cookiecutter.project_name}}/

outdated-pkgs-scan:
	@echo "Scanning for outdated python packages!"
	@python /{{cookiecutter.project_slug}}/scripts/scan_for_outdated_pkgs.py

shell:
	- $(run-server-service-command)
	- docker compose -f docker/docker-compose.yml down
	- docker system prune -f

# @fastapi run app
serve:
	@echo "Staring {{cookiecutter.module_name}} Backend Server..."
	@uvicorn {{cookiecutter.module_name}}:application --host 0.0.0.0 --reload --log-config uvicorn_logging.json

test:
	@echo "Running tests with pytest..."
	@uv run pytest tests

# To execute this commands first need to be executed `make shell`
ws-handlers:
	@echo "Make table with PkgID's and related websocket handlers"
	@python cli.py ws-handlers

new-ws-handlers:
	@echo "Generate new websocket handler"
	@python cli.py generate-new-ws-handler

code-docs:
	pydoc -n 0.0.0.0 -p 8080

ruff-check:
	uvx ruff check --config=pyproject.toml

# Local/develop dependency and security checking
bandit-scan:
	@uvx bandit -r /{{cookiecutter.project_slug}}/app -f html -o .security_reports/bandit_SAST_report.html -x /tests/

skjold-scan:
	@uvx skjold audit -s pyup -s gemnasium -o json ./uv.lock > .security_reports/skjold_audit_report.json

dead-code-scan:
	@uvx vulture app/

outdated-pkgs-scan:
	@echo "Scanning for outdated python packages!"
	@python /{{cookiecutter.project_slug}}/scripts/scan_for_outdated_pkgs.py

