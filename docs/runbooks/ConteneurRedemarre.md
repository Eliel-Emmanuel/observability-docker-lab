# ConteneurRedemarre

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `warning` | équipe | `make panne-redemarrages` |

## Ce que signifie l'alerte

Un conteneur du labo a démarré plus de 2 fois en 15 minutes : il plante et Docker le relance en boucle.

## Impact

Le service est instable : il est indisponible pendant chaque redémarrage, et peut perdre les requêtes en cours.

## Diagnostic

**1. Pourquoi s'arrête-t-il ?**

```bash
docker inspect obslab-<service>-1 --format 'OOMKilled={{.State.OOMKilled}} ExitCode={{.State.ExitCode}} Restarts={{.RestartCount}}'
```

`OOMKilled=true` ou code 137 : dépassement de la limite de mémoire. Code 1 ou 2 : erreur du programme ou de sa configuration.

**2. Première erreur**

```bash
docker compose logs <service> --tail=50 | grep -m1 -iE 'panic|error|fatal'
```

Seule la première ligne d'erreur compte, le reste est souvent la trace technique.

**3. Mémoire avant l'arrêt**

Tableau de bord « Conteneurs (USE) », panneau « Mémoire / limite »

Une courbe qui monte jusqu'à 100 % puis repart de zéro signe un OOM.

## Résolution

1. Panne volontaire : `make retablir`.
2. Manque de mémoire : relever la limite dans `compose.yaml` en se fondant sur la consommation mesurée, puis `make recreate s=<service>`.
3. Erreur de configuration : corriger le fichier, valider (promtool, amtool, alloy fmt), puis recréer le conteneur.

## Prévention

- Fixer les limites de mémoire à partir des mesures de cAdvisor, avec une marge.
- Surveiller l'alerte [MemoireConteneurProcheLimite](MemoireConteneurProcheLimite.md), qui précède souvent celle-ci.

---

[← Toutes les procédures](README.md)
