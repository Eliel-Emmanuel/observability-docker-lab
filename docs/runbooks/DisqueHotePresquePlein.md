# DisqueHotePresquePlein

| Gravité | Destinataire | Panne de démonstration |
| --- | --- | --- |
| `warning` | équipe | Pas de panne automatique : risquée pour le poste de travail. |

## Ce que signifie l'alerte

Il reste moins de 15 % d'espace libre sur le disque principal de l'hôte depuis 10 minutes.

## Impact

Aucun immédiat. Un disque plein bloquerait PostgreSQL, Prometheus et Loki, qui écrivent en continu.

## Diagnostic

**1. Espace libre (PromQL)**

```promql
node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}
```

**2. Ce qui occupe Docker**

```bash
docker system df
```

Images, conteneurs arrêtés, volumes, cache de construction.

**3. Taille des volumes**

```bash
docker system df -v | grep obslab
```

## Résolution

1. Supprimer les images et le cache inutilisés : `docker image prune -a` et `docker builder prune`.
2. Vérifier que les rétentions sont appliquées : 7 jours ou 2 Go pour Prometheus, 7 jours pour Loki.
3. Sous WSL2, la place libérée revient à Windows grâce à l'option `sparseVhd` du fichier `.wslconfig`.

## Prévention

- Toujours borner la rétention des données de supervision (EF-09, EF-12).

## À savoir

Sous Docker sur WSL2, « l'hôte » mesuré par node-exporter est la machine virtuelle WSL2, pas le disque de Windows.

---

[← Toutes les procédures](README.md)
