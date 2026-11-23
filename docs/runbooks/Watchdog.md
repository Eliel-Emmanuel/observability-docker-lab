# Watchdog

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `none` | watchdog | Arrêter Alertmanager : `docker compose stop alertmanager`. |

## Ce que signifie l'alerte

Cette alerte est **toujours** active, par construction (`vector(1)`). Elle prouve que toute la chaîne fonctionne : Prometheus évalue les règles, Alertmanager route et envoie, Mailpit reçoit.

## Impact

Aucun tant qu'elle arrive. **Son absence est le problème** : la supervision elle-même est en panne, et plus aucune alerte ne partirait.

## Diagnostic

**1. Prometheus évalue-t-il les règles ?**

http://localhost:9090/alerts

`Watchdog` doit apparaître en `firing`.

**2. Prometheus joint-il Alertmanager ?**

```bash
docker compose exec prometheus wget -qO- http://localhost:9090/api/v1/alertmanagers
```

**3. Alertmanager l'a-t-il reçue ?**

http://localhost:9093

**4. Alertmanager envoie-t-il ?**

```bash
docker compose logs alertmanager --since=30m | grep -i notify
```

Une erreur SMTP signale que Mailpit est injoignable.

## Résolution

1. Relancer le maillon en panne (Prometheus, Alertmanager ou Mailpit), puis vérifier qu'un nouveau mail `Watchdog` arrive.

## Prévention

- En production, on confie la Watchdog à un service externe (par exemple un « dead man's switch » chez un fournisseur d'astreinte) qui alerte quand il **cesse** de la recevoir.

## À savoir

Elle répond à la question : « qui surveille la supervision ? ».

---

[← Toutes les procédures](README.md)
