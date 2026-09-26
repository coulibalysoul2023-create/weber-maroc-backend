from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from deep_translator import GoogleTranslator
from database import obtenir_connexion
import time


router = APIRouter(prefix="/api/produits", tags=["Produits"])


class ProduitEntree(BaseModel):
    nom: str
    categorie_id: str
    description: str
    description_ar: Optional[str] = None
    prix_normal: float
    prix_promo: float
    icone: str
    photo_url: Optional[str] = None
    usages: list[str] = []
    rupture_stock: bool = False
    en_promo: bool = True

def traduire_en_arabe(texte: str) -> str:
    """Traduit automatiquement la description en arabe si l'admin ne l'a pas fournie."""
    try:
        return GoogleTranslator(source="fr", target="ar").translate(texte)
    except Exception as erreur:
        print(f"[ERREUR TRADUCTION] {type(erreur).__name__}: {erreur}")
        return texte


REQUETE_BASE_PRODUITS = """
    SELECT
        p.id, p.nom, p.description, p.description_ar, p.prix_normal, p.prix_promo,
        p.icone, p.photo_url, p.categorie_id, p.nb_likes, p.rupture_stock, p.en_promo,
        c.libelle AS categorie_libelle,
        GROUP_CONCAT(pu.usage_id) AS usages
    FROM produits p
    JOIN categories c ON p.categorie_id = c.id
    LEFT JOIN produit_usages pu ON pu.produit_id = p.id
"""


def formater_produit(ligne):
    return {
        "id": ligne["id"],
        "nom": ligne["nom"],
        "description": ligne["description"],
        "descriptionAr": ligne["description_ar"],
        "prixNormal": float(ligne["prix_normal"]),
        "prixPromo": float(ligne["prix_promo"]),
        "icone": ligne["icone"],
        "photoUrl": ligne["photo_url"],
        "categorie": ligne["categorie_id"],
        "categorieLibelle": ligne["categorie_libelle"],
        "nbLikes": ligne["nb_likes"] or 0,
        "ruptureStock": bool(ligne["rupture_stock"]),
        "enPromo": bool(ligne["en_promo"]),
        "usages": ligne["usages"].split(",") if ligne["usages"] else [],
    }


@router.get("")
def lister_produits():
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute(REQUETE_BASE_PRODUITS + " GROUP BY p.id ORDER BY p.date_creation DESC")
    lignes = curseur.fetchall()
    curseur.close()
    connexion.close()
    return [formater_produit(ligne) for ligne in lignes]


@router.get("/{produit_id}")
def obtenir_produit(produit_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute(REQUETE_BASE_PRODUITS + " WHERE p.id = %s GROUP BY p.id", (produit_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    if not ligne:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return formater_produit(ligne)


@router.post("", status_code=201)
def ajouter_produit(produit: ProduitEntree):
    connexion = obtenir_connexion()
    curseur = connexion.cursor()

    # Si l'admin n'a pas rempli la version arabe, on la génère automatiquement
    description_ar = (produit.description_ar or "").strip()
    if not description_ar:
        description_ar = traduire_en_arabe(produit.description)

    curseur.execute(
        """
        INSERT INTO produits
            (categorie_id, nom, description, description_ar, prix_normal, prix_promo,
             icone, photo_url, rupture_stock, en_promo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            produit.categorie_id, produit.nom, produit.description, description_ar,
            produit.prix_normal, produit.prix_promo, produit.icone, produit.photo_url,
            produit.rupture_stock, produit.en_promo,
        ),
    )
    nouveau_id = curseur.lastrowid

    for usage_id in produit.usages:
        curseur.execute(
            "INSERT INTO produit_usages (produit_id, usage_id) VALUES (%s, %s)",
            (nouveau_id, usage_id),
        )

    connexion.commit()
    curseur.close()
    connexion.close()
    return obtenir_produit(nouveau_id)


@router.put("/{produit_id}")
def modifier_produit(produit_id: int, produit: ProduitEntree):
    connexion = obtenir_connexion()
    curseur = connexion.cursor()

    curseur.execute("SELECT id FROM produits WHERE id = %s", (produit_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Produit introuvable")

    description_ar = (produit.description_ar or "").strip()
    if not description_ar:
        description_ar = traduire_en_arabe(produit.description)

    curseur.execute(
        """
        UPDATE produits
        SET categorie_id = %s, nom = %s, description = %s, description_ar = %s,
            prix_normal = %s, prix_promo = %s, icone = %s, photo_url = %s,
            rupture_stock = %s, en_promo = %s
        WHERE id = %s
        """,
        (
            produit.categorie_id, produit.nom, produit.description, description_ar,
            produit.prix_normal, produit.prix_promo, produit.icone,
            produit.photo_url, produit.rupture_stock, produit.en_promo, produit_id,
        ),
    )

    curseur.execute("DELETE FROM produit_usages WHERE produit_id = %s", (produit_id,))
    for usage_id in produit.usages:
        curseur.execute(
            "INSERT INTO produit_usages (produit_id, usage_id) VALUES (%s, %s)",
            (produit_id, usage_id),
        )

    connexion.commit()
    curseur.close()
    connexion.close()
    return obtenir_produit(produit_id)


@router.delete("/{produit_id}", status_code=204)
def supprimer_produit(produit_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor()
    curseur.execute("SELECT id FROM produits WHERE id = %s", (produit_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Produit introuvable")
    curseur.execute("DELETE FROM produits WHERE id = %s", (produit_id,))
    connexion.commit()
    curseur.close()
    connexion.close()