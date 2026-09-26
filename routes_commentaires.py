# ============================================================
# routes_commentaires.py
# Routes liées aux commentaires produits et aux likes :
#
# Côté client (public) :
#   GET  /api/produits/{produit_id}/commentaires  -> commentaires publics uniquement
#   POST /api/produits/{produit_id}/commentaires  -> ajoute un commentaire (en attente)
#   POST /api/produits/{produit_id}/like           -> ajoute un like au produit
#
# Côté admin (modération) :
#   GET    /api/admin/commentaires               -> tous les commentaires (public + attente)
#   PATCH  /api/admin/commentaires/{id}/publier   -> rend un commentaire public
#   DELETE /api/admin/commentaires/{id}           -> supprime un commentaire
#
# Note : il n'y a pas de compte client, donc un commentaire tout
# juste posté n'est visible que dans la session du navigateur qui
# l'a créé (géré côté frontend), pas via l'API tant qu'il n'est
# pas validé par l'admin.
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from database import obtenir_connexion

router = APIRouter(tags=["Commentaires"])
router_admin = APIRouter(prefix="/api/admin/commentaires", tags=["Commentaires (admin)"])


class CommentaireEntree(BaseModel):
    nom_client: str = Field(..., min_length=1, max_length=120)
    texte: str = Field(..., min_length=1, max_length=1000)


def formater_commentaire(ligne, avec_produit=False):
    donnees = {
        "id": ligne["id"],
        "produitId": ligne["produit_id"],
        "nomClient": ligne["nom_client"],
        "texte": ligne["texte"],
        "estPublic": bool(ligne["est_public"]),
        "dateCreation": ligne["date_creation"].isoformat(),
    }
    if avec_produit and "produit_nom" in ligne:
        donnees["produitNom"] = ligne["produit_nom"]
    return donnees


# ------------------------------------------------------------
# Côté client : commentaires publics d'un produit
# ------------------------------------------------------------
@router.get("/api/produits/{produit_id}/commentaires")
def lister_commentaires_publics(produit_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute(
        """
        SELECT * FROM commentaires_produits
        WHERE produit_id = %s AND est_public = TRUE
        ORDER BY date_creation DESC
        """,
        (produit_id,),
    )
    lignes = curseur.fetchall()
    curseur.close()
    connexion.close()
    return [formater_commentaire(ligne) for ligne in lignes]


@router.post("/api/produits/{produit_id}/commentaires", status_code=201)
def ajouter_commentaire(produit_id: int, commentaire: CommentaireEntree):
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)

    curseur.execute("SELECT id FROM produits WHERE id = %s", (produit_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Produit introuvable")

    curseur.execute(
        """
        INSERT INTO commentaires_produits (produit_id, nom_client, texte, est_public)
        VALUES (%s, %s, %s, FALSE)
        """,
        (produit_id, commentaire.nom_client, commentaire.texte),
    )
    connexion.commit()
    nouveau_id = curseur.lastrowid

    curseur.execute("SELECT * FROM commentaires_produits WHERE id = %s", (nouveau_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    # Renvoyé au client qui vient de poster, pour un affichage immédiat
    # marqué "en attente" dans sa propre session (pas visible ailleurs).
    return formater_commentaire(ligne)


# ------------------------------------------------------------
# Côté client : like d'un produit
# ------------------------------------------------------------
@router.post("/api/produits/{produit_id}/like")
def liker_produit(produit_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)

    curseur.execute("SELECT id FROM produits WHERE id = %s", (produit_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Produit introuvable")

    curseur.execute(
        "UPDATE produits SET nb_likes = nb_likes + 1 WHERE id = %s", (produit_id,)
    )
    connexion.commit()

    curseur.execute("SELECT nb_likes FROM produits WHERE id = %s", (produit_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    return {"produitId": produit_id, "nbLikes": ligne["nb_likes"]}


# ------------------------------------------------------------
# Côté admin : modération des commentaires
# ------------------------------------------------------------
@router_admin.get("")
def lister_tous_commentaires():
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute(
        """
        SELECT cp.*, p.nom AS produit_nom
        FROM commentaires_produits cp
        JOIN produits p ON p.id = cp.produit_id
        ORDER BY cp.date_creation DESC
        """
    )
    lignes = curseur.fetchall()
    curseur.close()
    connexion.close()
    return [formater_commentaire(ligne, avec_produit=True) for ligne in lignes]


@router_admin.patch("/{commentaire_id}/publier")
def publier_commentaire(commentaire_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)

    curseur.execute("SELECT id FROM commentaires_produits WHERE id = %s", (commentaire_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Commentaire introuvable")

    curseur.execute(
        "UPDATE commentaires_produits SET est_public = TRUE WHERE id = %s",
        (commentaire_id,),
    )
    connexion.commit()

    curseur.execute("SELECT * FROM commentaires_produits WHERE id = %s", (commentaire_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    return formater_commentaire(ligne)


@router_admin.delete("/{commentaire_id}", status_code=204)
def supprimer_commentaire(commentaire_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor()
    curseur.execute("SELECT id FROM commentaires_produits WHERE id = %s", (commentaire_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Commentaire introuvable")
    curseur.execute("DELETE FROM commentaires_produits WHERE id = %s", (commentaire_id,))
    connexion.commit()
    curseur.close()
    connexion.close()