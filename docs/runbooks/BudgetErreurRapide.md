# BudgetErreurRapide

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `critical` | astreinte | `make panne-erreurs` |

## Ce que signifie l'alerte

Sur 1 heure **et** sur 5 minutes, le taux d'erreurs dépasse 14 fois le taux autorisé par le SLO (0,5 %). À ce rythme, le budget d'erreur de 7 jours serait épuisé en moins de 12 heures.

## Impact

L'objectif de disponibilité de la période est en danger. Si rien ne change, il sera manqué.

## Diagnostic

**1. Vitesse de consommation (PromQL)**

```promql
sli:ratio_erreurs:rate5m / (1 - 0.995)
sli:ratio_erreurs:rate1h / (1 - 0.995)
```

Au-dessus de 14 : consommation critique. Le graphique est dans la rangée SLO du tableau de bord de l'API.

**2. Budget restant**

```promql
slo:budget_disponibilite_restant:ratio_7d
```

1 = intact, 0 = épuisé, négatif = objectif manqué.

**3. Cause des erreurs**

Voir le diagnostic de [TauxErreursEleve](TauxErreursEleve.md).

## Résolution

1. Traiter la cause des erreurs (voir [TauxErreursEleve](TauxErreursEleve.md)).
2. Si le budget est épuisé : geler les déploiements de nouvelles fonctionnalités et prioriser la fiabilité.

## Prévention

- Revoir chaque incident qui consomme une part importante du budget (analyse post-incident).

## À savoir

Les deux fenêtres évitent deux pièges : la fenêtre de 1 h ignore un pic isolé, celle de 5 min permet à l'alerte de se résoudre vite une fois le problème corrigé. Alerte inhibée si `ApiIndisponible` est active.

---

[← Toutes les procédures](README.md)
