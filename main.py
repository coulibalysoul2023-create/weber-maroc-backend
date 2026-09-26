# ============================================================
# main.py
# Point d'entrée du serveur FastAPI. Démarre l'application,
# active CORS (pour que React puisse appeler cette API depuis
# un autre port), et regroupe toutes les routes.
#
# Pour lancer le serveur :
#   uvicorn main:app --reload
# ============================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import tester_connexion
import routes_produits
import routes_clients
import routes_admin
import routes_videos
import routes_commentaires
import routes_avis
import routes_categories

app = FastAPI(title="API Weber Maroc")

# Autorise le frontend React (qui tourne sur localhost:3000) à
# appeler cette API. Sans ça, le navigateur bloque les requêtes
# entre deux origines différentes (politique de sécurité CORS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
           "https://weber-maroc-frontend.vercel.app",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Branche toutes les routes /api/produits/...
app.include_router(routes_produits.router)

# Branche toutes les routes /api/clients/...
app.include_router(routes_clients.router)

# Branche toutes les routes /api/admin/...
app.include_router(routes_admin.router)

# Branche toutes les routes /api/videos/...
app.include_router(routes_videos.router)

# Branche les routes commentaires produits (client + admin)
app.include_router(routes_commentaires.router)
app.include_router(routes_commentaires.router_admin)

# Branche les routes avis du site (client + admin)
app.include_router(routes_avis.router)
app.include_router(routes_avis.router_admin)

# Branche toutes les routes /api/categories/...
app.include_router(routes_categories.router)


@app.get("/")
def accueil():
    """Route de base, pour vérifier que le serveur répond."""
    return {"message": "API Weber Maroc opérationnelle"}


@app.get("/api/sante")
def verifier_sante():
    """
    Route de diagnostic : vérifie que le serveur ET la base de
    données fonctionnent bien ensemble.
    """
    try:
        nb_produits = tester_connexion()
        return {
            "statut": "ok",
            "base_de_donnees": "connectée",
            "nombre_produits": nb_produits,
        }
    except Exception as erreur:
        return {"statut": "erreur", "detail": str(erreur)}