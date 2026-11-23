# Étape 8 — Charge, pannes volontaires et procédures

**Objectif :** générer un trafic réaliste, provoquer chaque panne à la demande et vérifier que la bonne alerte arrive, avec sa procédure.

**Exigences :** EF-22 à EF-24.

## Charge : k6

`charge/scenario.js` simule des clients : 80 % de lectures (`GET /commandes`), 20 % de créations (`POST /commandes`), en trois paliers (montée à 10 utilisateurs virtuels, palier à 20, descente). k6 tourne dans un conteneur du profil `charge`, sur le réseau `app` : il ne démarre pas avec `make up`.

Les seuils k6 reprennent les SLO vus du client : moins de 0,5 % d'échecs et p95 < 300 ms. Pendant une panne volontaire, ils échouent : c'est attendu.

```bash
make charge           # 10 minutes
make charge-courte    # 2 minutes (30 s, 1 min, 30 s)
```

Mesure de référence, sans panne (`make charge-courte`) : **1 363 requêtes, 0 % d'erreurs, p95 = 7,7 ms**.

## Pannes

| Commande | Ce qui se passe | Alertes attendues |
| --- | --- | --- |
| `make panne-erreurs` | 30 % de réponses 500, sous charge | ErreursApplicatives, BudgetErreurRapide, TauxErreursEleve |
| `make panne-latence` | 800 ms ajoutées à chaque requête métier, sous charge | LatenceElevee |
| `make panne-api` | Arrêt du conteneur de l'API | ApiIndisponible, CibleInjoignable ; TauxErreursEleve inhibée |
| `make panne-db` | Arrêt de PostgreSQL | PostgresIndisponible, ApiIndisponible (`/sante` vérifie la base), CibleInjoignable |
| `make panne-memoire` | Fuite plafonnée à 68 Mo (environ 87 % de la limite de 128 Mo) | MemoireConteneurProcheLimite |
| `make panne-redemarrages` | Trois fuites rapides qui dépassent la limite : le noyau tue l'API trois fois (OOM) | ConteneurRedemarre |
| `make retablir` | Fin des pannes, redémarrage de l'API et de la base | Mails `[RESOLVED]` |

La fuite de `panne-memoire` est plafonnée (`max_mo`) : sans plafond, l'API dépasse sa limite en quelques secondes et est tuée avant que l'alerte, qui attend 5 minutes au-dessus du seuil, puisse se déclencher. Le plafond et le seuil (85 %) ont été réglés à partir des mesures : voir [résultats](10-resultats.md#panne-mémoire--deux-corrections).

Les délais mesurés pour chaque panne sont dans [10-resultats.md](10-resultats.md).

## Procédures (runbooks)

Une page par alerte dans [`docs/runbooks/`](runbooks/README.md), toutes sur le même modèle :

1. gravité, destinataire, panne qui la provoque dans le labo ;
2. signification et impact pour les utilisateurs ;
3. diagnostic : requêtes PromQL et LogQL prêtes à copier, commandes Docker ;
4. résolution ;
5. prévention.

Le lien `runbook_url` de chaque mail ouvre directement la bonne page.
