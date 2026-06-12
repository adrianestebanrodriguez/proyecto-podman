from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import json
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

db = redis.from_url(os.environ.get('REDIS_URL'), decode_responses=True)

def get_service():
    token_str = os.environ.get('GOOGLE_TOKEN_JSON')
    if not token_str: return None
    with open('temp_token.json', 'w') as f: f.write(token_str)
    creds = Credentials.from_authorized_user_file('temp_token.json', ['https://www.googleapis.com/auth/calendar'])
    return build('calendar', 'v3', credentials=creds)

def sincronizar_con_google(nota):
    try:
        service = get_service()
        # Parseo de fecha: '13/06/2026' -> '2026-06-13'
        solo_fecha = nota.get('fecha', '').split(',')[0].strip()
        partes = solo_fecha.split('/')
        fecha_formateada = f"{partes[2]}-{partes[1]}-{partes[0]}"
        
        event = {
            'summary': 'Planeador: ' + nota.get('texto'),
            'start': {'date': fecha_formateada},
            'end': {'date': fecha_formateada},
            'transparency': 'transparent'
        }
        res = service.events().insert(calendarId='primary', body=event).execute()
        return res.get('id') # Retornamos el ID para guardarlo en la nota
    except Exception as e:
        print(f"Error sincronizando con Google: {e}", flush=True)
        return None

@app.route('/notas', methods=['POST'])
def guardar_nota():
    datos = request.get_json()
    nota = datos.get('nota')
    if not nota: return jsonify({"error": "Datos inválidos"}), 400
    
    # Sincronizamos y guardamos el ID en la nota
    google_id = sincronizar_con_google(nota)
    if google_id:
        nota['google_id'] = google_id
    
    db.rpush('mis_notas', json.dumps(nota))
    return jsonify({"status": "success"}), 201

@app.route('/notas/<string:nota_id>', methods=['DELETE'])
def eliminar_nota(nota_id):
    raw_notas = db.lrange('mis_notas', 0, -1)
    for n_str in raw_notas:
        nota = json.loads(n_str)
        if nota.get('id') == nota_id:
            # Si tiene un google_id, lo borramos de Google Calendar
            if 'google_id' in nota:
                try:
                    service = get_service()
                    service.events().delete(calendarId='primary', eventId=nota['google_id']).execute()
                except Exception as e:
                    print(f"Error borrando de Google: {e}", flush=True)
            
            db.lrem('mis_notas', 1, n_str)
            return jsonify({"status": "success"}), 200
    return jsonify({"message": "No encontrada"}), 404

# Las rutas GET, PUT y BORRAR se mantienen igual que las tenías
@app.route('/notas', methods=['GET'])
def obtener_notas():
    try:
        raw_notas = db.lrange('mis_notas', 0, -1)
        return jsonify([json.loads(n) for n in raw_notas]), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/notas/<string:nota_id>', methods=['PUT'])
def editar_nota(nota_id):
    datos = request.get_json()
    nueva_data = datos.get('nota')
    raw_notas = db.lrange('mis_notas', 0, -1)
    for i, n_str in enumerate(raw_notas):
        if json.loads(n_str).get('id') == nota_id:
            db.lset('mis_notas', i, json.dumps(nueva_data))
            return jsonify({"status": "success"}), 200
    return jsonify({"message": "No encontrada"}), 404

@app.route('/borrar', methods=['POST'])
def borrar_todas():
    db.delete('mis_notas')
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)