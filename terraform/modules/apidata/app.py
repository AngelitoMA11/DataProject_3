import os
import requests
from flask import Flask, request, jsonify
from google.cloud import bigquery

app = Flask(__name__)

FUNC_VUELOS_URL = os.environ.get("FUNC_VUELOS_URL")
FUNC_HOTELES_URL = os.environ.get("FUNC_HOTELES_URL")
FUNC_COCHES_URL = os.environ.get("FUNC_COCHES_URL")
PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET = os.environ.get("DATASET")
TABLE_USUARIOS = os.environ.get("TABLE_USUARIOS")
TABLE_VIAJES = os.environ.get("TABLE_VIAJES")

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

@app.route('/usuarios', methods=['POST'])
def handle_usuarios():
    data = request.get_json()
    client = bigquery.Client()

    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE_USUARIOS}"

    errors = client.insert_rows_json(table_id, [data])
    if errors:
        print("Errores al insertar en BigQuery:", errors)
        return jsonify({"status": "error", "errors": errors}), 500
    else:
        print("✅ Usuario insertado en BigQuery:", data)
        return jsonify({"status": "success"}), 200

@app.route('/viajes', methods=['POST', 'GET'])
def handle_viajes():
    client = bigquery.Client()
    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE_VIAJES}"

    if request.method == 'POST':
        data = request.get_json()
        errors = client.insert_rows_json(table_id, [data])
        if errors:
            print("Errores al insertar viaje en BigQuery:", errors)
            return jsonify({"status": "error", "errors": errors}), 500
        else:
            print("✅ Viaje insertado en BigQuery:", data)
            return jsonify({"status": "success"}), 200

    elif request.method == 'GET':
        query = f"SELECT * FROM `{table_id}`"
        query_job = client.query(query)
        results = [dict(row) for row in query_job]
        return jsonify(results), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
