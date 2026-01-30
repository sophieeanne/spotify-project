import requests
import time
import json

# URL de ton API locale (lance d'abord uvicorn main:app --reload)
BASE_URL = "http://127.0.0.1:8000"

# Un ID de chanson qui existe dans le dataset (Ed Sheeran - I Don't Care)
TEST_TRACK_ID = "6f807x0ima9a1j3VPbc7VN" 

def print_separator(title):
    print(f"\n{'-'*10} {title} {'-'*10}")

def test_root():
    """Vérifie si l'API tourne"""
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ API en ligne :", response.json())
        else:
            print("❌ Erreur API :", response.status_code)
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter. Vérifie que 'uvicorn' est lancé dans un autre terminal.")
        exit()

def test_get_song():
    """Vérifie qu'on peut récupérer les infos d'une chanson"""
    print_separator("TEST 1: Récupération Chanson")
    
    start = time.time()
    response = requests.get(f"{BASE_URL}/songs/{TEST_TRACK_ID}")
    latence = (time.time() - start) * 1000 # en ms
    
    if response.status_code == 200:
        song = response.json()
        print(f"✅ Chanson trouvée : {song.get('track_name')} - {song.get('track_artist')}")
        print(f"⏱️ Latence réseau + DB : {latence:.2f} ms")
    else:
        print("❌ Erreur :", response.text)

def test_recommendation():
    """Teste la lourdeur de l'algo de recommandation"""
    print_separator("TEST 2: Algorithme de Recommandation")
    print(f"Demande de recommandation pour l'ID : {TEST_TRACK_ID}...")
    
    # Mesure du temps côté CLIENT (Latence totale perçue)
    start_total = time.time()
    response = requests.get(f"{BASE_URL}/recommend/{TEST_TRACK_ID}")
    end_total = time.time()
    
    total_latency = (end_total - start_total)
    
    if response.status_code == 200:
        data = response.json()
        
        # Affichage des résultats
        print(f"✅ Succès ! Recommandations pour '{data['target']}' :")
        for i, rec in enumerate(data['recommendations']):
            print(f"   {i+1}. {rec['track_name']} (Dist: {rec['distance']:.4f})")
        
        # ANALYSE DE PERFORMANCE (Crucial pour ton projet)
        server_compute_time = data['computation_time_seconds']
        network_overhead = total_latency - server_compute_time
        
        print("\n📊 ANALYSE DE LA LATENCE (Project Spirit) :")
        print(f"   1. Temps Calcul Serveur (CPU) : {server_compute_time:.4f} sec")
        print(f"   2. Latence Totale Client (W)  : {total_latency:.4f} sec")
        print(f"   -> Overhead Réseau/Serialisation : {network_overhead:.4f} sec")
        
        if total_latency > 0.5:
            print("\n⚠️  ALERTE : Latence élevée détectée ! C'est lent, c'est bon pour le projet !")
    else:
        print("❌ Erreur :", response.text)

if __name__ == "__main__":
    print("🚀 Démarrage des tests...")
    test_root()
    test_get_song()
    test_recommendation()