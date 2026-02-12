import concurrent.futures
import requests
import time
import statistics  

# Configuration pour 100 utilisateurs
BASE_URL = "http://127.0.0.1:8000"
TEST_TRACK_ID = "6f807x0ima9a1j3VPbc7VN"  
CONCURRENCY = 100   
NB_REQUESTS = 500  

def send_request(i):
    start = time.time()
    try:
        # Timeout réduit à 5s pour ne pas bloquer indefiniment si le serveur sature trop
        resp = requests.get(f"{BASE_URL}/recommend/{TEST_TRACK_ID}", timeout=5)
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

# Analyse des resultats
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
print(f"   - Debit (throughput)    : {throughput:.2f} req/sec")
print(f"   - Taux d'erreur         : {errors}/{NB_REQUESTS} ({errors/NB_REQUESTS*100:.1f}%)")
print("-" * 30)
print(f"   - Latence moyenne (p50) : {avg_latency:.2f} sec")
print(f"   - Latence p95 (tail)    : {p95_latency:.2f} sec")
print(f"   - Latence Max (p100)    : {max_latency:.2f} sec")

# Interprétation automatique basée sur le cours
if p95_latency > 1.0:
    print("\nDIAGNOSTIC : Saturation critique !")
    print("   Le p95 dépasse 1 seconde. Les files d'attente (Queueing) sont pleines")
elif errors > 0:
    print("\nDIAGNOSTIC : Le serveur rejette des connexions (Timeouts/Erreurs)")
else:
    print("\nLe système tient la charge ")