import concurrent.futures
import requests
import time
import statistics  
import random
import numpy as np

BASE_URL = "http://127.0.0.1:8080"  
CONCURRENCY = 1000   
NB_REQUESTS = 1000 

def load_track_data(filename):
    ids = []
    weights = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().replace('"', '').split(',')
                if len(parts) >= 2 and parts[0] != "track_id":
                    t_id = parts[0]
                    try:
                        pop = (float(parts[1]) + 1.0) ** 4 
                    except ValueError:
                        pop = 1.0
                    
                    ids.append(t_id)
                    weights.append(pop)
                    
        print(f"{len(ids)} musiques chargées avec leurs scores de popularité.")
    except Exception as e:
        print(f"Erreur lors du chargement : {e}")
    return ids, weights

TRACK_IDS, POPULARITIES = load_track_data("Spotify_songs.Songs.csv")

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=CONCURRENCY, pool_maxsize=CONCURRENCY)
session.mount('http://', adapter)

def send_request(i):
    track_id = random.choices(TRACK_IDS, weights=POPULARITIES, k=1)[0]
    
    start = time.time()
    try:
        resp = session.get(f"{BASE_URL}/recommend/{track_id}", timeout=5)
        duration = time.time() - start
        return duration, resp.status_code
    except Exception as e:
        return time.time() - start, "ERROR"

print(f"Lancement du test : {NB_REQUESTS} requêtes avec {CONCURRENCY} utilisateurs simultanés")

start_global = time.time()
latencies = []
errors = 0

# Lancement des threads
with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    results = list(executor.map(send_request, range(NB_REQUESTS)))

# Analyse des résultats
for duration, status in results:
    latencies.append(duration)
    if status != 200:
        errors += 1

end_global = time.time()
total_time = end_global - start_global

# Statistiques
if latencies:
    avg_latency = statistics.mean(latencies)
    try:
        p95_latency = statistics.quantiles(latencies, n=20)[18]
    except:
        latencies.sort()
        p95_latency = latencies[int(len(latencies)*0.95)]
        
    max_latency = max(latencies)
    throughput = NB_REQUESTS / total_time
else:
    avg_latency = 0
    p95_latency = 0
    max_latency = 0
    throughput = 0

print(f"\nRÉSULTATS POUR {CONCURRENCY} UTILISATEURS  :")
print(f"   - Temps total du test   : {total_time:.2f} sec")
print(f"   - Débit (throughput)    : {throughput:.2f} req/sec")
print(f"   - Taux d'erreur         : {errors}/{NB_REQUESTS} ({errors/NB_REQUESTS*100:.1f}%)")
print("-" * 30)
print(f"   - Latence moyenne (p50) : {avg_latency:.3f} sec")
print(f"   - Latence p95 (tail)    : {p95_latency:.3f} sec")
print(f"   - Latence max (p100)    : {max_latency:.3f} sec")

if p95_latency > 1.0:
    print("\nDIAGNOSTIC : Saturation critique !")
    print("   Le p95 dépasse 1 seconde. Les files d'attente (Queueing) sont pleines")
elif errors > 0:
    print("\nDIAGNOSTIC : Le serveur rejette des connexions (Timeouts/Erreurs)")
else:
    print("\nLe système tient parfaitement la charge !")