import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

FUNC_VUELOS_URL = os.environ.get("FUNC_VUELOS_URL")
FUNC_HOTELES_URL = os.environ.get("FUNC_HOTELES_URL")
FUNC_COCHES_URL = os.environ.get("FUNC_COCHES_URL")

@app.route('/vuelos', methods=['POST'])
def handle_vuelos():
    data = request.get_json()
    if data.get("respuesta") == True:
        print("🛫 Datos de vuelos limpios recibidos:", data)
        return '', 204
    else:
        response = requests.post(FUNC_VUELOS_URL, json=data)
        return jsonify(response.json()), response.status_code

@app.route('/hoteles', methods=['POST'])
def handle_hoteles():
    data = request.get_json()
    if data.get("respuesta") == True:
        print("🏨 Datos de hoteles limpios recibidos:", data)
        return '', 204
    else:
        response = requests.post(FUNC_HOTELES_URL, json=data)
        return jsonify(response.json()), response.status_code

@app.route('/coches', methods=['POST'])
def handle_coches():
    data = request.get_json()
    if data.get("respuesta") == True:
        print("🚗 Datos de coches limpios recibidos:", data)
        return '', 204
    else:
        response = requests.post(FUNC_COCHES_URL, json=data)
        return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
