SHELL := /bin/bash
.PHONY: start stop

build:
	docker compose -f docker/docker-compose.yml build

start:
	docker compose -f docker/docker-compose.yml up -d
stop:
	docker compose -f docker/docker-compose.yml down

run-server-service-command = \
	docker-compose -f docker/docker-compose.yml run --rm --name server --service-ports shell

shell:
	- $(run-server-service-command)
	- docker compose -f docker/docker-compose.yml down
	- docker system prune -f

serve:
	@echo "Staring DHC Scada Backend Server..."
	@uvicorn app:application --host 0.0.0.0 --reload
