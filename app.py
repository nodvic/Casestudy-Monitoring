from flask import Flask, request, redirect, url_for, session, jsonify, render_template
import datetime
import pyodbc 
import os
if not os.path.exists('data'):
    os.makedirs('data')
import sqlite3
from requests_oauthlib import OAuth2Session

CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')
TENANT_ID = os.environ.get('AZURE_TENANT_ID')
REDIRECT_URI = os.environ.get('AZURE_REDIRECT_URI', 'http://localhost:5000/auth/callback')

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
AUTHORIZE_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
SCOPE = ["User.Read", "openid", "profile"]

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'uw_zeer_veilige_geheime_sleutel') 
DATABASE_NAAM = os.path.join('data', 'monitoring_api.db')

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


def is_authenticated():
    return 'user_info' in session

def get_azure_auth_session():
    return OAuth2Session(CLIENT_ID, scope=SCOPE, redirect_uri=REDIRECT_URI)

def login_required(f):
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/login')
def login():
    azure = get_azure_auth_session()
    authorization_url, state = azure.authorization_url(AUTHORIZE_URL)
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/auth/callback')
def callback():
    try:
        azure = get_azure_auth_session()
        token = azure.fetch_token(
            TOKEN_URL,
            client_secret=CLIENT_SECRET,
            authorization_response=request.url
        )
        
        user_info_url = "https://graph.microsoft.com/v1.0/me"
        user_response = azure.get(user_info_url, token=token)
        user_info = user_response.json()

        session['user_info'] = user_info
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"[AUTH FOUT] Kan niet inloggen: {e}")
        return render_template('dashboard.html', metingen=[], auth_error="Inloggen mislukt. Controleer Client IDs en Secrets."), 401

@app.route('/logout')
def logout():
    session.pop('user_info', None)
    return redirect(url_for('dashboard'))

@app.route('/api/ingest', methods=['POST'])
def ontvang_metingen():
    try:
        inkomende_data = request.get_json()
        
        if not inkomende_data:
            return jsonify({"error": "Geen data ontvangen"}), 400
            
        hostname = inkomende_data.get('hostname', 'Onbekend')
        timestamp = inkomende_data.get('timestamp', datetime.datetime.now().isoformat())
        metrics = inkomende_data.get('metrics', {})

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

@app.route('/')
@login_required 
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
        container_totaal=container_totaal,
        user_email=session['user_info'].get('mail', 'Gast')
    )

if __name__ == '__main__':
    if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID]):
        print("[FATALE FOUT] Entra ID Omgevingsvariabelen zijn niet geconfigureerd. Kan niet starten zonder deze.")
    else:
        database_klaarmaken()
        print("[SERVER] API en WEB Frontend starten op poort 5000 (Beveiligd)...")
        app.run(host='0.0.0.0', port=5000)