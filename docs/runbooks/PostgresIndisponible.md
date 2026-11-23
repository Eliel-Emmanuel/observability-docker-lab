# PostgresIndisponible

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `critical` | astreinte | `make panne-db` |

## Ce que signifie l'alerte

postgres-exporter n'arrive plus à se connecter à la base depuis une minute (`pg_up == 0`).

## Impact

L'API ne peut plus lire ni écrire de commandes : ses requêtes métier échouent, et `/sante` renvoie 503 (ce qui déclenche aussi `ApiIndisponible`).

## Diagnostic

**1. État du conteneur**

```bash
make ps-debug
```

`postgres` est-il `Up (healthy)` ?

**2. Journaux de la base**

```bash
docker compose logs postgres --since=10m | tail -30
```

Cherche `FATAL`, `out of memory`, `no space left on device`.

**3. Mémoire du conteneur**

Tableau de bord « Conteneurs (USE) »

La base a-t-elle été tuée pour dépassement de sa limite ?

**4. Disque de l'hôte**

```promql
node_filesystem_avail_bytes{mountpoint="/"}
```

Un disque plein empêche la base d'écrire.

## Résolution

1. Conteneur arrêté : `docker compose start postgres`. L'API se reconnecte seule.
2. Disque plein : libérer de l'espace (voir [DisqueHotePresquePlein](DisqueHotePresquePlein.md)).
3. Vérifier ensuite que les données sont intactes : `curl localhost:8000/commandes`.

## Prévention

- Sauvegardes régulières du volume `donnees-postgres`.
- En production : réplication et basculement automatique (service managé ou Patroni).

---

[← Toutes les procédures](README.md)
