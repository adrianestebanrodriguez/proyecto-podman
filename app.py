from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

redis_host = os.environ.get('REDIS_HOST', 'localhost')
db = redis.Redis(host=redis_host, port=6379, decode_responses=True)

@app.route('/notas', methods=['GET'])
def obtener_notas():
    try:
        raw_notas = db.lrange('mis_notas', 0, -1)
        notas_procesadas = []
        for nota in raw_notas:
            try:
                notas_procesadas.append(json.loads(nota))
            except Exception:
                notas_procesadas.append({
                    "id": "antigua",
                    "texto": nota,
                    "fecha": "Fecha no registrada",
                    "categoria": "personal"
                })
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
            return jsonify({"status": "success"}), 201
        return jsonify({"error": "Estructura invalida"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# NUEVA RUTA: EDITAR NOTA EXISTENTE (Busca por ID y reemplaza el contenido)
@app.route('/notas/<string:nota_id>', methods=['PUT'])
def editar_nota(nota_id):
    try:
        datos = request.get_json()
        nota_actualizada = datos.get('nota', None)
        if not nota_actualizada:
            return jsonify({"error": "Datos invalidos"}), 400

        raw_notas = db.lrange('mis_notas', 0, -1)
        for i, nota_string in enumerate(raw_notas):
            try:
                nota_data = json.loads(nota_string)
                if nota_data.get('id') == nota_id:
                    # Reemplazamos exactamente en el índice de la lista de Redis
                    db.lset('mis_notas', i, json.dumps(nota_actualizada))
                    return jsonify({"status": "success", "message": "Nota actualizada"}), 200
            except Exception:
                continue
        return jsonify({"status": "error", "message": "Nota no encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notas/<string:nota_id>', methods=['DELETE'])
def eliminar_nota_individual(nota_id):
    try:
        raw_notas = db.lrange('mis_notas', 0, -1)
        for nota_string in raw_notas:
            try:
                nota_data = json.loads(nota_string)
                if nota_data.get('id') == nota_id:
                    db.lrem('mis_notas', 1, nota_string)
                    return jsonify({"status": "success"}), 200
            except Exception:
                continue
        return jsonify({"status": "error"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/borrar', methods=['POST'])
def borrar_todas_las_notas():
    try:
        db.delete('mis_notas')
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)