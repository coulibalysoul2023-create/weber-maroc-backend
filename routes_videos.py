# ============================================================
# routes_videos.py
# Routes liées aux vidéos publicitaires affichées sur la page
# Client (carrousel), gérées par l'admin :
# - GET    /api/videos       -> liste toutes les vidéos
# - POST   /api/videos       -> ajoute une nouvelle vidéo
# - DELETE /api/videos/{id}  -> supprime une vidéo
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import obtenir_connexion

router = APIRouter(prefix="/api/videos", tags=["Vidéos publicitaires"])


class VideoEntree(BaseModel):
    titre: Optional[str] = None
    video_url: str


def formater_video(ligne):
    return {
        "id": ligne["id"],
        "titre": ligne["titre"],
        "videoUrl": ligne["video_url"],
        "dateCreation": ligne["date_creation"].isoformat(),
    }


@router.get("")
def lister_videos():
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute("SELECT * FROM videos_publicitaires ORDER BY date_creation DESC")
    lignes = curseur.fetchall()
    curseur.close()
    connexion.close()
    return [formater_video(ligne) for ligne in lignes]


@router.post("", status_code=201)
def ajouter_video(video: VideoEntree):
    connexion = obtenir_connexion()
    curseur = connexion.cursor(dictionary=True)
    curseur.execute(
        "INSERT INTO videos_publicitaires (titre, video_url) VALUES (%s, %s)",
        (video.titre, video.video_url),
    )
    connexion.commit()
    nouveau_id = curseur.lastrowid

    curseur.execute("SELECT * FROM videos_publicitaires WHERE id = %s", (nouveau_id,))
    ligne = curseur.fetchone()
    curseur.close()
    connexion.close()
    return formater_video(ligne)


@router.delete("/{video_id}", status_code=204)
def supprimer_video(video_id: int):
    connexion = obtenir_connexion()
    curseur = connexion.cursor()
    curseur.execute("SELECT id FROM videos_publicitaires WHERE id = %s", (video_id,))
    if not curseur.fetchone():
        curseur.close()
        connexion.close()
        raise HTTPException(status_code=404, detail="Vidéo introuvable")
    curseur.execute("DELETE FROM videos_publicitaires WHERE id = %s", (video_id,))
    connexion.commit()
    curseur.close()
    connexion.close()