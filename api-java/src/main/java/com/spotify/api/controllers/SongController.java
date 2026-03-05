package com.spotify.api.controllers;

import com.spotify.api.repositories.SongRepository;
import com.spotify.api.services.RecommendationService;
import io.javalin.http.Context;
import org.bson.Document;

import java.util.Map;

public class SongController {
    // Références au repository et au service de recommandation
    private final SongRepository repository;
    private final RecommendationService recommendationService;

    // Constructeur pour initialiser les dépendances
    public SongController(SongRepository repository, RecommendationService recommendationService) {
        this.repository = repository;
        this.recommendationService = recommendationService;
    }

    // Route : GET /
    public void getRoot(Context ctx) {
        ctx.json(Map.of("message", "Spotify Recommender API V0 is running (Java Structured)"));
    }

    // Route : GET /songs/{track_id}
    public void getSong(Context ctx) {
        String trackId = ctx.pathParam("track_id");
        Document song = repository.findSongById(trackId);

        if (song == null) {
            ctx.status(404).json(Map.of("error", "Song not found"));
            return;
        }
        
        song.remove("_id"); // On cache l'ID interne de Mongo
        ctx.json(song);
    }

    // Route : GET /recommend/{track_id}
    public void getRecommendations(Context ctx) {
        String trackId = ctx.pathParam("track_id");

        try {
            Map<String, Object> response = recommendationService.getRecommendations(trackId);
            ctx.json(response);
        } catch (IllegalArgumentException e) {
            // Si le service renvoie une erreur (ex: chanson non trouvée)
            ctx.status(404).json(Map.of("error", e.getMessage()));
        }
    }
}
