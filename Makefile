# Raccourcis du labo. « make » ou « make help » liste les commandes.
.DEFAULT_GOAL := help
COMPOSE := docker compose
API := http://localhost:8000

.PHONY: help env up down restart ps logs build test-app clean up-debug down-debug ps-debug recreate \
        charge charge-courte panne-erreurs panne-latence panne-api panne-db panne-memoire \
        panne-redemarrages retablir

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

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

# --------------------------------------------------------------------------
# Charge et pannes volontaires (EF-23, EF-24)
# Chaque panne déclenche une ou plusieurs alertes ; « make retablir » y met fin.
# --------------------------------------------------------------------------

charge: ## Lance le scénario de charge k6 (10 min)
	-$(COMPOSE) --profile charge run --rm k6

charge-courte: ## Lance le scénario de charge k6 (2 min)
	-$(COMPOSE) --profile charge run --rm -e MONTEE=30s -e PALIER=1m -e DESCENTE=30s k6

panne-erreurs: ## 30 % d'erreurs 500 + charge → TauxErreursEleve, BudgetErreurRapide, ErreursApplicatives
	curl -fsS -X POST "$(API)/chaos/erreurs?taux=0.3"; echo
	$(MAKE) --no-print-directory charge

panne-latence: ## 800 ms de latence + charge → LatenceElevee
	curl -fsS -X POST "$(API)/chaos/latence?ms=800"; echo
	$(MAKE) --no-print-directory charge

panne-api: ## Arrête l'API → ApiIndisponible, CibleInjoignable
	$(COMPOSE) stop api-commandes

panne-db: ## Arrête PostgreSQL → PostgresIndisponible (et ApiIndisponible)
	$(COMPOSE) stop postgres

panne-memoire: ## Mémoire de l'API à ~93 % de sa limite → MemoireConteneurProcheLimite
	curl -fsS -X POST "$(API)/chaos/memoire?mo_par_seconde=5&max_mo=75"; echo

panne-redemarrages: ## 3 fuites mémoire, 3 arrêts par Docker (OOM) → ConteneurRedemarre
	@for i in 1 2 3; do \
	  echo "Fuite n°$$i : l'API va dépasser sa limite et être tuée par Docker"; \
	  curl -fsS -X POST "$(API)/chaos/memoire?mo_par_seconde=20" > /dev/null || true; \
	  sleep 45; \
	done

retablir: ## Arrête toutes les pannes et relance les services arrêtés
	-curl -fsS -X POST "$(API)/chaos/reset"; echo
	$(COMPOSE) start postgres api-commandes
	$(COMPOSE) restart api-commandes
