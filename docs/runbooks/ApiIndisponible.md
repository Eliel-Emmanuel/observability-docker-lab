# ApiIndisponible

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `critical` | astreinte | `make panne-api` |

## Ce que signifie l'alerte

La sonde blackbox n'obtient plus de réponse 200 sur `http://api-commandes:8000/sante` depuis plus d'une minute.

## Impact

Les utilisateurs ne peuvent plus consulter ni créer de commandes. C'est une panne totale du service.

## Diagnostic

**1. État des conteneurs**

```bash
make ps-debug
```

`api-commandes` est-il `Up (healthy)` ? `Restarting` ? Absent ?

**2. Réponse de la sonde (PromQL)**

```promql
probe_success{service="api-commandes"}
probe_http_status_code{service="api-commandes"}
```

Un code 503 signifie que l'API tourne mais que sa base ne répond pas : voir [PostgresIndisponible](PostgresIndisponible.md).

**3. Journaux de l'API**

```bash
docker compose logs api-commandes --since=10m | tail -30
```

Cherche une erreur au démarrage ou un message `Lecture des commandes impossible`.

**4. Journaux dans Grafana (LogQL)**

```logql
{service="api-commandes", niveau=~"ERROR|WARNING"}
```

Tableau de bord « Service — api-commandes (RED) », panneau des journaux.

## Résolution

1. Conteneur arrêté : `docker compose start api-commandes`.
2. Conteneur en redémarrage permanent : voir [ConteneurRedemarre](ConteneurRedemarre.md).
3. Code 503 : la base est en cause, voir [PostgresIndisponible](PostgresIndisponible.md).
4. Après résolution, vérifier que `probe_success` revient à 1 et qu'un mail `[RESOLVED]` arrive.

## Prévention

- Garder `restart: unless-stopped` et le healthcheck Docker de l'API.
- En production : au moins deux instances de l'API derrière un répartiteur de charge.

## À savoir

Pendant cette alerte, `TauxErreursEleve`, `LatenceElevee` et `BudgetErreurRapide` sont **inhibées** : elles n'apporteraient aucune information supplémentaire.

---

[← Toutes les procédures](README.md)
