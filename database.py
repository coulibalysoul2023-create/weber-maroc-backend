# ============================================================
# database.py
# Gère la connexion à la base de données MySQL. Toutes les
# routes (produits, clients, admin) passeront par la fonction
# obtenir_connexion() pour parler à la base.
# ============================================================

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Charge les identifiants depuis le fichier .env
load_dotenv()

CONFIG_DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "weber_maroc"),
    "charset": "utf8mb4",  # nécessaire pour bien gérer les accents français
    "use_unicode": True,
}


def obtenir_connexion():
    """
    Ouvre une nouvelle connexion à la base MySQL.
    Chaque route l'appelle, l'utilise, puis la referme
    (voir le paramètre 'with' dans les routes).
    """
    try:
        connexion = mysql.connector.connect(**CONFIG_DB)
        return connexion
    except Error as erreur:
        # On relève l'erreur pour que FastAPI puisse répondre
        # proprement avec un code d'erreur HTTP côté frontend
        raise Exception(f"Erreur de connexion à la base de données : {erreur}")


def tester_connexion():
    """Fonction utilitaire pour vérifier que tout fonctionne."""
    connexion = obtenir_connexion()
    curseur = connexion.cursor()
    curseur.execute("SELECT COUNT(*) FROM produits")
    resultat = curseur.fetchone()
    curseur.close()
    connexion.close()
    return resultat[0]