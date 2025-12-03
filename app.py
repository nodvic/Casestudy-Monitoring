from flask import Flask, request, jsonify, render_template
import datetime
import pyodbc 
import os
import sqlite3

app = Flask(__name__)
DATABASE_NAAM = 'monitoring_api.db'

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

def meting_opslaan(hostname, metric_naam, waarde, nu):
    conn = sqlite3.connect(DATABASE_NAAM)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO metingen (hostname, timestamp, metric_naam, waarde)
        VALUES (?, ?, ?, ?)
    ''', (hostname, nu, metric_naam, waarde))
    
    conn.commit()
    conn.close()

# API route (ontvangen van client data)
@app.route('/api/ingest', methods=['POST'])
def ontvang_metingen():
    try:
        inkomende_data = request.get_json()
        
        if not inkomende_data:
            return jsonify({"error": "Geen data ontvangen"}), 400
            
        hostname = inkomende_data.get('hostname', 'Onbekend')
        timestamp = inkomende_data.get('timestamp', datetime.datetime.now().isoformat())
        metrics = inkomende_data.get('metrics', {})

        print(f"\n[API] Nieuwe data ontvangen van: {hostname}")

        for metric_naam, waarde in metrics.items():
            if isinstance(waarde, dict):
                 for docker_metric, docker_waarde in waarde.items():
                    meting_opslaan(hostname, f'docker_{docker_metric}', docker_waarde, timestamp)
            else:
                meting_opslaan(hostname, metric_naam, waarde, timestamp)
        
        return jsonify({"message": "Data succesvol ontvangen en verwerkt", "status": "success"}), 201

    except Exception as e:
        print(f"[API FOUT] Er ging iets mis: {e}")
        return jsonify({"error": str(e)}), 500

# WEB FRONTEND route (tonen van data)
@app.route('/')
def dashboard():
    conn = sqlite3.connect(DATABASE_NAAM)
    cursor = conn.cursor()
    
    cursor.execute("SELECT timestamp, hostname, metric_naam, waarde FROM metingen ORDER BY timestamp DESC")
    metingen = cursor.fetchall()
    
    metingen_data = [{"timestamp": r[0], "hostname": r[1], "metric_naam": r[2], "waarde": r[3]} for r in metingen]
    
    hosts_count = len(set(r['hostname'] for r in metingen_data))
    laatste_cpu = next((r['waarde'] for r in metingen_data if r['metric_naam'] == 'cpu'), 'N/A')
    container_totaal = next((r['waarde'] for r in metingen_data if r['metric_naam'] == 'docker_total_containers'), 'N/A')

    conn.close()
    
    return render_template(
        'dashboard.html', 
        metingen=metingen_data,
        hosts_count=hosts_count,
        laatste_cpu=laatste_cpu,
        container_totaal=container_totaal
    )

if __name__ == '__main__':
    database_klaarmaken()
    print("[SERVER] API en WEB Frontend starten op poort 5000...")
    app.run(host='0.0.0.0', port=5000)