// Scénario de charge k6 pour api-commandes (EF-23).
// Trafic réaliste : 80 % de lectures, 20 % de créations de commandes.
//
// Lancement : make charge          (10 minutes)
//             make charge-courte   (2 minutes)
// Les durées des paliers se règlent par variables d'environnement.

import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://api-commandes:8000";

const CLIENTS = ["ACME", "Globex", "Initech", "Umbrella", "Hooli", "Stark"];
const PRODUITS = ["Clavier", "Souris", "Écran", "Casque", "Webcam", "Dock USB-C"];

export const options = {
  scenarios: {
    trafic: {
      executor: "ramping-vus",
      startVUs: 2,
      stages: [
        { duration: __ENV.MONTEE || "1m", target: 10 },   // montée en charge
        { duration: __ENV.PALIER || "8m", target: 20 },   // trafic soutenu
        { duration: __ENV.DESCENTE || "1m", target: 0 },  // retour au calme
      ],
      gracefulRampDown: "10s",
    },
  },
  // Les objectifs de service, vus côté client. Pendant une panne volontaire,
  // ils échouent : c'est attendu, et k6 le signale en fin de test.
  thresholds: {
    http_req_failed: ["rate<0.005"],     // SLO de disponibilité : 99,5 %
    http_req_duration: ["p(95)<300"],    // SLO de latence : p95 < 300 ms
  },
};

function auHasard(liste) {
  return liste[Math.floor(Math.random() * liste.length)];
}

export default function () {
  if (Math.random() < 0.8) {
    const reponse = http.get(`${BASE_URL}/commandes?limite=20`, {
      tags: { operation: "lecture" },
    });
    check(reponse, { "lecture : 200": (r) => r.status === 200 });
  } else {
    const commande = {
      client: auHasard(CLIENTS),
      produit: auHasard(PRODUITS),
      quantite: 1 + Math.floor(Math.random() * 5),
    };
    const reponse = http.post(`${BASE_URL}/commandes`, JSON.stringify(commande), {
      headers: { "Content-Type": "application/json" },
      tags: { operation: "creation" },
    });
    check(reponse, { "création : 201": (r) => r.status === 201 });
  }
  // Temps de réflexion d'un utilisateur : entre 0,5 et 1,5 seconde.
  sleep(0.5 + Math.random());
}
