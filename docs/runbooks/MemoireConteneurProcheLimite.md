# MemoireConteneurProcheLimite

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `warning` | équipe | `make panne-memoire` |

## Ce que signifie l'alerte

Un conteneur utilise plus de 85 % de sa limite de mémoire depuis 5 minutes.

## Impact

Aucun pour l'instant, mais au-delà de 100 % Docker tue le conteneur. C'est une alerte d'anticipation.

## Diagnostic

**1. Quels conteneurs ?**

```promql
container_memory_working_set_bytes{name=~"obslab.*"} / (container_spec_memory_limit_bytes{name=~"obslab.*"} > 0)
```

Tableau de bord « Conteneurs (USE) », panneau « Mémoire / limite ».

**2. Croissance ou plateau ?**

Même panneau, sur les 6 dernières heures

Une croissance continue suggère une fuite de mémoire ; un plateau, une limite trop basse.

**3. Panne injectée ?**

```promql
chaos_actif{type="memoire_mo_par_seconde"}
```

## Résolution

1. Panne volontaire : `make retablir` (qui redémarre l'API pour libérer la mémoire).
2. Limite trop basse : la relever dans `compose.yaml`, puis `make recreate s=<service>`.
3. Fuite de mémoire : redémarrer le service pour gagner du temps, puis corriger le code.

## Prévention

- Réviser les limites après chaque évolution importante, à partir des mesures.

## À savoir

C'est grâce à ce type de mesure que la limite de Grafana a été relevée de 256 à 384 Mo à l'étape 5.

Si le conteneur a droit au swap, le noyau y envoie l'excédent quand la limite approche : la mémoire mesurée (`working_set`) plafonne alors sous le seuil et l'alerte ne se déclenche pas, alors que le service ralentit. Vérifier `container_memory_swap` en plus du `working_set`. Dans le labo, l'API n'a pas de swap (`memswap_limit` égal à sa limite).

Le `working_set` ne compte pas toute la mémoire facturée au conteneur. Mesuré dans le labo, l'API est tuée vers 88 % de `working_set` : c'est pourquoi le seuil est à 85 %, et non à 90 %.

---

[← Toutes les procédures](README.md)
