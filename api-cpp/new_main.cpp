#include <iostream>
#include <string>
#include <cmath>
#include <chrono>
#include <vector>
#include <algorithm>

// Framework HTTP : Lithium -> pour créer API en C++
#include <lithium_http_server.hh>

// MONGODB 
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <mongocxx/uri.hpp>
#include <bsoncxx/json.hpp>
#include <bsoncxx/builder/basic/document.hpp>
#include <bsoncxx/builder/basic/kvp.hpp>
#include <bsoncxx/builder/basic/array.hpp>

using namespace bsoncxx::builder::basic;

#ifndef LI_SYMBOL_track_id
#define LI_SYMBOL_track_id
LI_SYMBOL(track_id)
#endif

// Cache en RAM
struct SongFeature {
    std::string id;
    std::string name;
    std::string genre;
    double danceability;
    double energy;
    double valence;
};

// Structure pour stocker les résultats avant le tri
struct ScoredSong {
    std::string name;
    std::string id;
    double distance;
};

// Fonction pour extraire un nombre depuis MongoDB
double get_double_safe(const bsoncxx::document::view& doc, const std::string& key) {
    auto ele = doc[key];
    if (!ele) return 0.0;

    // On vérifie le type avant de l'extraire pour eviter un crash
    if (ele.type() == bsoncxx::type::k_double) return ele.get_double().value;
    if (ele.type() == bsoncxx::type::k_int32) return static_cast<double>(ele.get_int32().value);
    if (ele.type() == bsoncxx::type::k_int64) return static_cast<double>(ele.get_int64().value);
    return 0.0;
}

// Calcule distance euclidienne
double calculate_distance(const SongFeature& target, const SongFeature& candidate) {
    return std::sqrt(std::pow(target.danceability - candidate.danceability, 2) + 
                     std::pow(target.energy - candidate.energy, 2) + 
                     std::pow(target.valence - candidate.valence, 2));
}

int main() {
    // Initialisation de MongoDB 
    mongocxx::instance instance{};
    mongocxx::client client(mongocxx::uri("mongodb://127.0.0.1:27017"));
    auto collection = client["Spotify_songs"]["Songs"];

    // Cache (chargement au démarrage) 
    std::vector<SongFeature> global_songs_cache;
    std::cout << "⏳ Chargement de MongoDB vers la RAM C++..." << std::endl;
    
    auto cursor = collection.find({});
    for (auto&& doc : cursor) {
        SongFeature sf;
        sf.id = doc["track_id"] ? std::string(doc["track_id"].get_string().value) : "Unknown";
        sf.name = doc["track_name"] ? std::string(doc["track_name"].get_string().value) : "Unknown";
        sf.genre = doc["playlist_genre"] ? std::string(doc["playlist_genre"].get_string().value) : "";
        sf.danceability = get_double_safe(doc, "danceability");
        sf.energy = get_double_safe(doc, "energy");
        sf.valence = get_double_safe(doc, "valence");
        global_songs_cache.push_back(sf);
    }

    // Creation de l'API avec Lithium
    li::http_api api;

    // Route simple pour verifier que l'API fonctionne
    api.get("/") = [&](li::http_request& request, li::http_response& response) {
        response.write("{\"message\": \"API C++ avec Cache RAM\"}");
    };

    //Route pour chercher une chanson par ID 
    api.get("/songs/{{track_id}}") = [&](li::http_request& request, li::http_response& response) {
        auto params = request.url_parameters(s::track_id = std::string());
        std::string t_id = params.track_id;

        auto it = std::find_if(global_songs_cache.begin(), global_songs_cache.end(), 
            [&](const SongFeature& song) { return song.id == t_id; });

        if (it != global_songs_cache.end()) {
            // On reconstruit un petit JSON à la volée
            auto doc = make_document(
                kvp("track_id", it->id),
                kvp("track_name", it->name),
                kvp("playlist_genre", it->genre)
            );
            response.write(bsoncxx::to_json(doc.view()));
        } else {
            response.set_status(404);
            response.write("{\"detail\": \"Song not found\"}");
        }
    };

    // Recommendation de chansons
    api.get("/recommend/{{track_id}}") = [&](li::http_request& request, li::http_response& response) {
        // Demarrer le chronometre
        auto start_time = std::chrono::high_resolution_clock::now();

        auto params = request.url_parameters(s::track_id = std::string());
        std::string t_id = params.track_id;

        // Etape 1 : Trouver la cible dans la RAM 
        auto target_it = std::find_if(global_songs_cache.begin(), global_songs_cache.end(), 
            [&](const SongFeature& song) { return song.id == t_id; });

        if (target_it == global_songs_cache.end()) {
            response.set_status(404);
            response.write("{\"detail\": \"Song not found\"}");
            return;
        }
        
        const SongFeature& target_song = *target_it;
        std::vector<ScoredSong> scored_songs;

        // Etape 2 : Boucle sur toute la RAM pour calculer les distances 
        for (const auto& candidate : global_songs_cache) {
            if (candidate.genre == target_song.genre && candidate.id != target_song.id) {
                double dist = calculate_distance(target_song, candidate);
                scored_songs.push_back({candidate.name, candidate.id, dist});
            }
        }

        // Etape 3 : Trier et garder le Top 5
        std::sort(scored_songs.begin(), scored_songs.end(), [](const ScoredSong& a, const ScoredSong& b) {
            return a.distance < b.distance;
        });

        int top_n = std::min(5, (int)scored_songs.size());

        auto end_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> exec_time = end_time - start_time;

        // Construire le JSON
        auto arr_builder = bsoncxx::builder::basic::array{};
        for(int i = 0; i < top_n; ++i) {
            arr_builder.append(make_document(
                kvp("track_name", scored_songs[i].name),
                kvp("track_id", scored_songs[i].id),
                kvp("distance", scored_songs[i].distance)
            ));
        }

        auto response_doc = make_document(
            kvp("target", target_song.name),
            kvp("computation_time_seconds", exec_time.count()),
            kvp("recommendations", arr_builder)
        );

        response.write(bsoncxx::to_json(response_doc.view()));
    };

    std::cout << "Serveur en ligne sur http://localhost:8081 " << std::endl;
    li::http_serve(api, 8081);
    
    return 0;
}