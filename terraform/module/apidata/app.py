import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

FUNC_VUELOS_URL = os.environ.get("FUNC_VUELOS_URL")
FUNC_HOTELES_URL = os.environ.get("FUNC_HOTELES_URL")
FUNC_COCHES_URL = os.environ.get("FUNC_COCHES_URL")

@app.route('/vuelos', methods=['POST'])
def activar_funcion_vuelos():
    response = requests.post(os.environ["FUNC_VUELOS_URL"], json=request.get_json())
    return jsonify({"status": response.status_code}), response.status_code

@app.route('/hoteles', methods=['POST'])
def activar_funcion_hoteles():
    response = requests.post(os.environ["FUNC_HOTELES_URL"], json=request.get_json())
    return jsonify({"status": response.status_code}), response.status_code

@app.route('/coches', methods=['POST'])
def activar_funcion_coches():
    response = requests.post(os.environ["FUNC_COCHES_URL"], json=request.get_json())
    return jsonify({"status": response.status_code}), response.status_code

@app.route('/vuelos/limpios', methods=['POST'])
def recibir_vuelos_limpios():
    data = request.get_json()
    print("🛫 Datos de vuelos limpios recibidos:", data)
    return '', 204

@app.route('/hoteles/limpios', methods=['POST'])
def recibir_hoteles_limpios():
    data = request.get_json()
    print("🏨 Datos de hoteles limpios recibidos:", data)
    return '', 204

@app.route('/coches/limpios', methods=['POST'])
def recibir_coches_limpios():
    data = request.get_json()
    print("🚗 Datos de coches limpios recibidos:", data)
    return '', 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
