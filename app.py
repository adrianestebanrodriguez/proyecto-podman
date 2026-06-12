from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import json
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuración de Redis
redis_url = os.environ.get('REDIS_URL')
if not redis_url:
    raise ValueError("La variable de entorno REDIS_URL no está configurada")

db = redis.from_url(redis_url, decode_responses=True)
print("Conexión a Redis establecida correctamente", flush=True)

def sincronizar_con_google(nota_texto, fecha_str):
    print(f"DEBUG: El frontend envió esta fecha: '{fecha_str}'", flush=True)
    
    token_str = os.environ.get('GOOGLE_TOKEN_JSON')
    if not token_str:
        print("Error: GOOGLE_TOKEN_JSON no configurado", flush=True)
        return

    with open('temp_token.json', 'w') as f:
        f.write(token_str)
    
    creds = Credentials.from_authorized_user_file('temp_token.json', ['https://www.googleapis.com/auth/calendar'])
    service = build('calendar', 'v3', credentials=creds)
    
    # PROCESAMIENTO ESTRICTO DE FECHA
    try:
        # El formato esperado es 'DD/MM/YYYY, HH:MM'
        # 1. Separamos fecha de hora
        solo_fecha = fecha_str.split(',')[0].strip() # '13/06/2026'
        # 2. Separamos día, mes y año
        partes = solo_fecha.split('/') # ['13', '06', '2026']
        
        # 3. Construimos YYYY-MM-DD estrictamente
        fecha_formateada = f"{partes[2]}-{partes[1]}-{partes[0]}"
        print(f"DEBUG: Fecha procesada para Google: {fecha_formateada}", flush=True)
    except Exception as e:
        # Si algo falla, NO enviamos a Google para evitar errores de calendario
        print(f"Error crítico procesando fecha: {e}", flush=True)
        raise ValueError(f"Formato de fecha inválido recibido: {fecha_str}")

    event = {
        'summary': 'Planeador: ' + nota_texto,
        'start': {'date': fecha_formateada},
        'end': {'date': fecha_formateada},
    }
    
    print(f"Enviando evento a Google: {event}", flush=True)
    event_result = service.events().insert(calendarId='primary', body=event).execute()
    print(f"RESPUESTA DE GOOGLE: {event_result.get('id')}", flush=True)

# --- RUTAS DE LA API (Sin cambios) ---
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
            try:
                print("Intentando sincronizar con Google...", flush=True) 
                sincronizar_con_google(nueva_nota_obj.get('texto'), nueva_nota_obj.get('fecha'))
            except Exception as e:
                print(f"!!! ERROR FATAL: {e}", flush=True)
            return jsonify({"status": "success"}), 201
        return jsonify({"error": "Estructura invalida"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... resto de rutas (PUT, DELETE, BORRAR) se mantienen igual ...

if __name__ == '__main__':
    print(f"--- Servidor iniciado a las {datetime.now()} ---", flush=True)
    app.run(host='0.0.0.0', port=5000, debug=False)