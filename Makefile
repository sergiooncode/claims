COMPOSE_CMD = TAG=$(tag) docker compose

export UID := $(shell id -u)
export GID := $(shell id -g)

.PHONY: clean
clean: ## Stop and delete containers and volumes (will cause data loss)
	$(COMPOSE_CMD) down -v --remove-orphans

.PHONY: down
down: ## Stop containers without removing volumes (preserves database)
	$(COMPOSE_CMD) down --remove-orphans

.PHONY: manage
manage: ## Run python manage.py commands. Example make manage cmd=collectstatic args=--noinput
	$(COMPOSE_CMD) run --rm claims-service python manage.py $(cmd) $(args)

.PHONY: .env.local
.env.local: ## Create local.env file
	@if [ "$(OF_APPLICATION_USE_CASE)" = "ofpi" ]; then \
		echo "Creating .env.local file" && \
		cp -n .env.local || true; \
	else \
		echo "Creating .env.local file" && \
		touch .env.local; \
	fi

.PHONY: external-net
external-net: SERVICE_GRP_NET=service-grp-net
external-net: ## Create common external docker network (if missing).
	# this network is shared across services and marked as external in docker compose (thus not managed by it).
	@if [ "$$(docker network ls --filter name=$(SERVICE_GRP_NET) --format '{{ .Name }}')" != $(SERVICE_GRP_NET) ]; then \
		docker network create $(SERVICE_GRP_NET); \
	fi

.PHONY: build
build:
	$(COMPOSE_CMD) build

.PHONY: up
up: .env.local ## Boot up containers
	$(COMPOSE_CMD) up -d
	sleep 1
	$(COMPOSE_CMD) ps

.PHONY: migrate
migrate: ## Run database migrations
	$(COMPOSE_CMD) run --rm claims-service sh -c "python manage.py migrate --database=default --noinput"

.PHONY: recreate
recreate: down .env.local build external-net up migrate ## Recreate containers while preserving database data

.PHONY: logs
logs: ## Show all containers logs
	$(COMPOSE_CMD) logs -f
