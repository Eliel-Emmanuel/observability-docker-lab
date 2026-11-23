#!/usr/bin/env bash
# Test de bout en bout du labo (ENF-05) : la pile doit être démarrée en mode
# débogage (make up-debug), qui publie les ports de Prometheus, Loki et Mailpit.
# Usage : bash tests/e2e.sh   (nécessite curl et jq)

set -euo pipefail

API=http://localhost:8000
PROMETHEUS=http://localhost:9090
LOKI=http://localhost:3100
MAILPIT=http://localhost:8025
CIBLES_ATTENDUES=10

echecs=0

# attendre "description" "commande" [délai maximal en secondes]
attendre() {
  local description=$1 commande=$2 limite=${3:-180} ecoule=0
  until eval "$commande" > /dev/null 2>&1; do
    if (( ecoule >= limite )); then
      echo "ÉCHEC  $description (après ${limite} s)"
      echecs=$((echecs + 1))
      return 0
    fi
    sleep 5
    ecoule=$((ecoule + 5))
  done
  echo "OK     $description"
}

cibles_up() {
  local json
  json=$(curl -fsS "$PROMETHEUS/api/v1/targets")
  [[ $(jq '[.data.activeTargets[] | select(.health == "up")] | length' <<< "$json") -ge $CIBLES_ATTENDUES ]]
}

echo "== Application"
attendre "l'API répond sur /sante" "curl -fsS $API/sante"
attendre "création d'une commande" \
  "curl -fsS -X POST $API/commandes -H 'content-type: application/json' -d '{\"client\":\"E2E\",\"produit\":\"Test\",\"quantite\":1}'"
attendre "lecture des commandes" "curl -fsS $API/commandes | jq -e 'length >= 1'"

echo "== Métriques"
attendre "les $CIBLES_ATTENDUES cibles Prometheus sont UP" cibles_up 240
attendre "les règles SLO et d'alerte sont chargées" \
  "curl -fsS $PROMETHEUS/api/v1/rules | jq -e '[.data.groups[].rules[]] | length >= 20'"
attendre "la sonde blackbox voit l'API" \
  "curl -fsS $PROMETHEUS/api/v1/query --data-urlencode 'query=probe_success{service=\"api-commandes\"}' | jq -e '.data.result[0].value[1] == \"1\"'"

echo "== Journaux"
attendre "les journaux de l'API arrivent dans Loki" \
  "curl -fsS -G $LOKI/loki/api/v1/query --data-urlencode 'query=sum(count_over_time({service=\"api-commandes\"}[15m]))' | jq -e '.data.result | length > 0'"

echo "== Alertes"
attendre "Prometheus est relié à Alertmanager" \
  "curl -fsS $PROMETHEUS/api/v1/alertmanagers | jq -e '.data.activeAlertmanagers | length >= 1'"
attendre "le mail Watchdog arrive dans Mailpit" \
  "curl -fsS '$MAILPIT/api/v1/search?query=subject%3AWatchdog' | jq -e '.messages_count >= 1'" 240

echo
if (( echecs > 0 )); then
  echo "$echecs vérification(s) en échec."
  exit 1
fi
echo "Toutes les vérifications ont réussi."
