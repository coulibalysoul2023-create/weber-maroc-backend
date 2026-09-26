# ============================================================
# routes_clients.py
# Routes liées aux clients inscrits sur le site :
# - POST  /api/clients             -> inscription d'un nouveau client
# - GET   /api/clients             -> liste tous les clients (admin)
# - GET   /api/clients/{id}        -> détail d'un client (admin)
# - PATCH /api/clients/{id}/points -> ajoute/retire des points de fidélité (admin)
#
# ⚠️ Le mot de passe est stocké en clair pour l'instant. Il
# faudra le hacher (ex: avec bcrypt/passlib) avant toute mise
# en production réelle.
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from database import obtenir_connexion

router = APIRouter(prefix="/api/clients", tags=["Clients"])


# --- Schéma des données envoyées par le formulaire d'inscription ---
class ClientEntree(BaseModel):
    nom: str
    email: EmailStr
    telephone: str
    mot_de_passe: str
    accepter_promotions: bool = True


# --- Schéma des données envoyées pour ajuster les points de fidélité ---
class AjustementPoints(BaseModel):
    # Nombre de points à AJOUTER (mettre un nombre négatif pour en retirer)
    points: int


def formater_client(ligne, inclure_email=True):
    """Transforme une ligne SQL en dictionnaire pour le frontend
    (on ne renvoie jamais le mot de passe, même haché)."""
    return {
        "id": ligne["id"],
        "nom": ligne["nom"],
        "email": ligne["email"],
        "telephone": ligne["telephone"],
        "accepterPromotions": bool(ligne["accepter_promotions"]),
        "pointsFidelite": ligne["points_fidelite"],
        "dateInscription": ligne["date_inscription"].isoformat(),
    }


@router.post("", status_code=201)
def inscrire_client(client: ClientEntree):
    """Inscrit un nouveau client, en refusant les doublons d'e-mail."""
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)

    # Vérifie qu'aucun compte n'existe déjà avec cet e-mail
    curseur.execute(
        "SELECT id FROM clients WHERE LOWER(email) = LOWER(%s)", (client.email,)
    )
    if curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(
            status_code=409, detail="Un compte existe déjà avec cette adresse e-mail."
        )

    curseur.execute(
        """
        INSERT INTO clients (nom, email, telephone, mot_de_passe, accepter_promotions)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (client.nom, client.email, client.telephone, client.mot_de_passe, client.accepter_promotions),
    )
    connexion.commit()
    nouveau_id = curseur.lastrowid

    curseur.execute("SELECT * FROM clients WHERE id = %s", (nouveau_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    return formater_client(ligne)


@router.get("")
def lister_clients():
    """Renvoie la liste de tous les clients inscrits (pour l'admin)."""
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute("SELECT * FROM clients ORDER BY date_inscription DESC")
    lignes = curseur.fetchall()
    curseur.close()
    connexion.close()
    return [formater_client(ligne) for ligne in lignes]


@router.get("/{client_id}")
def obtenir_client(client_id: int):
    """Renvoie le détail d'un client précis (pour l'admin)."""
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()

    if not ligne:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return formater_client(ligne)


@router.patch("/{client_id}/points")
def ajuster_points_fidelite(client_id: int, ajustement: AjustementPoints):
    """
    Ajoute (ou retire, si le nombre est négatif) des points de
    fidélité à un client. Utilisé manuellement par l'administrateur
    après une vente réelle (en magasin, par téléphone, etc.), en
    attendant un vrai système de commandes automatique.

    Les points ne peuvent jamais descendre en dessous de 0.
    """
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)

    curseur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
    client = curseur.fetchone()
    if not client:
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Client introuvable")

    nouveau_total = max(0, client["points_fidelite"] + ajustement.points)

    curseur.execute(
        "UPDATE clients SET points_fidelite = %s WHERE id = %s",
        (nouveau_total, client_id),
    )
    connexion.commit()

    curseur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
    ligne_mise_a_jour = curseur.fetchone()
    curseur.close()
    connexion.close()
    return formater_client(ligne_mise_a_jour)