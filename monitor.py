import sqlite3
import datetime
import json
import psutil
import requests

DATABASE_NAAM = 'monitoring_data.db'
API_URL = 'http://127.0.0.1:5000/api/ingest'

def database_klaarmaken():
    conn = sqlite3.connect(DATABASE_NAAM)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metingen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT,
            timestamp TEXT,
            metric_naam TEXT,
            waarde REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def meting_opslaan(hostname, metric_naam, waarde):
    conn = sqlite3.connect(DATABASE_NAAM)
    cursor = conn.cursor()
    
    nu = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO metingen (hostname, timestamp, metric_naam, waarde)
        VALUES (?, ?, ?, ?)
    ''', (hostname, nu, metric_naam, waarde))
    
    conn.commit()
    conn.close()
    
    print(f"[INFO] Meting lokaal opgeslagen: {hostname} | {metric_naam}: {waarde}")

def verstuur_naar_cloud(payload):
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200 or response.status_code == 201:
            print("[INFO] Data succesvol verstuurd naar Azure API.")
        else:
            print(f"[FOUT] API retourneerde statuscode: {response.status_code}")
    except Exception as e:
        print(f"[FOUT] Kon geen verbinding maken met de API: {e}")

def doe_automatische_meting():
    print("\n--- Automatische Meting Registreren ---")
    
    hostname = input("Voer een naam in voor deze meting: ")
    
    print("[INFO] Bezig met het verzamelen van lokale systeemdata...")
    try:
        cpu_gebruik = psutil.cpu_percent(interval=1)
        geheugen_gebruik = psutil.virtual_memory().percent
        schijf_gebruik = psutil.disk_usage('/').percent
        
        print("[INFO] Metingen voltooid.")
        
        meting_opslaan(hostname, 'cpu_usage_pct', cpu_gebruik)
        meting_opslaan(hostname, 'memory_usage_pct', geheugen_gebruik)
        meting_opslaan(hostname, 'disk_usage_pct', schijf_gebruik)
        
        cloud_payload = {
            "hostname": hostname,
            "timestamp": datetime.datetime.now().isoformat(),
            "metrics": {
                "cpu": cpu_gebruik,
                "memory": geheugen_gebruik,
                "disk": schijf_gebruik
            }
        }
        
        print("[INFO] Data klaarmaken voor verzending naar Cloud...")
        verstuur_naar_cloud(cloud_payload)
        
        print("--- Metingen Succesvol Verwerkt ---")
        
    except Exception as e:
        print(f"[FOUT] Er is een fout opgetreden: {e}")

def toon_rapport():
    print("\n--- Volledig Rapport (Lokale Database) ---")
    
    conn = sqlite3.connect(DATABASE_NAAM)
    cursor = conn.cursor()
    
    cursor.execute("SELECT timestamp, hostname, metric_naam, waarde FROM metingen ORDER BY timestamp DESC")
    
    resultaten = cursor.fetchall()
    
    if not resultaten:
        print("[INFO] De database is nog leeg. Voer eerst een meting uit.")
    else:
        print(f"{'TIJDSTIP':<20} {'HOSTNAME':<15} {'METRIEK':<15} {'WAARDE'}")
        print("-" * 60)
        for rij in resultaten:
            print(f"{rij[0]:<20} {rij[1]:<15} {rij[2]:<15} {rij[3]}")
            
    conn.close()

def exporteer_naar_json():
    print("\n--- Data Exporteren naar JSON ---")
    
    conn = sqlite3.connect(DATABASE_NAAM)
    cursor = conn.cursor()
    
    cursor.execute("SELECT timestamp, hostname, metric_naam, waarde FROM metingen ORDER BY timestamp")
    resultaten = cursor.fetchall()
    
    if not resultaten:
        print("[INFO] De database is nog leeg. Er is niets om te exporteren.")
        conn.close()
        return

    export_data = []
    for timestamp, hostname, metric_naam, waarde in resultaten:
        export_data.append({
            "tijd": timestamp,
            "host": hostname,
            "metriek": metric_naam,
            "waarde": waarde
        })

    with open('export.json', 'w') as f:
        json.dump(export_data, f, indent=4)
    
    print("[SUCCES] Data geëxporteerd naar 'export.json'.")
    conn.close()

database_klaarmaken()

while True:
    print("\n-- Hoofdmenu --")
    print("Kies een optie:")
    print("1. Meting uitvoeren (en naar Azure sturen)")
    print("2. Toon lokaal rapport")
    print("3. Lokaal exporteren naar JSON")
    print("4. Stoppen")
    
    keuze = input("Keuze: ")
    
    if keuze == '1':
        doe_automatische_meting()
    elif keuze == '2':
        toon_rapport()
    elif keuze == '3':
        exporteer_naar_json()
    elif keuze == '4':
        print("Applicatie wordt gestopt.")
        break
    else:
        print("[FOUT] Ongeldige keuze, probeer opnieuw.")