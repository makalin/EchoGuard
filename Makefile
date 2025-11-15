.PHONY: help setup build up down logs clean init-db create-model test

help:
	@echo "EchoGuard Makefile Commands:"
	@echo "  make setup      - Initial setup (copy .env, install deps)"
	@echo "  make build      - Build Docker images"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs"
	@echo "  make init-db    - Initialize database"
	@echo "  make create-model - Create ML model"
	@echo "  make clean      - Clean up containers and volumes"

setup:
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Setup complete. Please edit .env file with your settings."

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

init-db:
	docker-compose exec backend python scripts/init_db.py

create-model:
	docker-compose exec backend python scripts/create_model.py

clean:
	docker-compose down -v
	docker system prune -f

