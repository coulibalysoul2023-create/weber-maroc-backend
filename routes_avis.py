# ============================================================
# routes_avis.py
# Routes liées aux avis généraux sur le site (pas liés à un
# produit précis), déposés via le bouton flottant de la page
# Client :
#
# Côté client (public) :
#   GET  /api/avis  -> avis publics uniquement
#   POST /api/avis  -> ajoute un avis (en attente de modération)
#
# Côté admin (modération) :
#   GET    /api/admin/avis               -> tous les avis (public + attente)
#   PATCH  /api/admin/avis/{id}/publier   -> rend un avis public
#   DELETE /api/admin/avis/{id}           -> supprime un avis
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from database import obtenir_connexion

router = APIRouter(prefix="/api/avis", tags=["Avis du site"])
router_admin = APIRouter(prefix="/api/admin/avis", tags=["Avis du site (admin)"])


class AvisEntree(BaseModel):
    nom_client: str = Field(..., min_length=1, max_length=120)
    texte: str = Field(..., min_length=1, max_length=1000)


def formater_avis(ligne):
    return {
        "id": ligne["id"],
        "nomClient": ligne["nom_client"],
        "texte": ligne["texte"],
        "estPublic": bool(ligne["est_public"]),
        "dateCreation": ligne["date_creation"].isoformat(),
    }


# ------------------------------------------------------------
# Côté client
# ------------------------------------------------------------
@router.get("")
def lister_avis_publics():
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute(
        "SELECT * FROM avis_site WHERE est_public = TRUE ORDER BY date_creation DESC"
    )
    lignes = curseur.fetchall()
    curseur.close()
    connexion.close()
    return [formater_avis(ligne) for ligne in lignes]


@router.post("", status_code=201)
def ajouter_avis(avis: AvisEntree):
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute(
        "INSERT INTO avis_site (nom_client, texte, est_public) VALUES (%s, %s, FALSE)",
        (avis.nom_client, avis.texte),
    )
    connexion.commit()
    nouveau_id = curseur.lastrowid

    curseur.execute("SELECT * FROM avis_site WHERE id = %s", (nouveau_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    return formater_avis(ligne)


# ------------------------------------------------------------
# Côté admin : modération des avis
# ------------------------------------------------------------
@router_admin.get("")
def lister_tous_avis():
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute("SELECT * FROM avis_site ORDER BY date_creation DESC")
    lignes = curseur.fetchall()
    curseur.close()
    connexion.close()
    return [formater_avis(ligne) for ligne in lignes]


@router_admin.patch("/{avis_id}/publier")
def publier_avis(avis_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)

    curseur.execute("SELECT id FROM avis_site WHERE id = %s", (avis_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Avis introuvable")

    curseur.execute("UPDATE avis_site SET est_public = TRUE WHERE id = %s", (avis_id,))
    connexion.commit()

    curseur.execute("SELECT * FROM avis_site WHERE id = %s", (avis_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    return formater_avis(ligne)


@router_admin.delete("/{avis_id}", status_code=204)
def supprimer_avis(avis_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor()
    curseur.execute("SELECT id FROM avis_site WHERE id = %s", (avis_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Avis introuvable")
    curseur.execute("DELETE FROM avis_site WHERE id = %s", (avis_id,))
    connexion.commit()
    curseur.close()
    connexion.close()