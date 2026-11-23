# Étape 6 — Indicateurs et objectifs de service (SLI, SLO)

**Objectif :** mesurer la qualité du service vue par l'utilisateur et suivre le budget d'erreur.

**Exigences :** EF-08, EF-16.

## Objectifs

| SLO | Indicateur (SLI) | Objectif | Budget d'erreur |
| --- | --- | --- | --- |
| Disponibilité | Part des requêtes métier sans réponse 5xx | 99,5 % | 0,5 % des requêtes |
| Latence | Part des requêtes métier servies en moins de 300 ms | 95 % | 5 % des requêtes |

**Requêtes métier :** toutes les routes sauf `/`, `/sante` et `/chaos*`. La sonde et l'injection de pannes ne doivent pas fausser l'indicateur.

**Fenêtre :** 7 jours glissants dans le labo (c'est la rétention de Prometheus), 30 jours en production.

## Règles d'enregistrement (`prometheus/rules/slo.yml`)

Nommage `niveau:métrique:opération`.

| Règle | Calcul |
| --- | --- |
| `sli:requetes:rate5m`, `sli:erreurs:rate5m`, `sli:ratio_erreurs:rate5m` | Débit, erreurs et part d'erreurs sur 5 min |
| `sli:requetes:rate1h`, `sli:erreurs:rate1h`, `sli:ratio_erreurs:rate1h` | Mêmes calculs sur 1 h |
| `sli:disponibilite:ratio_7d` | `1 − erreurs / requêtes` sur 7 jours |
| `slo:budget_disponibilite_restant:ratio_7d` | `1 − (1 − dispo) / 0,005` : 1 = intact, 0 = épuisé, négatif = objectif manqué |
| `sli:latence_ok:ratio_7d` | Requêtes dans la tranche `le="0.3"` de l'histogramme / total |
| `slo:budget_latence_restant:ratio_7d` | `1 − (1 − latence_ok) / 0,05` |

`or vector(0)` sur les erreurs : sans aucune erreur, la série 5xx n'existe pas, et sans ce repli tout le calcul serait vide au lieu de valoir 0.

Les calculs sur 7 jours sont évalués toutes les 5 min (coûteux) ; ceux sur 5 min et 1 h toutes les 30 s.

## Vitesse de consommation du budget (burn rate)

Un burn rate de 1 consomme exactement le budget sur la fenêtre. L'alerte `BudgetErreurRapide` se déclenche à **14 fois** ce rythme (part d'erreurs supérieure à 14 × 0,5 % = 7 %), mesurée à la fois sur 5 min et sur 1 h :

- la fenêtre de 1 h évite d'alerter sur un pic de quelques secondes ;
- la fenêtre de 5 min fait cesser l'alerte vite quand la panne est corrigée.

À ce rythme, le budget de la fenêtre de 7 jours serait épuisé en 12 heures (celui d'une fenêtre de 30 jours en un peu plus de 2 jours).

## Tests

`prometheus/tests/slo-test.yml` vérifie les règles avec des séries simulées : par exemple 100 requêtes par minute dont 1 en erreur donnent une disponibilité de 99 % et un budget restant de −100 % ; si 97 % des requêtes passent sous 300 ms, l'indicateur de latence vaut 97 %. Un second cas vérifie que, sans aucune erreur, le ratio vaut 0 au lieu d'être vide.

```bash
docker run --rm -v "$PWD/prometheus:/p" --entrypoint promtool prom/prometheus:v3.13.5 test rules /p/tests/slo-test.yml
```

## À savoir

Dans le labo, les pannes provoquées font chuter la disponibilité sur 7 jours bien en dessous de 99,5 % : un budget fortement négatif est attendu après les tests, et revient à la normale quand les erreurs sortent de la fenêtre.
