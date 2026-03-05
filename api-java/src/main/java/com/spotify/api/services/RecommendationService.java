package com.spotify.api.services;

import com.spotify.api.repositories.SongRepository;
import org.bson.Document;
import java.util.*;

public class RecommendationService {
    private final SongRepository repository;

    // Constructeur pour initialiser le repository
    public RecommendationService(SongRepository repository) {
        this.repository = repository;
    }
    
    // Méthode principale pour obtenir les recommandations basées sur une chanson cible
    public Map<String, Object> getRecommendations(String trackId) {
        long startTime = System.currentTimeMillis();

        // 1. Chercher la chanson cible
        Document targetSong = repository.findSongById(trackId);
        if (targetSong == null) {
            throw new IllegalArgumentException("Song not found");
        }

        String targetGenre = targetSong.getString("playlist_genre");

        // 2. Récupérer les candidats
        List<Document> candidates = repository.findCandidates(targetGenre, trackId);
        List<Map<String, Object>> scoredSongs = new ArrayList<>();

        // 3. Calcul de distance
        for (Document song : candidates) {
            double dist = calculateDistance(targetSong, song);
            scoredSongs.add(Map.of(
                "track_name", song.getString("track_name"),
                "track_id", song.getString("track_id"),
                "distance", dist
            ));
        }

        // 4. Tri et sélection des 5 meilleurs
        scoredSongs.sort(Comparator.comparingDouble(s -> (Double) s.get("distance")));
        List<Map<String, Object>> top5 = scoredSongs.subList(0, Math.min(5, scoredSongs.size()));

        double executionTime = (System.currentTimeMillis() - startTime) / 1000.0;

        // 5. Formatage de la réponse
        return Map.of(
            "target", targetSong.getString("track_name"),
            "computation_time_seconds", executionTime,
            "recommendations", top5
        );
    }


    // Méthode pour calculer la distance entre deux chansons en utilisant les caractéristiques audio
    private double calculateDistance(Document s1, Document s2) {
        double d1 = getDoubleSafely(s1, "danceability");
        double e1 = getDoubleSafely(s1, "energy");
        double v1 = getDoubleSafely(s1, "valence");

        double d2 = getDoubleSafely(s2, "danceability");
        double e2 = getDoubleSafely(s2, "energy");
        double v2 = getDoubleSafely(s2, "valence");

        return Math.sqrt(Math.pow(d1 - d2, 2) + Math.pow(e1 - e2, 2) + Math.pow(v1 - v2, 2));
    }

    private double getDoubleSafely(Document doc, String key) {
        Object val = doc.get(key);
        if (val instanceof Number) return ((Number) val).doubleValue();
        if (val instanceof String) {
            try { return Double.parseDouble((String) val); } catch (Exception e) { return 0.0; }
        }
        return 0.0;
    }

}
