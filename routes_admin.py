# ============================================================
# routes_admin.py
# Route de connexion pour l'espace administrateur :
# - POST /api/admin/connexion -> vérifie l'e-mail + mot de passe
#
# ⚠️ Le mot de passe est comparé en clair pour l'instant (comme
# dans la table administrateurs). Il faudra le hacher (bcrypt/
# passlib) avant toute mise en production réelle, et remplacer
# la réponse simple par un vrai jeton d'authentification (JWT).
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from database import obtenir_connexion

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class ConnexionEntree(BaseModel):
    email: EmailStr
    mot_de_passe: str


@router.post("/connexion")
def connecter_admin(donnees: ConnexionEntree):
    """Vérifie les identifiants d'un administrateur."""
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute(
        "SELECT id, nom, email, mot_de_passe FROM administrateurs WHERE LOWER(email) = LOWER(%s)",
        (donnees.email,),
    )
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()

    # Message volontairement identique dans les deux cas (email
    # inconnu ou mot de passe faux) pour ne pas indiquer à un
    # attaquant si l'e-mail existe ou non dans la base
    identifiants_invalides = HTTPException(
        status_code=401, detail="E-mail ou mot de passe incorrect."
    )

    if not ligne:
        raise identifiants_invalides

    if ligne["mot_de_passe"] != donnees.mot_de_passe:
        raise identifiants_invalides

    return {
        "id": ligne["id"],
        "nom": ligne["nom"],
        "email": ligne["email"],
    }