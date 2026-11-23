# TauxErreursEleve

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `critical` | astreinte | `make panne-erreurs` |

## Ce que signifie l'alerte

Plus de 5 % des requêtes métier de l'API renvoient une erreur 5xx depuis 5 minutes (règle `sli:ratio_erreurs:rate5m`).

## Impact

Une partie des utilisateurs reçoit des erreurs. Le budget d'erreur du SLO de disponibilité (99,5 %) se consume vite.

## Diagnostic

**1. Taux d'erreurs par route et par code (PromQL)**

```promql
sum by (route, code) (rate(http_requests_total{service="api-commandes", code=~"5.."}[5m]))
```

Quelle route échoue ? Avec quel code ?

**2. Panne injectée ?**

```promql
chaos_actif{service="api-commandes"}
```

Une valeur non nulle pour `erreurs` signifie qu'une panne volontaire est en cours.

**3. Messages d'erreur (LogQL)**

```logql
{service="api-commandes", niveau="ERROR"} | json | line_format "{{.route}} {{.code}} {{.message}}"
```

Le message explique souvent la cause : base, délai, bug.

**4. La base répond-elle ?**

```promql
pg_up
```

Si 0, voir [PostgresIndisponible](PostgresIndisponible.md).

## Résolution

1. Panne volontaire : `make retablir`.
2. Base indisponible : voir [PostgresIndisponible](PostgresIndisponible.md).
3. Erreur introduite par un déploiement récent : revenir à la version précédente de l'image.
4. Suivre la baisse du taux d'erreurs sur le tableau de bord, puis vérifier le budget d'erreur restant.

## Prévention

- Tests automatisés avant chaque déploiement (CI).
- Déploiements progressifs, pour limiter le nombre d'utilisateurs touchés par une erreur.

## À savoir

Alerte inhibée si `ApiIndisponible` est active pour le même service.

---

[← Toutes les procédures](README.md)
