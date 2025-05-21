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


@app.route('/registro', methods=['POST'])
def handle_usuarios():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['id', 'usuario', 'correo', 'PWD']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"Faltan campos requeridos: {', '.join(missing_fields)}"
        }), 400

    client = bigquery.Client()
    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE_USUARIOS}"

    # Check if user already exists
    check_query = f"""
    SELECT id FROM `{table_id}`
    WHERE id = @id OR usuario = @usuario OR correo = @correo
    LIMIT 1
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("id", "STRING", data['id']),
            bigquery.ScalarQueryParameter("usuario", "STRING", data['usuario']),
            bigquery.ScalarQueryParameter("correo", "STRING", data['correo'])
        ]
    )
    
    existing_user = list(client.query(check_query, job_config=job_config))
    if existing_user:
        return jsonify({
            "status": "error",
            "message": "Ya existe un usuario con ese ID, nombre de usuario o correo"
        }), 409

    # Insert new user
    errors = client.insert_rows_json(table_id, [data])
    if errors:
        return jsonify({
            "status": "error",
            "errors": errors
        }), 500
    else:
        return jsonify({
            "status": "success",
            "message": "Usuario registrado exitosamente",
            "user_id": data['id']
        }), 201

@app.route('/viajes', methods=['POST', 'GET'])
def handle_viajes():
    client = bigquery.Client()
    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE_VIAJES}"

    if request.method == 'POST':
        data = request.get_json()
        
        # Validate required user field
        if not data or 'user' not in data:
            return jsonify({
                "status": "error",
                "message": "El campo 'user' es requerido"
            }), 400
            
        # Validate user exists in usuarios table
        user_query = f"""
        SELECT usuario FROM `{PROJECT_ID}.{DATASET}.{TABLE_USUARIOS}`
        WHERE usuario = @user
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user", "STRING", data['user'])
            ]
        )
        
        user_result = list(client.query(user_query, job_config=job_config))
        if not user_result:
            return jsonify({
                "status": "error",
                "message": "Usuario no encontrado"
            }), 404

        errors = client.insert_rows_json(table_id, [data])
        if errors:
            print("Errores al insertar viaje en BigQuery:", errors)
            return jsonify({"status": "error", "errors": errors}), 500
        else:
            print("✅ Viaje insertado en BigQuery:", data)
            return jsonify({"status": "success"}), 200

    elif request.method == 'GET':
        user = request.args.get('user')
        if not user:
            return jsonify({
                "status": "error",
                "message": "El parámetro 'user' es requerido"
            }), 400
            
        query = f"""
        SELECT * FROM `{table_id}`
        WHERE user = @user
        ORDER BY thread_id DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user", "STRING", user)
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = [dict(row) for row in query_job]
        return jsonify(results), 200

@app.route('/login', methods=['POST'])
def handle_login():
    data = request.get_json()
    if not data or 'usuario' not in data or 'pwd' not in data:
        return jsonify({"status": "error", "message": "Se requieren usuario y contraseña"}), 400

    client = bigquery.Client()
    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE_USUARIOS}"
    
    # Query to check credentials
    query = f"""
    SELECT * FROM `{table_id}`
    WHERE usuario = @usuario AND pwd = @pwd
    LIMIT 1
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("usuario", "STRING", data['usuario']),
            bigquery.ScalarQueryParameter("pwd", "STRING", data['pwd'])
        ]
    )
    
    query_job = client.query(query, job_config=job_config)
    results = list(query_job)
    
    if results:
        return jsonify({
            "status": "success",
            "message": "Login exitoso",
            "user": dict(results[0])
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Credenciales inválidas"
        }), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
