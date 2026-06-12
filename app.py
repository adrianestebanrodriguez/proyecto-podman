from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import json
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

redis_url = os.environ.get('REDIS_URL')
if not redis_url:
    raise ValueError("La variable de entorno REDIS_URL no está configurada")

db = redis.from_url(redis_url, decode_responses=True)

def sincronizar_con_google(nota_texto, fecha_str):
    try:
        # 1. Parseo de fecha
        solo_fecha = fecha_str.split(',')[0].strip()
        partes = solo_fecha.split('/')
        fecha_formateada = f"{partes[2]}-{partes[1]}-{partes[0]}"
        
        # 2. Configuración API
        token_str = os.environ.get('GOOGLE_TOKEN_JSON')
        if not token_str: return
        
        with open('temp_token.json', 'w') as f: f.write(token_str)
        creds = Credentials.from_authorized_user_file('temp_token.json', ['https://www.googleapis.com/auth/calendar'])
        service = build('calendar', 'v3', credentials=creds)
        
        # 3. Envío
        event = {'summary': 'Planeador: ' + nota_texto, 'start': {'date': fecha_formateada}, 'end': {'date': fecha_formateada}}
        service.events().insert(calendarId='primary', body=event).execute()
    except Exception as e:
        print(f"Error en sincronización (no crítico): {e}", flush=True)

@app.route('/notas', methods=['GET'])
def obtener_notas():
    try:
        raw_notas = db.lrange('mis_notas', 0, -1)
        return jsonify([json.loads(n) for n in raw_notas]), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/notas', methods=['POST'])
def guardar_nota():
    try:
        datos = request.get_json()
        nueva_nota = datos.get('nota')
        if nueva_nota:
            db.rpush('mis_notas', json.dumps(nueva_nota))
            sincronizar_con_google(nueva_nota.get('texto'), nueva_nota.get('fecha'))
            return jsonify({"status": "success"}), 201
        return jsonify({"error": "Datos inválidos"}), 400
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/notas/<string:nota_id>', methods=['PUT'])
def editar_nota(nota_id):
    try:
        datos = request.get_json()
        nueva_data = datos.get('nota')
        raw_notas = db.lrange('mis_notas', 0, -1)
        for i, n_str in enumerate(raw_notas):
            if json.loads(n_str).get('id') == nota_id:
                db.lset('mis_notas', i, json.dumps(nueva_data))
                return jsonify({"status": "success"}), 200
        return jsonify({"message": "No encontrada"}), 404
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/notas/<string:nota_id>', methods=['DELETE'])
def eliminar_nota(nota_id):
    try:
        raw_notas = db.lrange('mis_notas', 0, -1)
        for n_str in raw_notas:
            if json.loads(n_str).get('id') == nota_id:
                db.lrem('mis_notas', 1, n_str)
                return jsonify({"status": "success"}), 200
        return jsonify({"message": "No encontrada"}), 404
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/borrar', methods=['POST'])
def borrar_todas():
    db.delete('mis_notas')
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)