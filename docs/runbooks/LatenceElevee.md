# LatenceElevee

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `warning` | équipe | `make panne-latence` |

## Ce que signifie l'alerte

Le 95ᵉ centile du temps de réponse des requêtes métier dépasse 500 ms depuis 5 minutes.

## Impact

Le service fonctionne mais il est lent. Le SLO de latence (95 % des requêtes en moins de 300 ms) est menacé.

## Diagnostic

**1. Latence par route (PromQL)**

```promql
histogram_quantile(0.95, sum by (le, route) (rate(http_request_duration_seconds_bucket{service="api-commandes"}[5m])))
```

Toutes les routes sont-elles lentes, ou une seule ?

**2. Panne injectée ?**

```promql
chaos_actif{service="api-commandes", type="latence_ms"}
```

Une valeur non nulle signifie qu'une latence volontaire est ajoutée.

**3. Ressources de l'API**

Tableau de bord « Conteneurs (USE) »

CPU élevé ou mémoire proche de la limite ?

**4. Requêtes les plus lentes (LogQL)**

```logql
{service="api-commandes"} | json | duree_ms > 500
```

Quelles requêtes, à quel moment ?

## Résolution

1. Panne volontaire : `make retablir`.
2. Conteneur saturé : augmenter sa limite de CPU ou de mémoire, ou réduire la charge.
3. Base lente : vérifier le nombre de connexions (`pg_stat_database_numbackends`).

## Prévention

- Garder un test de charge (k6) dans le processus de validation, avec les seuils du SLO.

## À savoir

Alerte inhibée si `ApiIndisponible` est active pour le même service.

---

[← Toutes les procédures](README.md)
