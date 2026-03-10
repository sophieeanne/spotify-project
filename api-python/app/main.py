from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
import math
import time

app = FastAPI()

client = MongoClient("mongodb://localhost:27017/")
db = client["Spotify_songs"]
collection = db["Songs"]


def calculate_distance(song1, song2):
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
    
    target_song = collection.find_one({"track_id": track_id})
    if not target_song:
        raise HTTPException(status_code=404, detail="Song not found")

    target_genre = target_song.get("playlist_genre")
    query_filter = {
        "playlist_genre": target_genre,
        "track_id": {"$ne": track_id}
    }
    
    candidate_songs = list(collection.find(query_filter))
    
    scored_songs = []
    for song in candidate_songs:
        dist = calculate_distance(target_song, song)
        scored_songs.append({
            "track_name": song.get("track_name"),
            "track_id": song.get("track_id"),
            "distance": dist
        })
    
    scored_songs.sort(key=lambda x: x["distance"])
    recommendations = scored_songs[:5]
    
    execution_time = time.time() - start_time
    
    return {
        "target": target_song.get("track_name"),
        "computation_time_seconds": execution_time,
        "recommendations": recommendations
    }


