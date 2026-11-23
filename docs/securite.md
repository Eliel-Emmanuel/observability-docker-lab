# Sécurité du labo

Cette page recense les mesures de sécurité appliquées (ES-01 à ES-07), et surtout les **exceptions** : les endroits où un service a reçu plus de droits que les autres, pourquoi, et comment on compenserait en production.

## Mesures appliquées à tous les services

| Mesure | Effet | Où |
| --- | --- | --- |
| Aucun secret dans le dépôt | Les mots de passe sont dans `.env`, ignoré par Git. Seul `.env.example`, sans vraie valeur, est versionné | `.gitignore`, job CI `secrets` (gitleaks sur tout l'historique) |
| Ports publiés sur `127.0.0.1` uniquement | Rien n'est joignable depuis le réseau local | `compose.yaml` : seuls Grafana, l'API et Mailpit sont publiés |
| Services internes non publiés | Prometheus, Loki, Alertmanager et les exporteurs ne sont joignables que par les réseaux Docker. Leurs ports n'existent qu'en mode débogage | `compose.debug.yaml` |
| Deux réseaux séparés | `app` (API, base) et `monitoring` (supervision). La base n'est pas joignable par les outils de supervision, sauf son exporteur | `compose.yaml` |
| Conteneurs durcis | `read_only`, `cap_drop: [ALL]`, `no-new-privileges`, utilisateur non root quand l'image le permet | `compose.yaml` |
| Limites de mémoire | Un service qui s'emballe ne peut pas priver les autres | `deploy.resources.limits` |
| Versions épinglées | Aucune image en `latest`, actions GitHub épinglées par empreinte de commit (SHA) | `.env`, `.github/workflows/ci.yml` |
| Analyse de l'image de l'API | La CI échoue si l'image contient une vulnérabilité critique corrigeable | Job CI `trivy` |
| Compte de supervision dédié | postgres-exporter se connecte avec un compte en lecture des statistiques seulement (`pg_monitor`), sans accès aux données | `postgres/init/01-supervision.sh` |
| Points d'injection de pannes désactivés par défaut | Les routes `/chaos` renvoient 404 si `CHAOS_ENABLED` n'est pas à `true` | Application |

## Exceptions documentées

Trois services ont besoin d'accès étendus pour faire leur travail. Ce sont les points à surveiller en priorité.

### 1. cAdvisor : `privileged: true`

**Pourquoi :** cAdvisor lit les statistiques de **tous** les conteneurs dans les cgroups et le noyau de l'hôte (`/sys`, `/dev/kmsg`, `/var/lib/docker`).

**Risque :** un conteneur privilégié a presque tous les droits sur la machine. Si cAdvisor était compromis, l'attaquant contrôlerait l'hôte.

**Compensation dans le labo :** image officielle épinglée, aucun port publié, réseau `monitoring` uniquement, tous les montages en lecture seule.

**En production :** sur Kubernetes, les métriques des conteneurs sont fournies par le kubelet, qui intègre cAdvisor : on n'a plus de conteneur privilégié à déployer.

### 2. node-exporter : `pid: host`

**Pourquoi :** node-exporter mesure la machine entière (CPU, mémoire, disques). Il doit voir les processus de l'hôte, pas seulement les siens.

**Risque :** le conteneur voit la liste de tous les processus de la machine, et leurs arguments, qui contiennent parfois des informations sensibles.

**Compensation :** `read_only`, aucun privilège Linux (`cap_drop: [ALL]`), `/sys` et `/` montés en lecture seule, aucun port publié.

**En production :** node-exporter tourne souvent directement sur le serveur, comme service système, plutôt qu'en conteneur.

### 3. Alloy et cAdvisor : le socket Docker

**Pourquoi :** Alloy découvre les conteneurs et lit leurs journaux par l'API Docker. cAdvisor l'utilise pour nommer les conteneurs.

**Risque :** le socket Docker est la porte d'entrée de Docker. Le montage en `:ro` empêche de modifier le **fichier**, pas d'envoyer des **commandes** : qui peut parler au socket peut créer un conteneur privilégié, donc prendre le contrôle de l'hôte. C'est l'équivalent d'un accès administrateur.

**Compensation :** images officielles épinglées, aucun port publié, réseau `monitoring` uniquement.

**En production :** passer par un proxy du socket qui n'autorise que les appels en lecture nécessaires (par exemple `docker-socket-proxy`), ou utiliser un environnement où les journaux sont collectés autrement (fichiers de journaux, Kubernetes).

## Limites assumées du labo

| Limite | En production |
| --- | --- |
| Pas de TLS entre les services | TLS partout, certificats gérés automatiquement |
| Grafana protégé par un simple mot de passe | Authentification unique (SSO), rôles par équipe |
| Prometheus et Alertmanager sans authentification (non publiés) | Accès derrière un proxy authentifiant |
| Un seul hôte, pas de sauvegarde | Volumes sauvegardés, supervision séparée des systèmes supervisés |

## Leçon de la chaîne d'approvisionnement

En mars 2026, des identifiants volés ont permis de publier une version malveillante de Trivy et de **déplacer les étiquettes** de l'action GitHub `trivy-action` vers du code qui volait les secrets des pipelines. Les projets qui référençaient l'action par une étiquette (`@v0.34`) ont exécuté ce code ; ceux qui l'avaient épinglée par **empreinte de commit** n'ont pas été touchés.

C'est pourquoi la CI de ce labo épingle ses actions par SHA, et lance gitleaks et Trivy depuis des images à la version fixée plutôt que par des actions tierces.
