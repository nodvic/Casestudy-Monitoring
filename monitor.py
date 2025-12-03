import sqlite3
import datetime
import json
import psutil
import requests
import os

DATABASE_NAAM = 'monitoring_data.db'
API_URL = os.getenv('API_ENDPOINT', 'http://monitoring-api:5000/api/ingest')

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
    print(f"[INFO] Verbindingsdoel: {API_URL}")
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200 or response.status_code == 201:
            print("[INFO] Data succesvol verstuurd naar API.")
        else:
            print(f"[FOUT] API retourneerde statuscode: {response.status_code}")
            print(f"[FOUT] API Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("[FATALE FOUT] Kon GEEN verbinding maken met de API-container. Zorg dat de API-service draait en bereikbaar is via de netwerknaam.")
    except Exception as e:
        print(f"[FOUT] Er is een fout opgetreden bij de API-verbinding: {e}")

def doe_automatische_meting():
    print("\n--- Automatische Meting Registreren ---")
    
    hostname = os.uname().nodename 
    print(f"[INFO] Hostname voor meting: {hostname}")
    
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

if __name__ == '__main__':
    database_klaarmaken()
    doe_automatische_meting()