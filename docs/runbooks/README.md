# Procédures de résolution (runbooks)

Chaque alerte du labo renvoie, par son lien `runbook_url`, vers l'une de ces pages. Elles suivent toutes le même plan : signification, impact, diagnostic, résolution, prévention.

| Alerte | Gravité | Source | Panne de démonstration |
| --- | --- | --- | --- |
| [ApiIndisponible](ApiIndisponible.md) | `critical` | Prometheus | `make panne-api` |
| [TauxErreursEleve](TauxErreursEleve.md) | `critical` | Prometheus | `make panne-erreurs` |
| [LatenceElevee](LatenceElevee.md) | `warning` | Prometheus | `make panne-latence` |
| [BudgetErreurRapide](BudgetErreurRapide.md) | `critical` | Prometheus | `make panne-erreurs` |
| [CibleInjoignable](CibleInjoignable.md) | `warning` | Prometheus | `make panne-api` |
| [PostgresIndisponible](PostgresIndisponible.md) | `critical` | Prometheus | `make panne-db` |
| [ConteneurRedemarre](ConteneurRedemarre.md) | `warning` | Prometheus | `make panne-redemarrages` |
| [MemoireConteneurProcheLimite](MemoireConteneurProcheLimite.md) | `warning` | Prometheus | `make panne-memoire` |
| [DisqueHotePresquePlein](DisqueHotePresquePlein.md) | `warning` | Prometheus | Pas de panne automatique : risquée pour le poste de travail. |
| [ErreursApplicatives](ErreursApplicatives.md) | `warning` | Loki | `make panne-erreurs` |
| [Watchdog](Watchdog.md) | `none` | Prometheus | Arrêter Alertmanager : `docker compose stop alertmanager`. |

Pour mettre fin à toutes les pannes : `make retablir`.
