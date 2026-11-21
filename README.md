# observability-docker-lab

![CI](https://github.com/Eliel-Emmanuel/observability-docker-lab/actions/workflows/ci.yml/badge.svg)

Chaîne de supervision complète en Docker Compose — métriques (Prometheus), journaux (Loki, Grafana Alloy), tableaux de bord (Grafana) et alertes (Alertmanager) — autour d'une API de démonstration, avec des pannes provoquées à la demande pour prouver chaque alerte.

> 🚧 En cours de construction. Avancement : étape 1 sur 10.

## Objectifs

- Détecter un incident avant les utilisateurs, et en trouver la cause en quelques minutes
- Tout décrire en code : services, tableaux de bord, alertes, tests
- Tenir dans moins de 2 Go de RAM

## Démarrage rapide

```bash
make env   # crée .env, puis modifier les mots de passe
make up    # démarre la pile
```

## Documentation

- [Cahier des charges](docs/00-cahier-des-charges.md)
- [Application de démonstration](app/README.md)

## Licence

MIT
