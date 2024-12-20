SHELL := /bin/bash
.PHONY: start stop

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
	@echo "Staring DHC Scada Backend Server..."
	@uvicorn {{cookiecutter.module_name}}:application --host 0.0.0.0 --reload --log-config uvicorn_logging.json


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
	ruff check --config=pyproject.toml

# Local/develop dependency and security checking
bandit-scan:
	@bandit -r /project/app -f html -o security_reports/bandit_SAST_report.html -x /tests/

skjold-scan:
	@skjold audit -s pyup -s gemnasium -o json ./requirements.txt > security_reports/skjold_audit_report.json

dead-code-scan:
	@vulture app/

outdated-pkgs-scan:
	@echo "Scanning for outdated python packages!"
	@python /project/scripts/scan_for_outdated_pkgs.py

