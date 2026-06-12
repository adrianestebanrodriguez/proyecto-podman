FROM python:3.11-slim

WORKDIR /app

# Instalamos las librerías necesarias
RUN pip install flask flask-cors redis

# Copiamos nuestro script al contenedor
COPY app.py .

# Exponemos el puerto de la API
EXPOSE 5000

CMD ["python", "app.py"]