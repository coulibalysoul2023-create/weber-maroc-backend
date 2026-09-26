# ============================================================
# routes_categories.py
# Routes liées aux catégories de produits :
#   GET  /api/categories  -> liste toutes les catégories
#   POST /api/categories  -> ajoute une nouvelle catégorie (admin)
# ============================================================

import re
import unicodedata
from fastapi import APIRouter
from pydantic import BaseModel, Field
from database import obtenir_connexion

router = APIRouter(prefix="/api/categories", tags=["Catégories"])

# Icônes lucide-react proposées à l'admin pour habiller une catégorie
ICONES_AUTORISEES = {
    "LayoutGrid", "Layers", "Grid2x2", "PaintBucket", "Droplets",
    "PaintRoller", "Package", "Wrench", "ShieldCheck", "Sparkles", "Hammer",
}


class CategorieEntree(BaseModel):
    label: str = Field(..., min_length=1, max_length=80)
    icone: str = "LayoutGrid"


def generer_id(label: str) -> str:
    """Transforme un libellé (ex: 'Colle Carrelage') en identifiant
    technique simple (ex: 'colle_carrelage'), sans accents ni espaces."""
    texte = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    texte = texte.lower().strip()
    texte = re.sub(r"[^a-z0-9]+", "_", texte).strip("_")
    return texte or "categorie"


def formater_categorie(ligne):
    return {
        "id": ligne["id"],
        "label": ligne["libelle"],
        "icone": ligne["icone"] or "LayoutGrid",
    }


@router.get("")
def lister_categories():
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute("SELECT * FROM categories ORDER BY libelle ASC")
    lignes = curseur.fetchall()
    curseur.close()
    connexion.close()
    return [formater_categorie(ligne) for ligne in lignes]


@router.post("", status_code=201)
def ajouter_categorie(categorie: CategorieEntree):
    icone = categorie.icone if categorie.icone in ICONES_AUTORISEES else "LayoutGrid"
    identifiant = generer_id(categorie.label)

    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)

    # Évite les doublons d'identifiant en ajoutant un suffixe numérique
    identifiant_final = identifiant
    compteur = 2
    while True:
        curseur.execute("SELECT id FROM categories WHERE id = %s", (identifiant_final,))
        if not curseur.fetchone():
            break
        identifiant_final = f"{identifiant}_{compteur}"
        compteur += 1

    curseur.execute(
        "INSERT INTO categories (id, libelle, icone) VALUES (%s, %s, %s)",
        (identifiant_final, categorie.label, icone),
    )
    connexion.commit()

    curseur.execute("SELECT * FROM categories WHERE id = %s", (identifiant_final,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    return formater_categorie(ligne)