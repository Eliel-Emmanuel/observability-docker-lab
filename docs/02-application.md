# Étape 2 — Application et base de données

**Objectif :** construire l'API de démonstration, la brancher sur PostgreSQL dans Compose et vérifier qu'elle est prête à être supervisée.

**Exigences :** EF-01 à EF-05.

## Ce qui est en place

- `app/` contient l'API `api-commandes` (FastAPI, `psycopg_pool`, `prometheus_client`), ses 12 tests pytest et son Dockerfile multi-étapes (utilisateur non root, `HEALTHCHECK`). Détail des routes : [app/README.md](../app/README.md).
- L'API expose les métriques RED (`http_requests_total`, `http_request_duration_seconds`, `http_requests_in_progress`), une métrique métier (`commandes_creees_total`), l'état des pannes injectées (`chaos_actif`) et `app_info`.
- Les journaux sont écrits en JSON sur la sortie standard : `horodatage`, `niveau`, `service`, `message`, `id_requete`, `methode`, `route`, `chemin`, `code`, `duree_ms`. Les routes `/` et `/metrics` ne sont pas journalisées pour ne pas noyer les journaux utiles.
- PostgreSQL 17 tourne avec un volume nommé (`donnees-postgres`) ; l'API attend qu'il soit `healthy` avant de démarrer (`depends_on: condition: service_healthy`).

## Commandes

```bash
make env          # crée .env, puis changer les mots de passe
make build        # construit l'image de l'API
make test-app     # ruff + 12 tests pytest, dans un conteneur jetable
make up
curl -s localhost:8000/sante
curl -s -X POST localhost:8000/commandes -H 'Content-Type: application/json' \
     -d '{"client":"ACME","produit":"Clavier","quantite":2}'
curl -s localhost:8000/metrics | grep http_requests_total
```

## Résultat attendu

- `make test-app` : `12 passed`.
- `/sante` renvoie `200` ; il renvoie `503` si la base est arrêtée.
- `/metrics` contient `http_requests_total{code="201",methode="POST",route="/commandes"}`.

## Points d'injection de pannes

| Route | Effet | Utilisée par |
| --- | --- | --- |
| `POST /chaos/erreurs?taux=0.3` | 30 % de réponses 500 | `make panne-erreurs` |
| `POST /chaos/latence?ms=800` | 800 ms ajoutées | `make panne-latence` |
| `POST /chaos/memoire?mo_par_seconde=2&max_mo=68` | Fuite mémoire plafonnée | `make panne-memoire` |
| `POST /chaos/reset` | Fin des pannes | `make retablir` |

Les pannes ne touchent jamais `/sante` ni `/metrics`, pour que la supervision reste fiable pendant un test. Elles ne répondent que si `CHAOS_ENABLED=true` (désactivé par défaut dans l'application, activé dans `.env.example` parce que c'est un labo).
