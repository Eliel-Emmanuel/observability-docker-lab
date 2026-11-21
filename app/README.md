# api-commandes

API de démonstration supervisée par le labo **observability-docker-lab**. Elle n'est pas le cœur du projet : elle sert de cible réaliste pour les métriques, les journaux et les alertes.

## Points d'accès

| Méthode | Route | Rôle |
| --- | --- | --- |
| GET | `/` | Nom et version du service (utilisé par le `HEALTHCHECK` Docker) |
| GET | `/sante` | 200 si la base répond, 503 sinon (utilisé par blackbox-exporter) |
| GET | `/commandes?limite=50` | Dernières commandes |
| POST | `/commandes` | Crée une commande : `{"client": "ACME", "produit": "Clavier", "quantite": 2}` |
| GET | `/metrics` | Métriques Prometheus |

### Injection de pannes (seulement si `CHAOS_ENABLED=true`)

Désactivés, ces points renvoient 404.

| Méthode | Route | Effet |
| --- | --- | --- |
| GET | `/chaos` | État des pannes en cours |
| POST | `/chaos/erreurs?taux=0.3` | 30 % des requêtes métier renvoient 500 |
| POST | `/chaos/latence?ms=800` | 800 ms ajoutées à chaque requête métier |
| POST | `/chaos/memoire?mo_par_seconde=5` | L'API retient 5 Mo de plus chaque seconde, jusqu'à atteindre la limite du conteneur |
| POST | `/chaos/reset` | Arrête toutes les pannes |

Les pannes ne touchent jamais `/sante` ni `/metrics`. Après une fuite mémoire, Python ne rend pas toujours la mémoire au système : redémarrer le conteneur pour repartir de zéro.

## Variables d'environnement

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `DB_HOST` | `postgres` | Hôte PostgreSQL |
| `DB_PORT` | `5432` | Port PostgreSQL |
| `DB_NAME` | `commandes` | Base |
| `DB_USER` | `commandes` | Utilisateur |
| `DB_PASSWORD` | vide | Mot de passe, à fournir par `.env` |
| `CHAOS_ENABLED` | `false` | Active les points d'injection de pannes |
| `LOG_LEVEL` | `INFO` | Niveau de journalisation |
| `APP_VERSION` | `1.0.0` | Version exposée dans `app_info` |

La table `commandes` est créée automatiquement à la première requête. L'API démarre même si la base n'est pas encore prête : `/sante` renvoie 503 jusqu'à ce qu'elle réponde.

## Métriques exposées

| Métrique | Type | Étiquettes | Usage |
| --- | --- | --- | --- |
| `http_requests_total` | compteur | `methode`, `route`, `code` | Débit et taux d'erreurs (RED) |
| `http_request_duration_seconds` | histogramme | `methode`, `route` | Latence p50, p95, p99 (RED) |
| `http_requests_in_progress` | jauge | aucune | Requêtes en cours |
| `commandes_creees_total` | compteur | aucune | Indicateur métier |
| `chaos_actif` | jauge | `type` | Panne injectée en cours, utile pour les annotations Grafana |
| `app_info` | info | `service`, `version` | Version déployée |

L'étiquette `route` contient le modèle de la route (`/commandes`), jamais le chemin brut ; une route inconnue devient `inconnue`. La cardinalité reste donc faible. `/metrics` n'est pas compté.

Pour les SLO, filtrer les routes techniques : `route!~"/sante|/chaos.*"`.

## Journaux

Une ligne JSON par événement sur la sortie standard, y compris les messages d'uvicorn et du pool de connexions :

```json
{"horodatage": "2026-11-20T15:27:54.810+00:00", "niveau": "INFO", "service": "api-commandes", "message": "POST /commandes 201", "id_requete": "59c1757bba7b4a06", "methode": "POST", "route": "/commandes", "chemin": "/commandes", "code": 201, "duree_ms": 5.8}
```

Niveau `ERROR` pour les réponses 5xx, `WARNING` pour les 4xx et les pannes injectées, `INFO` sinon. L'en-tête `x-request-id` est repris s'il est fourni, sinon généré, et renvoyé dans la réponse.

## Image Docker

- Construction en deux étapes, image `python:3.13-slim`
- Utilisateur non root (UID 10001), aucun fichier écrit à l'exécution : compatible avec `read_only: true`
- `HEALTHCHECK` intégré sur `/`

## Développement et tests

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest
```

Les tests n'ont pas besoin de base de données : ses accès sont simulés.
