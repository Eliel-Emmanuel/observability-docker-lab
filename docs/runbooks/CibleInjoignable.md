# CibleInjoignable

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `warning` | équipe | `make panne-api` |

## Ce que signifie l'alerte

Prometheus n'arrive plus à collecter les métriques d'une cible depuis 2 minutes (`up == 0`).

## Impact

On perd la visibilité sur ce service : ses tableaux de bord se vident et ses alertes ne peuvent plus se déclencher.

## Diagnostic

**1. Quelles cibles ?**

```promql
up == 0
```

Le label `job` indique le service.

**2. Erreur exacte**

Page Status → Target health de Prometheus (http://localhost:9090/targets)

`no such host` : conteneur arrêté. `connection refused` : port fermé. `timeout` : service saturé.

**3. État du conteneur**

```bash
make ps-debug
```

## Résolution

1. Conteneur arrêté : `docker compose start <service>`.
2. Conteneur en redémarrage : lire `docker compose logs <service> --tail=30`.
3. Erreur de configuration : `promtool check config`, puis recharger Prometheus (`docker compose kill -s SIGHUP prometheus`).

## Prévention

- Valider la configuration de Prometheus en CI (`promtool`).

---

[← Toutes les procédures](README.md)
