#include <iostream>
#include <string>
#include <cmath>
#include <chrono>
#include <vector>
#include <algorithm>
#include <atomic>

// Framework HTTP : Lithium -> pour créer API en C++
#include <lithium_http_server.hh>

// MONGODB 
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <mongocxx/uri.hpp>
#include <mongocxx/pool.hpp>
#include <bsoncxx/json.hpp>
#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/builder/basic/document.hpp>
#include <bsoncxx/builder/basic/kvp.hpp>
#include <bsoncxx/builder/basic/array.hpp>

// REDIS
#include <sw/redis++/redis++.h>

using namespace bsoncxx::builder::basic;

#ifndef LI_SYMBOL_track_id
#define LI_SYMBOL_track_id
LI_SYMBOL(track_id)
LI_SYMBOL(threads)
#endif

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
double calculate_distance(const bsoncxx::document::view& target, const bsoncxx::document::view& candidate) {
    double d1 = get_double_safe(target, "danceability");
    double e1 = get_double_safe(target, "energy");
    double v1 = get_double_safe(target, "valence");

    double d2 = get_double_safe(candidate, "danceability");
    double e2 = get_double_safe(candidate, "energy");
    double v2 = get_double_safe(candidate, "valence");

    return std::sqrt(std::pow(d1 - d2, 2) + std::pow(e1 - e2, 2) + std::pow(v1 - v2, 2));
}

// LOAD SHEDDING 
std::atomic<int> active_requests{0};
const int MAX_CONCURRENT_REQUESTS = 300;

struct RequestGuard {
    std::atomic<int>& counter;
    RequestGuard(std::atomic<int>& c) : counter(c) { counter++; }
    ~RequestGuard() { counter--; }
};


