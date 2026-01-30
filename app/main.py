from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
import math
import time

app = FastAPI()

client = MongoClient("mongodb://localhost:27017/")
db = client["spotify"]
collection = db["database.spotify 30k"]


# Fonction mathématique simple (Distance Euclidienne)
# On compare deux chansons sur : danceability, energy, valence
def calculate_distance(song1, song2):
    # On récupère les champs. On met 0.0 par sécurité si le champ manque.
    d1 = float(song1.get("danceability", 0.0))
    e1 = float(song1.get("energy", 0.0))
    v1 = float(song1.get("valence", 0.0))
    
    d2 = float(song2.get("danceability", 0.0))
    e2 = float(song2.get("energy", 0.0))
    v2 = float(song2.get("valence", 0.0))
    
    return math.sqrt((d1 - d2)**2 + (e1 - e2)**2 + (v1 - v2)**2)

@app.get("/")
def read_root():
    return {"message": "Spotify Recommender API V0 is running"}

@app.get("/songs/{track_id}")
def get_song(track_id: str):
    song = collection.find_one({"track_id": track_id}, {"_id": 0})
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song

@app.get("/recommend/{track_id}")
def recommend(track_id: str):
    start_time = time.time()
    
    # 1. Récupérer la chanson cible
    target_song = collection.find_one({"track_id": track_id})
    if not target_song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    # 2. Filtrage (L'optimisation est ICI)
    # On ne demande à Mongo que les chansons du même genre
    # On exclut toujours la chanson elle-même
    target_genre = target_song.get("playlist_genre")
    query_filter = {
        "playlist_genre": target_genre,
        "track_id": {"$ne": track_id}
    }
    
    # Mongo fait le travail de tri initial
    candidate_songs = list(collection.find(query_filter))
    
    # 3. Calcul de distance (sur beaucoup moins de candidats !)
    scored_songs = []
    for song in candidate_songs:
        dist = calculate_distance(target_song, song)
        scored_songs.append({
            "track_name": song.get("track_name"),
            "track_id": song.get("track_id"),
            "distance": dist
        })
    
    
    # 4. Trier par distance (plus petit = plus proche) et prendre le top 5
    scored_songs.sort(key=lambda x: x["distance"])
    recommendations = scored_songs[:5]
    
    execution_time = time.time() - start_time
    
    return {
        "target": target_song.get("track_name"),
        "computation_time_seconds": execution_time,
        "recommendations": recommendations
    }


