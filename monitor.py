import sqlite3
import datetime
import json
import psutil
import requests
import os
import time

API_URL = os.getenv('API_ENDPOINT', 'https://monitoringapp.graysand-800d58de.switzerlandnorth.azurecontainerapps.io/api/ingest')

def send_payload(payload):
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
        raise
    except Exception as e:
        print(f"[FOUT] Er is een fout opgetreden bij de API-verbinding: {e}")
        raise

def doe_automatische_meting():
    print("\n--- Automatische Meting Registreren ---")
    
    hostname = os.name
    print(f"[INFO] Hostname voor meting: {hostname}")
    print("[INFO] Bezig met het verzamelen van lokale systeemdata...")
    try:
        cpu_gebruik = psutil.cpu_percent(interval=1)
        geheugen_gebruik = psutil.virtual_memory().percent
        schijf_gebruik = psutil.disk_usage('/').percent
        
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
        send_payload(cloud_payload)
        
        print("--- Metingen Succesvol Verwerkt ---")
        
    except Exception as e:
        print(f"[FOUT] Er is een fout opgetreden: {e}")
        #raise

if __name__ == '__main__':
    while True:
        doe_automatische_meting()
        time.sleep(300) #elke 5 min