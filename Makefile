.PHONY: help up down build logs migrate seed test test-backend test-frontend fmt lint backend-dev frontend-dev

help:
	@echo "Public Records Research MVP - common commands"
	@echo "  make up            - build & start the full stack (docker compose up --build)"
	@echo "  make down          - stop the stack"
	@echo "  make migrate       - run alembic migrations in the backend container"
	@echo "  make seed          - seed demo data in the backend container"
	@echo "  make test          - run backend + frontend tests in containers"
	@echo "  make test-backend  - run backend pytest in the container"
	@echo "  make test-frontend - run frontend tests in the container"
	@echo "  make backend-dev   - run backend locally (sqlite, no docker)"
	@echo "  make frontend-dev  - run frontend locally"

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.seed

test: test-backend test-frontend

test-backend:
	docker compose exec backend pytest

test-frontend:
	docker compose exec frontend npm test

fmt:
	cd backend && ruff format app && ruff check --fix app

lint:
	cd backend && ruff check app

backend-dev:
	cd backend && uvicorn app.main:app --reload

frontend-dev:
	cd frontend && npm run dev
