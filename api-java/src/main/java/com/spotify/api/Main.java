package com.spotify.api;

import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoDatabase;
import com.spotify.api.controllers.SongController;
import com.spotify.api.repositories.SongRepository;
import com.spotify.api.services.RecommendationService;
import io.javalin.Javalin;

public class Main {
    public static void main(String[] args) {
        // 1. Connexion à la base de données
        MongoClient mongoClient = MongoClients.create("mongodb://localhost:27017/");
        MongoDatabase db = mongoClient.getDatabase("spotify");

        // 2. Instanciation des couches
        SongRepository repository = new SongRepository(db);
        RecommendationService service = new RecommendationService(repository);
        SongController controller = new SongController(repository, service);

        // 3. Configuration et lancement du serveur web
        Javalin app = Javalin.create().start(8000);

        // 4. Définition des routes
        app.get("/", controller::getRoot);
        app.get("/songs/{track_id}", controller::getSong);
        app.get("/recommend/{track_id}", controller::getRecommendations);
        
        // Arrêt propre de Mongo si on coupe le serveur
        Runtime.getRuntime().addShutdownHook(new Thread(mongoClient::close));
    }
    
}
