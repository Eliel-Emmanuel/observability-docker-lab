# ErreursApplicatives

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `warning` | équipe | `make panne-erreurs` |

## Ce que signifie l'alerte

Plus de 20 lignes de journal de niveau `ERROR` en 5 minutes pour un même service. Alerte évaluée par le ruler de **Loki**, à partir des journaux.

## Impact

Variable. Elle peut révéler un problème avant qu'il ne produise des erreurs visibles par les utilisateurs (connexion à la base qui échoue, tâche de fond en erreur).

## Diagnostic

**1. Les erreurs (LogQL)**

```logql
{service="api-commandes", niveau="ERROR"} | json
```

Lire les messages : ils donnent la cause.

**2. Erreurs les plus fréquentes**

```logql
topk(5, sum by (message) (count_over_time({service="api-commandes", niveau="ERROR"} | json [15m])))
```

Une seule erreur répétée, ou plusieurs problèmes ?

**3. Lien avec les métriques**

Tableau de bord de l'API : taux d'erreurs 5xx et base de données

## Résolution

1. Panne volontaire : `make retablir`.
2. Base indisponible : voir [PostgresIndisponible](PostgresIndisponible.md).
3. Autre message : le corriger à la source, dans le code ou la configuration.

## Prévention

- Journaliser les erreurs avec un message explicite et le contexte (route, identifiant de requête).

## À savoir

Cette alerte complète les métriques : elle repose sur le contenu des journaux, collectés par Alloy.

---

[← Toutes les procédures](README.md)
