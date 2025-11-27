from flask import Flask, request, jsonify
import datetime
import pyodbc
import os

app = Flask(__name__)

@app.route('/api/ingest', methods=['POST'])
def ontvang_metingen():
    try:
        inkomende_data = request.get_json()
        
        if not inkomende_data:
            return jsonify({"error": "Geen data ontvangen"}), 400
            
        print(f"\n[API] Nieuwe data ontvangen van: {inkomende_data.get('hostname')}")
        print(f"[API] Inhoud: {inkomende_data}")

        return jsonify({"message": "Data succesvol ontvangen en verwerkt", "status": "success"}), 201

    except Exception as e:
        print(f"[API FOUT] Er ging iets mis: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("[SERVER] API start op poort 5000...")
    app.run(debug=True, port=5000)