import requests

nota_de_prueba = {
    "nota": {
        "id": "test123",
        "texto": "¡Hola, Google Calendar!",
        "fecha": "2026-06-12"
    }
}

try:
    response = requests.post('http://localhost:5000/notas', json=nota_de_prueba)
    print("Respuesta del servidor:")
    print(response.json())
except Exception as e:
    print(f"Error al conectar: {e}")