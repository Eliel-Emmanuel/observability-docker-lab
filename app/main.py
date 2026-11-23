"""api-commandes : API de démonstration du labo observability-docker-lab.

Elle stocke des commandes dans PostgreSQL, expose des métriques Prometheus
(méthode RED), écrit des journaux JSON et propose des points d'injection
de pannes pour déclencher les alertes à la demande.
"""

import asyncio
import json
import logging
import os
import random
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field
from starlette.routing import Match

SERVICE = "api-commandes"
VERSION = os.getenv("APP_VERSION", "1.0.0")


def chaos_autorise() -> bool:
    """Lu à chaque appel : CHAOS_ENABLED=true active les points d'injection."""
    return os.getenv("CHAOS_ENABLED", "false").lower() == "true"


# Routes exclues de l'injection de pannes et, pour /metrics, des métriques.
ROUTES_TECHNIQUES = {"/metrics", "/sante"}


# --------------------------------------------------------------------------
# Journaux JSON (EF-03)
# --------------------------------------------------------------------------
class FormatJSON(logging.Formatter):
    CHAMPS = ("id_requete", "methode", "route", "chemin", "code", "duree_ms")

    def format(self, record: logging.LogRecord) -> str:
        entree = {
            "horodatage": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "niveau": record.levelname,
            "service": SERVICE,
            "message": record.getMessage(),
        }
        for champ in self.CHAMPS:
            if hasattr(record, champ):
                entree[champ] = getattr(record, champ)
        if record.exc_info:
            entree["exception"] = self.formatException(record.exc_info)
        return json.dumps(entree, ensure_ascii=False)


def configurer_journaux() -> logging.Logger:
    sortie = logging.StreamHandler(sys.stdout)
    sortie.setFormatter(FormatJSON())
    niveau = os.getenv("LOG_LEVEL", "INFO").upper()
    # Journaux de l'API, du pool de connexions et d'uvicorn : tous en JSON,
    # pour que Loki puisse tous les analyser de la même façon.
    for nom in (SERVICE, "psycopg.pool", "uvicorn", "uvicorn.error"):
        journal = logging.getLogger(nom)
        journal.handlers = [sortie]
        # Le pool de connexions écrit 3 lignes INFO par requête : on ne garde que ses alertes.
        journal.setLevel("WARNING" if nom == "psycopg.pool" else niveau)
        journal.propagate = False
    return logging.getLogger(SERVICE)


log = configurer_journaux()


# --------------------------------------------------------------------------
# Métriques Prometheus (EF-02)
# --------------------------------------------------------------------------
REQUETES = Counter(
    "http_requests_total",
    "Nombre de requêtes HTTP reçues",
    ["methode", "route", "code"],
)
DUREE = Histogram(
    "http_request_duration_seconds",
    "Durée de traitement des requêtes HTTP",
    ["methode", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 2, 5),
)
EN_COURS = Gauge("http_requests_in_progress", "Requêtes HTTP en cours de traitement")
COMMANDES_CREEES = Counter("commandes_creees_total", "Nombre de commandes créées")
CHAOS = Gauge("chaos_actif", "Panne injectée en cours (valeur du réglage)", ["type"])
INFO = Info("app", "Informations sur l'application")
INFO.info({"service": SERVICE, "version": VERSION})


# --------------------------------------------------------------------------
# Injection de pannes (EF-04)
# --------------------------------------------------------------------------
class EtatChaos:
    def __init__(self) -> None:
        self.taux_erreurs = 0.0
        self.latence_ms = 0
        self.fuite_mo_par_seconde = 0
        self.fuite_max_mo: int | None = None
        self._fuite: list[bytes] = []
        self._verrou = threading.Lock()
        self._arret_fuite = threading.Event()
        self._thread_fuite: threading.Thread | None = None

    def publier(self) -> None:
        CHAOS.labels("erreurs").set(self.taux_erreurs)
        CHAOS.labels("latence_ms").set(self.latence_ms)
        CHAOS.labels("memoire_mo_par_seconde").set(self.fuite_mo_par_seconde)

    def memoire_retenue_mo(self) -> int:
        with self._verrou:
            return sum(len(bloc) for bloc in self._fuite) // (1024 * 1024)

    def demarrer_fuite(self, mo_par_seconde: int, max_mo: int | None = None) -> None:
        """Retient mo_par_seconde Mo de plus chaque seconde.

        Sans max_mo, la fuite continue jusqu'à ce que Docker tue le conteneur.
        Avec max_mo, elle se stabilise à ce plafond : le conteneur reste
        durablement proche de sa limite, sans être tué.
        """
        self.arreter_fuite()
        self.fuite_mo_par_seconde = mo_par_seconde
        self.fuite_max_mo = max_mo
        self._arret_fuite.clear()

        def fuir() -> None:
            while not self._arret_fuite.wait(1):
                retenu = self.memoire_retenue_mo()
                if max_mo is not None and retenu + mo_par_seconde > max_mo:
                    continue  # plafond atteint : on garde la mémoire sans en ajouter
                with self._verrou:
                    self._fuite.append(os.urandom(mo_par_seconde * 1024 * 1024))
                log.warning("Fuite mémoire simulée : %s Mo retenus", retenu + mo_par_seconde)

        self._thread_fuite = threading.Thread(target=fuir, daemon=True)
        self._thread_fuite.start()

    def arreter_fuite(self) -> None:
        self._arret_fuite.set()
        if self._thread_fuite:
            self._thread_fuite.join(timeout=2)
        with self._verrou:
            self._fuite.clear()
        self.fuite_mo_par_seconde = 0
        self.fuite_max_mo = None

    def reinitialiser(self) -> None:
        self.taux_erreurs = 0.0
        self.latence_ms = 0
        self.arreter_fuite()
        self.publier()

    def resume(self) -> dict:
        return {
            "actif": chaos_autorise(),
            "taux_erreurs": self.taux_erreurs,
            "latence_ms": self.latence_ms,
            "fuite_mo_par_seconde": self.fuite_mo_par_seconde,
            "fuite_max_mo": self.fuite_max_mo,
            "memoire_retenue_mo": self.memoire_retenue_mo(),
        }


