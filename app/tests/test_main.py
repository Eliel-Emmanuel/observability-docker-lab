"""Tests de l'API, sans base de données : les accès à la base sont simulés."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def module(monkeypatch):
    monkeypatch.setenv("CHAOS_ENABLED", "true")
    commandes = []

    def creer(client, produit, quantite):
        commande = {
            "id": len(commandes) + 1,
            "client": client,
            "produit": produit,
            "quantite": quantite,
            "cree_le": datetime.now(UTC).isoformat(),
        }
        commandes.append(commande)
        return commande

    monkeypatch.setattr(main, "creer_commande", creer)
    monkeypatch.setattr(main, "lister_commandes", lambda limite: commandes[-limite:])
    monkeypatch.setattr(main, "base_disponible", lambda: True)
    yield main
    main.chaos.reinitialiser()


@pytest.fixture
def client(module):
    # Sans « with » : le cycle de vie (connexion à la base) n'est pas lancé.
    return TestClient(module.app)


def test_creer_puis_lister(client):
    reponse = client.post("/commandes", json={"client": "ACME", "produit": "Clavier", "quantite": 2})
    assert reponse.status_code == 201
    assert reponse.json()["id"] == 1
    assert client.get("/commandes").json()[0]["produit"] == "Clavier"


def test_validation_quantite(client):
    reponse = client.post("/commandes", json={"client": "ACME", "produit": "Clavier", "quantite": 0})
    assert reponse.status_code == 422


def test_sante_ok(client):
    reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json()["base"] == "ok"


def test_sante_base_injoignable(client, module, monkeypatch):
    monkeypatch.setattr(module, "base_disponible", lambda: False)
    assert client.get("/sante").status_code == 503


def test_base_indisponible_renvoie_503(client, module, monkeypatch):
    def echec(limite):
        raise ConnectionError("base arrêtée")

    monkeypatch.setattr(module, "lister_commandes", echec)
    assert client.get("/commandes").status_code == 503


def test_metriques_red(client):
    client.get("/commandes")
    texte = client.get("/metrics").text
    assert 'http_requests_total{code="200",methode="GET",route="/commandes"}' in texte
    assert "http_request_duration_seconds_bucket" in texte
    assert "commandes_creees_total" in texte


def test_route_sans_cardinalite_elevee(client):
    client.get("/existe-pas/123")
    texte = client.get("/metrics").text
    assert 'route="inconnue"' in texte
    assert "/existe-pas/123" not in texte


def test_identifiant_de_requete(client):
    reponse = client.get("/", headers={"x-request-id": "abc123"})
    assert reponse.headers["x-request-id"] == "abc123"


def test_chaos_erreurs(client):
    client.post("/chaos/erreurs", params={"taux": 1})
    assert client.get("/commandes").status_code == 500
    # Les routes techniques ne sont jamais touchées par les pannes.
    assert client.get("/sante").status_code == 200
    client.post("/chaos/reset")
    assert client.get("/commandes").status_code == 200


def test_chaos_latence(client):
    client.post("/chaos/latence", params={"ms": 300})
    reponse = client.get("/commandes")
    assert reponse.status_code == 200
    assert client.get("/chaos").json()["latence_ms"] == 300


def test_chaos_desactive_par_defaut(client, monkeypatch):
    monkeypatch.delenv("CHAOS_ENABLED", raising=False)
    assert client.post("/chaos/erreurs").status_code == 404
    assert client.get("/chaos").status_code == 404


def test_chaos_memoire_plafonnee(client, module):
    import time

    reponse = client.post("/chaos/memoire", params={"mo_par_seconde": 2, "max_mo": 4})
    assert reponse.json()["fuite_max_mo"] == 4
    time.sleep(3.5)
    assert module.chaos.memoire_retenue_mo() == 4
    client.post("/chaos/reset")
    assert module.chaos.memoire_retenue_mo() == 0
