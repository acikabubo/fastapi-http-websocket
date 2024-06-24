.PHONY: init-db start-server run-tests deploy

init-db:
    python app/db.py

start-server:
    docker-compose up --build

run-tests:
    pytest tests/

deploy:
    # Add your deployment commands here
    echo "Deploying application..."
