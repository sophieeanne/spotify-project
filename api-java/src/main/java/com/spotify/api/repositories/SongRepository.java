package com.spotify.api.repositories;

// Import pour MongoDB et d'autres classes nécessaires
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import org.bson.Document;
import java.util.ArrayList;
import java.util.List;

public class SongRepository {

    // Référence à la collection MongoDB pour les chansons
    private final MongoCollection<Document> collection;

    // Constructeur pour initialiser la collection à partir de la base de données MongoDB
    public SongRepository(MongoDatabase database) {
        this.collection = database.getCollection("Songs");
    }

    // Méthode pour trouver une chanson par son ID
    public Document findSongById(String trackId){
        return collection.find(new Document("track_id", trackId)).first();
    }
    
    // Méthode pour trouver des chansons candidates basées sur le genre et en excluant une chanson spécifique
    public List<Document> findCandidates(String genre, String excludeTrackId) {
        Document query = new Document("playlist_genre", genre)
                .append("track_id", new Document("$ne", excludeTrackId));
        
        return collection.find(query).into(new ArrayList<>());
    }

}
