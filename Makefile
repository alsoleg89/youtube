.PHONY: up down logs test lint migrate shell-backend

COMPOSE = docker compose -f infra/docker-compose.yml

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

test:
	$(COMPOSE) exec backend pytest tests/ -v

lint:
	$(COMPOSE) exec backend ruff check .

migrate:
	$(COMPOSE) exec backend alembic upgrade head

shell-backend:
	$(COMPOSE) exec backend bash
