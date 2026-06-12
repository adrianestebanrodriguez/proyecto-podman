from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import json
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

import os
import redis

# Leemos la URL, si no está, lanzamos un error claro
redis_url = os.environ.get('redis://red-d8lmg20js32c73b06th0:6379')

if not redis_url:
    raise ValueError("La variable de entorno REDIS_URL no está configurada")

# Conectamos eliminando parámetros extra por si acaso
db = redis.from_url(redis_url, decode_responses=True)
print("Conexión a Redis establecida correctamente", flush=True)

def sincronizar_con_google(nota_texto, fecha):
    if not os.path.exists('token.json'):
        print("Error: token.json no encontrado", flush=True)
        return
    
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/calendar'])
    service = build('calendar', 'v3', credentials=creds)
    
    event = {
        'summary': 'Planeador: ' + nota_texto,
        'start': {'date': fecha},
        'end': {'date': fecha},
    }
    
    # Capturamos la respuesta completa aquí
    print(f"Enviando evento a Google: {event}", flush=True)
    try:
        event_result = service.events().insert(calendarId='adrianalvarezr@gmail.com', body=event).execute()
        print(f"RESPUESTA DE GOOGLE: {event_result}", flush=True)
    except Exception as e:
        print(f"ERROR DETALLADO DE LA API: {e}", flush=True)
        raise e # Esto hará que el bloque try/except de guardar_nota capture el error

# --- RUTAS DE LA API ---

@app.route('/notas', methods=['GET'])
def obtener_notas():
    try:
        raw_notas = db.lrange('mis_notas', 0, -1)
        notas_procesadas = [json.loads(nota) for nota in raw_notas]
        return jsonify(notas_procesadas), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notas', methods=['POST'])
def guardar_nota():
    try:
        datos = request.get_json()
        nueva_nota_obj = datos.get('nota', None)
        if nueva_nota_obj:
            db.rpush('mis_notas', json.dumps(nueva_nota_obj))
            
            # Sincronización forzada con 'flush=True' para verla en terminal
            try:
                print("Intentando sincronizar con Google...", flush=True) 
                sincronizar_con_google(nueva_nota_obj.get('texto'), nueva_nota_obj.get('fecha'))
                print("Sincronización finalizada.", flush=True) 
            except Exception as e:
                print(f"!!! ERROR FATAL EN SINCRONIZACION: {e}", flush=True)
            
            return jsonify({"status": "success"}), 201
        return jsonify({"error": "Estructura invalida"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notas/<string:nota_id>', methods=['PUT'])
def editar_nota(nota_id):
    try:
        datos = request.get_json()
        nota_actualizada = datos.get('nota', None)
        raw_notas = db.lrange('mis_notas', 0, -1)
        for i, nota_string in enumerate(raw_notas):
            nota_data = json.loads(nota_string)
            if nota_data.get('id') == nota_id:
                db.lset('mis_notas', i, json.dumps(nota_actualizada))
                return jsonify({"status": "success"}), 200
        return jsonify({"status": "error", "message": "No encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notas/<string:nota_id>', methods=['DELETE'])
def eliminar_nota_individual(nota_id):
    try:
        raw_notas = db.lrange('mis_notas', 0, -1)
        for nota_string in raw_notas:
            nota_data = json.loads(nota_string)
            if nota_data.get('id') == nota_id:
                db.lrem('mis_notas', 1, nota_string)
                return jsonify({"status": "success"}), 200
        return jsonify({"status": "error", "message": "No encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/borrar', methods=['POST'])
def borrar_todas_las_notas():
    db.delete('mis_notas')
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    import datetime
    print(f"--- Servidor iniciado a las {datetime.datetime.now()} ---", flush=True)
    app.run(host='0.0.0.0', port=5005, debug=False) # debug=False es importante