chaos = EtatChaos()
chaos.publier()


def verifier_chaos_autorise() -> None:
    # Points d'injection invisibles si le chaos est désactivé (ES-07).
    if not chaos_autorise():
        raise HTTPException(status_code=404, detail="Not Found")


# --------------------------------------------------------------------------
# Base de données
# --------------------------------------------------------------------------
def chaine_connexion() -> str:
    return (
        f"host={os.getenv('DB_HOST', 'postgres')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME', 'commandes')} "
        f"user={os.getenv('DB_USER', 'commandes')} "
        f"password={os.getenv('DB_PASSWORD', '')} "
        "connect_timeout=3"
    )


pool: ConnectionPool | None = None
_schema_pret = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS commandes (
    id         BIGSERIAL PRIMARY KEY,
    client     TEXT        NOT NULL,
    produit    TEXT        NOT NULL,
    quantite   INTEGER     NOT NULL CHECK (quantite > 0),
    cree_le    TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def connexion():
    if pool is None:
        raise RuntimeError("Pool de connexions non initialisé")
    return pool.connection(timeout=3)


def preparer_schema() -> None:
    global _schema_pret
    if _schema_pret:
        return
    with connexion() as conn:
        conn.execute(SCHEMA)
    _schema_pret = True
    log.info("Schéma de la base prêt")


def base_disponible() -> bool:
    try:
        with connexion() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def lister_commandes(limite: int) -> list[dict]:
    preparer_schema()
    with connexion() as conn:
        lignes = conn.execute(
            "SELECT id, client, produit, quantite, cree_le FROM commandes ORDER BY id DESC LIMIT %s",
            (limite,),
        ).fetchall()
    return [
        {
            "id": ligne[0],
            "client": ligne[1],
            "produit": ligne[2],
            "quantite": ligne[3],
            "cree_le": ligne[4].isoformat(),
        }
        for ligne in lignes
    ]


def creer_commande(client: str, produit: str, quantite: int) -> dict:
    preparer_schema()
    with connexion() as conn:
        ligne = conn.execute(
            "INSERT INTO commandes (client, produit, quantite) VALUES (%s, %s, %s) RETURNING id, cree_le",
            (client, produit, quantite),
        ).fetchone()
    return {
        "id": ligne[0],
        "client": client,
        "produit": produit,
        "quantite": quantite,
        "cree_le": ligne[1].isoformat(),
    }


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
@asynccontextmanager
async def cycle_de_vie(_: FastAPI):
    global pool
    pool = ConnectionPool(chaine_connexion(), min_size=1, max_size=5, open=False)
    pool.open(wait=False)  # l'API démarre même si la base n'est pas encore prête
    log.info("Démarrage de %s %s (chaos %s)", SERVICE, VERSION, "activé" if chaos_autorise() else "désactivé")
    yield
    chaos.arreter_fuite()
    pool.close()
    log.info("Arrêt de %s", SERVICE)


app = FastAPI(title=SERVICE, version=VERSION, lifespan=cycle_de_vie)


def modele_de_route(request: Request) -> str:
    # Étiquette « route » = modèle de la route, jamais le chemin brut,
    # pour garder une cardinalité faible.
    for route in app.router.routes:
        correspondance, _ = route.matches(request.scope)
        if correspondance == Match.FULL:
            return route.path
    return "inconnue"


@app.middleware("http")
async def observer(request: Request, call_next):
    route = modele_de_route(request)
    id_requete = request.headers.get("x-request-id", uuid.uuid4().hex[:16])
    debut = time.perf_counter()
    EN_COURS.inc()
    try:
        injectable = route not in ROUTES_TECHNIQUES and not route.startswith("/chaos")
        if injectable and chaos.latence_ms:
            await asyncio.sleep(chaos.latence_ms / 1000)
        if injectable and chaos.taux_erreurs and random.random() < chaos.taux_erreurs:
            reponse = JSONResponse({"detail": "Erreur simulée"}, status_code=500)
        else:
            try:
                reponse = await call_next(request)
            except Exception:
                log.exception("Erreur non gérée", extra={"id_requete": id_requete, "route": route})
                reponse = JSONResponse({"detail": "Erreur interne"}, status_code=500)
    finally:
        EN_COURS.dec()

    duree = time.perf_counter() - debut
    if route != "/metrics":
        REQUETES.labels(request.method, route, str(reponse.status_code)).inc()
        DUREE.labels(request.method, route).observe(duree)

    niveau = (
        logging.ERROR
        if reponse.status_code >= 500
        else (logging.WARNING if reponse.status_code >= 400 else logging.INFO)
    )
    # Pas de journal pour /metrics (Prometheus) ni / (healthcheck Docker) : ce serait du bruit.
    if route not in ("/metrics", "/"):
        log.log(
            niveau,
            "%s %s %s",
            request.method,
            request.url.path,
            reponse.status_code,
            extra={
                "id_requete": id_requete,
                "methode": request.method,
                "route": route,
                "chemin": request.url.path,
                "code": reponse.status_code,
                "duree_ms": round(duree * 1000, 1),
            },
        )
    reponse.headers["x-request-id"] = id_requete
    return reponse


class NouvelleCommande(BaseModel):
    client: str = Field(min_length=1, max_length=100)
    produit: str = Field(min_length=1, max_length=100)
    quantite: int = Field(ge=1, le=1000)


@app.get("/")
def accueil() -> dict:
    return {"service": SERVICE, "version": VERSION}


@app.get("/sante")
def sante(response: Response) -> dict:
    ok = base_disponible()
    if not ok:
        response.status_code = 503
    return {"statut": "ok" if ok else "degrade", "base": "ok" if ok else "injoignable"}


@app.get("/commandes")
def get_commandes(limite: int = Query(50, ge=1, le=500)) -> list[dict]:
    try:
        return lister_commandes(limite)
    except Exception as erreur:
        log.error("Lecture des commandes impossible : %s", erreur)
        raise HTTPException(status_code=503, detail="Base de données indisponible") from erreur


@app.post("/commandes", status_code=201)
def post_commande(commande: NouvelleCommande) -> dict:
    try:
        resultat = creer_commande(commande.client, commande.produit, commande.quantite)
    except Exception as erreur:
        log.error("Création de commande impossible : %s", erreur)
        raise HTTPException(status_code=503, detail="Base de données indisponible") from erreur
    COMMANDES_CREEES.inc()
    return resultat


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --------------------------------------------------------------------------
# Points d'injection de pannes (actifs seulement si CHAOS_ENABLED=true)
# --------------------------------------------------------------------------
@app.get("/chaos")
def chaos_etat() -> dict:
    verifier_chaos_autorise()
    return chaos.resume()


@app.post("/chaos/erreurs")
def chaos_erreurs(taux: float = Query(0.3, ge=0, le=1)) -> dict:
    verifier_chaos_autorise()
    chaos.taux_erreurs = taux
    chaos.publier()
    log.warning("Chaos : %s %% de réponses 500", round(taux * 100))
    return chaos.resume()


@app.post("/chaos/latence")
def chaos_latence(ms: int = Query(800, ge=0, le=10000)) -> dict:
    verifier_chaos_autorise()
    chaos.latence_ms = ms
    chaos.publier()
    log.warning("Chaos : %s ms de latence ajoutée", ms)
    return chaos.resume()


@app.post("/chaos/memoire")
def chaos_memoire(
    mo_par_seconde: int = Query(5, ge=1, le=50),
    max_mo: int | None = Query(None, ge=1, le=1000),
) -> dict:
    verifier_chaos_autorise()
    chaos.demarrer_fuite(mo_par_seconde, max_mo)
    chaos.publier()
    log.warning(
        "Chaos : fuite mémoire de %s Mo par seconde (plafond : %s Mo)", mo_par_seconde, max_mo or "aucun"
    )
    return chaos.resume()


@app.post("/chaos/reset")
def chaos_reset() -> dict:
    verifier_chaos_autorise()
    chaos.reinitialiser()
    log.info("Chaos : toutes les pannes sont arrêtées")
    return chaos.resume()
