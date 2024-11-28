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
	docker-compose -f docker/docker-compose.yml run --rm --name hw-server --service-ports shell

shell:
	- $(run-server-service-command)
	- docker compose -f docker/docker-compose.yml down
	- docker system prune -f

# @fastapi run app
serve:
	@echo "Staring DHC Scada Backend Server..."
	@uvicorn app:application --host 0.0.0.0 --reload


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
