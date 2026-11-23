#!/usr/bin/env bash
# Crée le compte de supervision de PostgreSQL, utilisé par postgres-exporter.
#
# Il reçoit le rôle pg_monitor : il peut lire les statistiques de la base,
# mais ni lire ni modifier les données (moindre privilège).
#
# Exécuté automatiquement par l'image postgres au premier démarrage, quand le
# volume de données est vide. Sur une base existante, le lancer une fois :
#   docker compose exec postgres bash /docker-entrypoint-initdb.d/01-supervision.sh
# Il peut être relancé sans risque : il met à jour le mot de passe s'il existe déjà.

set -euo pipefail

: "${DB_MONITORING_USER:?variable DB_MONITORING_USER manquante}"
: "${DB_MONITORING_PASSWORD:?variable DB_MONITORING_PASSWORD manquante}"

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set utilisateur="$DB_MONITORING_USER" \
  --set mot_de_passe="$DB_MONITORING_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN', :'utilisateur')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'utilisateur') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'utilisateur', :'mot_de_passe') \gexec
SELECT format('GRANT pg_monitor TO %I', :'utilisateur') \gexec
SQL

echo "Compte de supervision « $DB_MONITORING_USER » prêt (rôle pg_monitor)."
