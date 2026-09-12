# Mizan Labs Platform v2 — developer entry points.
# Recipes use ">" as the prefix so the file needs no tab characters.
.RECIPEPREFIX = >
.DEFAULT_GOAL := help
SHELL := /bin/bash

UV ?= uv
BACKEND := backend
COMPOSE := docker compose -f docker-compose.dev.yml

.PHONY: storybook help setup dev api worker web test test-backend test-frontend lint lint-backend lint-frontend fmt build migrate makemigrations seed e2e db-up db-down openapi clean

help: ## Show this help
> @grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Install backend (uv) and front-end (pnpm) dependencies
> $(UV) sync --all-groups
> pnpm install

db-up: ## Start PostgreSQL, MinIO and Mailpit with Docker Compose
> $(COMPOSE) up -d db minio minio-init mailpit

db-down: ## Stop the development services
> $(COMPOSE) down

migrate: ## Apply database migrations
> cd $(BACKEND) && $(UV) run python manage.py migrate --noinput

makemigrations: ## Generate migrations for model changes
> cd $(BACKEND) && $(UV) run python manage.py makemigrations

seed: ## Create the demo tenant (branch, roles, numbering, workflows, definitions, users)
> cd $(BACKEND) && $(UV) run python manage.py seed_demo

api: ## Run the API with auto-reload on http://127.0.0.1:8000
> cd $(BACKEND) && $(UV) run granian --interface asgi --host 127.0.0.1 --port 8000 --reload mizan.config.asgi:application

worker: ## Run the Procrastinate worker
> cd $(BACKEND) && $(UV) run python manage.py procrastinate worker

web: ## Run the four front-end apps in dev mode
> pnpm turbo run dev

dev: ## Run API, worker and front-ends together
> $(MAKE) -j3 api worker web

test: test-backend test-frontend ## Run every test suite

test-backend: ## Run backend tests (needs PostgreSQL; see backend/.env.example)
> cd $(BACKEND) && $(UV) run pytest

test-frontend: ## Run front-end tests
> pnpm turbo run test

lint: lint-backend lint-frontend ## Run every linter and type checker

lint-backend: ## ruff, mypy and import-linter
> cd $(BACKEND) && $(UV) run ruff check . && $(UV) run ruff format --check . && $(UV) run mypy mizan && $(UV) run lint-imports

lint-frontend: ## eslint and tsc across the workspace
> pnpm turbo run lint typecheck

fmt: ## Format backend code
> cd $(BACKEND) && $(UV) run ruff format . && $(UV) run ruff check --fix .

storybook: ## Open the design system in Storybook
> pnpm --filter @mizan/ui storybook

openapi: ## Export the OpenAPI document and regenerate the TypeScript client
> cd $(BACKEND) && $(UV) run python manage.py export_openapi ../frontend/packages/api-client/src/generated/openapi.json
> pnpm --filter @mizan/api-client generate

build: ## Build the container image and the front-end bundles
> docker build -t mizan-labs/platform:dev -f backend/Dockerfile .
> pnpm turbo run build

e2e: ## Run Playwright end-to-end tests against the built apps
> pnpm turbo run build --filter='./frontend/apps/*' && pnpm --filter @mizan/e2e test

clean: ## Remove caches and build outputs
> rm -rf .turbo frontend/apps/*/dist frontend/packages/*/dist backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache
