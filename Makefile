.PHONY: help build build-dev up up-dev down clean pull push

# Default to development mode
COMPOSE_FILE = docker-compose.yml
DEV_COMPOSE_FILE = docker-compose.dev.yml

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all services for production
	docker compose -f $(COMPOSE_FILE) build

build-dev: ## Build all services for development (optimized)
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) build

build-fast: ## Build specific services quickly (db and redis from registry)
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) pull db redis
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) build web celery_worker celery_beat frontend mapserver mapcache

up: ## Start all services in production mode
	docker compose -f $(COMPOSE_FILE) up -d

up-dev: ## Start all services in development mode
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) up -d

up-build: ## Build and start all services in development mode
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) up -d --build

logs: ## View logs for all services
	docker compose -f $(COMPOSE_FILE) logs -f

logs-web: ## View logs for web service only
	docker compose -f $(COMPOSE_FILE) logs -f web

logs-mapcache: ## View logs for mapcache service only
	docker compose -f $(COMPOSE_FILE) logs -f mapcache

down: ## Stop all services
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) down

down-volumes: ## Stop all services and remove volumes
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) down -v

clean: ## Remove all containers, networks, and unused images
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) down -v --remove-orphans
	docker system prune -f

pull: ## Pull latest images from registry
	docker compose -f $(COMPOSE_FILE) pull

push: ## Push images to registry (requires proper authentication)
	docker compose -f $(COMPOSE_FILE) push

restart: ## Restart all services
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) restart

restart-web: ## Restart web service only
	docker compose -f $(COMPOSE_FILE) restart web

restart-mapcache: ## Restart mapcache service only
	docker compose -f $(COMPOSE_FILE) restart mapcache

shell-web: ## Get shell access to web container
	docker compose -f $(COMPOSE_FILE) exec web bash

shell-mapcache: ## Get shell access to mapcache container
	docker compose -f $(COMPOSE_FILE) exec mapcache bash

# Development specific targets
dev-build-mapcache: ## Build only mapcache service for development
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) build mapcache

dev-up-mapcache: ## Start only mapcache service for development
	docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) up -d mapcache

# Quick development workflow
quick-start: pull build-fast up-dev ## Quick start: pull registry images, build custom services, start in dev mode