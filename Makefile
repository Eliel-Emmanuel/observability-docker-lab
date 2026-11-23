# Raccourcis du labo. « make » ou « make help » liste les commandes.
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help env up down restart ps logs build test-app clean up-debug down-debug ps-debug recreate

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Crée .env à partir de .env.example s'il n'existe pas
	@test -f .env && echo ".env existe déjà" || (cp .env.example .env && echo ".env créé : change les mots de passe")

up: ## Démarre la pile en arrière-plan
	$(COMPOSE) up -d --build

down: ## Arrête la pile (les données sont conservées)
	$(COMPOSE) down

restart: down up ## Redémarre la pile

ps: ## État des services
	$(COMPOSE) ps

logs: ## Suit les journaux de tous les services
	$(COMPOSE) logs -f --tail=50

build: ## Construit l'image de l'application
	docker build -t api-commandes:local app/

test-app: ## Lance le lint et les tests de l'application dans un conteneur
	docker run --rm -v "$(PWD)/app:/app" -w /app -e PYTHONDONTWRITEBYTECODE=1 python:3.13-slim \
	  sh -c "pip install -q --root-user-action=ignore --disable-pip-version-check -r requirements-dev.txt \
	  && ruff check --no-cache . && ruff format --no-cache --check . && pytest -q -p no:cacheprovider"

clean: ## Arrête la pile et SUPPRIME les volumes (données perdues)
	$(COMPOSE) down -v

up-debug: ## Démarre la pile avec les ports de débogage
	$(COMPOSE) -f compose.yaml -f compose.debug.yaml up -d --build

down-debug: ## Arrête la pile démarrée en mode débogage
	$(COMPOSE) -f compose.yaml -f compose.debug.yaml down

ps-debug: ## État des services (mode débogage)
	$(COMPOSE) -f compose.yaml -f compose.debug.yaml ps

recreate: ## Recrée un service en mode débogage (make recreate s=prometheus)
	$(COMPOSE) -f compose.yaml -f compose.debug.yaml up -d $(s)