int main(int argc, char* argv[]) {
    // On definit le port 8081 par defaut
    int port = 8081;

    // Si on tape un port dans le terminal, on remplace la valeur du port
    if (argc > 1) {
       
        port = std::stoi(argv[1]);
    }
    // Initialisation de MongoDB 
    mongocxx::instance instance{};

    // Connection base de données en local (via Docker)
    mongocxx::uri uri("mongodb://127.0.0.1:27017");
    mongocxx::pool pool{mongocxx::uri("mongodb://127.0.0.1:27017")};

    // Connection base de données en ligne (MongoDB Atlas)
    //const char* env_uri = std::getenv("MONGODB_URI");

    //if (!env_uri) {
        //std::cerr << "ERREUR : La variable MONGODB_URI n'est pas définie" << std::endl;
        //return 1;
    //}


    //std::string mongo_uri(env_uri);

    //mongocxx::uri uri(mongo_uri);
    //mongocxx::pool pool{mongocxx::uri(mongo_uri)};

    // Initialisation de Redis
    sw::redis::Redis redis("tcp://127.0.0.1:6379");

    // Creation de l'API avec Lithium
    li::http_api api;

    // Route simple pour verifier que l'API fonctionne
    api.get("/") = [&](li::http_request& request, li::http_response& response) {
        response.write("{\"message\": \"Spotify Recommender API V1 is running (C++ Version)\"}");
    };

    // Route pour chercher une chanson par ID 
    api.get("/songs/{{track_id}}") = [&](li::http_request& request, li::http_response& response) {
        auto client = pool.acquire();
        auto collection = (*client)["Spotify_songs"]["Songs"];
        
        auto params = request.url_parameters(s::track_id = std::string());
        std::string t_id = params.track_id;

        auto doc = collection.find_one(make_document(kvp("track_id", t_id)));
        if (doc) {
            response.write(bsoncxx::to_json(doc->view()));
        } else {
            response.set_status(404);
            response.write("{\"detail\": \"Song not found\"}");
        }
    };

    // Recommendation de chansons
    api.get("/recommend/{{track_id}}") = [&](li::http_request& request, li::http_response& response) {
        // Demarrer le chronometre
        auto start_time = std::chrono::high_resolution_clock::now();

        if (active_requests.load() >= MAX_CONCURRENT_REQUESTS) {
            std::cout << "BOUM ! Rejet instantané (Load Shedding)" << std::endl;
            response.set_status(503);
            response.write("{\"detail\": \"Service Unavailable\"}");
            return;
        }

        RequestGuard guard(active_requests);

        auto params = request.url_parameters(s::track_id = std::string());
        std::string t_id = params.track_id;

        // Verification dans le cache Redis
        std::string cache_key = "recommend:" + t_id;
        try {
            auto cached_response = redis.get(cache_key);
            if (cached_response) {
                // Si on trouve une réponse dans Redis, on retourne le resultat
                std::cout << "CACHE HIT (Redis) pour la musique " << t_id << std::endl;
                response.write(*cached_response);
                return; 
            }
        } catch (const sw::redis::Error& e) {
            std::cerr << "Erreur Redis : " << e.what() << std::endl;
        }
        std::cout << "CACHE MISS... Calcul avec MongoDB en cours..." << std::endl;


        auto mongo_client = pool.acquire();
        auto collection = (*mongo_client)["Spotify_songs"]["Songs"];

        // Etape 1 : Recuperer la chanson cible
        auto target_opt = collection.find_one(make_document(kvp("track_id", t_id)));
        if (!target_opt) {
            response.set_status(404);
            response.write("{\"detail\": \"Song not found\"}");
            return;
        }
        auto target_doc = target_opt->view();

        // Etape 2 : Filtrer les chansons par genre 
        std::string genre = "";
        if (target_doc["playlist_genre"] && target_doc["playlist_genre"].type() == bsoncxx::type::k_string) {
            genre = std::string(target_doc["playlist_genre"].get_string().value);
        }

        auto query_filter = make_document(
            kvp("playlist_genre", genre),
            kvp("track_id", make_document(kvp("$ne", t_id))) // Exclure la chanson elle-même
        );

        // Etape 3 : Boucle de calcul de distance
        auto cursor = collection.find(query_filter.view());
        std::vector<ScoredSong> scored_songs;

        for (auto&& doc : cursor) {
            double dist = calculate_distance(target_doc, doc);
            
            std::string c_name = doc["track_name"] ? std::string(doc["track_name"].get_string().value) : "Unknown";
            std::string c_id = doc["track_id"] ? std::string(doc["track_id"].get_string().value) : "Unknown";
            
            scored_songs.push_back({c_name, c_id, dist});
        }

        // Etape 4 : tri des resultats par distance
        std::sort(scored_songs.begin(), scored_songs.end(), [](const ScoredSong& a, const ScoredSong& b) {
            return a.distance < b.distance;
        });

        int top_n = std::min(5, (int)scored_songs.size());

        // Arreter le chronometre
        auto end_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> exec_time = end_time - start_time;

        auto arr_builder = bsoncxx::builder::basic::array{};
        for(int i = 0; i < top_n; ++i) {
            arr_builder.append(make_document(
                kvp("track_name", scored_songs[i].name),
                kvp("track_id", scored_songs[i].id),
                kvp("distance", scored_songs[i].distance)
            ));
        }

        std::string target_name = target_doc["track_name"] ? std::string(target_doc["track_name"].get_string().value) : "Unknown";

        auto response_doc = make_document(
            kvp("target", target_name),
            kvp("computation_time_seconds", exec_time.count()),
            kvp("recommendations", arr_builder)
        );

        // Stocker le résultat dans Redis pour les prochaines requêtes
        std::string final_json = bsoncxx::to_json(response_doc.view());
        try {
            redis.set(cache_key, final_json);
            redis.expire(cache_key, 3600); // Expire dans 3600 secondes
        } catch (const sw::redis::Error& e) {
            std::cerr << "Erreur Redis (Ecriture) : " << e.what() << std::endl;
        }

        // Envoyer la réponse finale
        response.write(bsoncxx::to_json(response_doc.view()));
    };

    std::cout << "API Worker en ligne sur http://127.0.0.1:" << port << std::endl;
    li::http_serve(api, port, s::threads = 100);
    
    return 0;
}
