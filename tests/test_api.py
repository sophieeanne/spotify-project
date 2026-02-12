import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

# Ed Sheeran - I Don't Care
TEST_TRACK_ID = "6f807x0ima9a1j3VPbc7VN" 

def print_separator(title):
    print(f"\n{'-'*10} {title} {'-'*10}")

def test_root():
    """Vérifie si l'API tourne"""
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("API en ligne :", response.json())
        else:
            print("Erreur API :", response.status_code)
    except requests.exceptions.ConnectionError:
        print("Impossible de se connecter")
        exit()

def test_get_song():
    """Vérifie qu'on peut récupérer les infos d'une chanson"""
    print_separator("TEST 1: Récupération infos d'une chanson")
    
    start = time.time()
    response = requests.get(f"{BASE_URL}/songs/{TEST_TRACK_ID}")
    latence = (time.time() - start) * 1000 # en ms
    
    if response.status_code == 200:
        song = response.json()
        print(f"Chanson trouvée : {song.get('track_name')} - {song.get('track_artist')}")
        print(f"Latence reseau + DB : {latence:.2f} ms")
    else:
        print("Erreur :", response.text)

def test_recommendation():
    """Teste la latence de l'algo de recommandation"""
    print_separator("TEST 2: Algorithme de recommandation")
    print(f"Demande de recommandation pour l'ID : {TEST_TRACK_ID}...")
    
    # Mesure du temps coté client (Latence totale perçue)
    start_total = time.time()
    response = requests.get(f"{BASE_URL}/recommend/{TEST_TRACK_ID}")
    end_total = time.time()
    
    total_latency = (end_total - start_total)
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"Succes ! Recommandations pour '{data['target']}' :")
        for i, rec in enumerate(data['recommendations']):
            print(f"   {i+1}. {rec['track_name']} (Dist: {rec['distance']:.4f})")
        
        # ANALYSE DE PERFORMANCE 
        server_compute_time = data['computation_time_seconds']
        network_overhead = total_latency - server_compute_time
        
        print("\nANALYSE DE LA LATENCE :")
        print(f"   1. Temps calcul serveur (CPU) : {server_compute_time:.4f} sec")
        print(f"   2. Latence totale client (W)  : {total_latency:.4f} sec")
        print(f"   -> Latence reseau : {network_overhead:.4f} sec")
        
        if total_latency > 0.5:
            print("\nALERTE : Latence élevée détectée")
    else:
        print("Erreur :", response.text)

if __name__ == "__main__":
    print("Démarrage des tests...")
    test_root()
    test_get_song()
    test_recommendation()