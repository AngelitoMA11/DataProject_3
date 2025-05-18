import json
import os
import httpx
import urllib.parse
import pandas as pd
from google.cloud import bigquery
import functions_framework
import google.cloud.logging
import logging
import traceback

# Configuración
PROJECT_ID = os.getenv("PROJECT_ID")
DATASET = os.getenv("DATASET")
TABLE = os.getenv("TABLE")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
CAR_HOST = "booking-com18.p.rapidapi.com"
CAR_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": CAR_HOST
}
DEFAULT_RATE = float(os.getenv("USD_TO_EUR_RATE", "0.9"))
ENDPOINT_BASE = os.getenv("API_DATA_URL")
ENDPOINT_COCHES_LIMPIOS = f"{ENDPOINT_BASE}/coches/limpios"

# Inicializar cliente de logging
client_logging = google.cloud.logging.Client()
client_logging.setup_logging()

def obtener_pickup_ids(ciudad_destino: str) -> list:
    try:
        with httpx.Client() as client:
            query = urllib.parse.quote(ciudad_destino)
            url = f"https://{CAR_HOST}/car/auto-complete?query={query}"
            resp = client.get(url, headers=CAR_HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            airport_ids = [item.get("id") for item in data if item.get("type", "").lower() == "airport"]
            if not airport_ids:
                raise ValueError(f"No se encontraron aeropuertos para {ciudad_destino}")
            return airport_ids
    except Exception as e:
        logging.error(f"Error in obtener_pickup_ids: {e}")
        return [] # Return empty list in case of error

def procesar_alquileres(data, ciudad, rate=DEFAULT_RATE):
    registros = []
    resultados = data.get('data', {}).get('search_results', [])
    for res in resultados:
        proveedor = res.get('content', {}).get('supplier', {}).get('name', '')
        modelo = res.get('vehicle_info', {}).get('v_name', '')
        label = res.get('vehicle_info', {}).get('label', '')
        categoria = label.split(' with')[0] if label else None
        asientos = res.get('vehicle_info', {}).get('seats')
        transmision = None
        for spec in res.get('content', {}).get('vehicleSpecs', []):
            if spec.get('icon', '').startswith("TRANSMISSION_"):
                transmision = spec.get('text')
                break
        pr = res.get('pricing_info', {}) or {}
        raw = pr.get('drive_away_price') if pr.get('drive_away_price') is not None else pr.get('price')
        try:
            usd = float(raw or 0)
        except (ValueError, TypeError):
            usd = 0.0
        precio = round(usd * rate, 2)
        registros.append({
            'Ciudad': ciudad,
            'Compañía': proveedor,
            'Vehículo': modelo,
            'Categoría': categoria,
            'Asientos': asientos,
            'Transmisión': transmision,
            'Precio': precio
        })
    return registros

def preparar_dataframe(registros):
    df = pd.DataFrame(registros)
    if df.empty:
        return df
    df['Asientos'] = df['Asientos'] = df['Asientos'].apply(extraer_asientos)
    df['Precio'] = df['Precio'].fillna(0.0)
    for col in ['Ciudad', 'Compañía', 'Vehículo', 'Categoría', 'Transmisión']:
        df[col] = df[col].fillna('').astype(str)
    return df

def extraer_asientos(valor):
    try:
        if isinstance(valor, (int, float)):
            return int(valor)
        if isinstance(valor, str):
            partes = [int(p) for p in valor.split("+") if p.isdigit()]
            return sum(partes)
    except:
        pass
    return 0

def insertar_bigquery(df):
    try:
        if df.empty:
            return
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"
        job = client.load_table_from_dataframe(df, table_id)
        job.result()
    except Exception as e:
        logging.exception("Error al insertar en BigQuery")

@functions_framework.http
def buscar_coches(request):
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            logging.error("Cuerpo JSON no válido o ausente.")
            return {"error": "No se proporcionó un cuerpo JSON válido"}
    except Exception as e:
        logging.exception("Error al obtener el JSON de la solicitud.")
        return {"error": f"Error al procesar la solicitud: {str(e)}"}

    try:
        if not all(key in request_json for key in ["ciudad_destino", "fecha_salida", "fecha_vuelta"]):
            logging.error("Faltan datos obligatorios para la búsqueda de coches.")
            return {"error": "Faltan datos obligatorios para la búsqueda de coches"}

        ciudad = request_json["ciudad_destino"]
        fecha_salida = request_json["fecha_salida"]
        fecha_vuelta = request_json["fecha_vuelta"]
        pickup_ids = obtener_pickup_ids(ciudad)
        pick_up_date = pd.to_datetime(fecha_salida, dayfirst=True).strftime("%Y-%m-%d")
        drop_off_date = pd.to_datetime(fecha_vuelta, dayfirst=True).strftime("%Y-%m-%d")
        pick_up_time = "10:00"
        drop_off_time = "10:00"
        todos_registros = []
        resultados_por_aeropuerto = []

        for pid in pickup_ids:
            params_car = {
                "pickUpId": pid,
                "pickUpDate": pick_up_date,
                "pickUpTime": pick_up_time,
                "dropOffDate": drop_off_date,
                "dropOffTime": drop_off_time
            }
            url_car = f"https://{CAR_HOST}/car/search"
            try:
                with httpx.Client() as client:
                    resp_car = client.get(url_car, headers=CAR_HEADERS, params=params_car, timeout=60)
                    resp_car.raise_for_status()
                    data_coches = resp_car.json()
                    registros = procesar_alquileres(data_coches, ciudad)
                    todos_registros.extend(registros)
                    resultados_por_aeropuerto.append({
                        "pickUpId": pid,
                        "resultados": data_coches
                    })
            except Exception as e:
                logging.error(f"Error fetching car data for pickup ID {pid}: {e}")
                # Consider adding an empty list or a default structure to avoid further errors
                resultados_por_aeropuerto.append({
                    "pickUpId": pid,
                    "resultados": {"data": {"search_results": []}}  # Ensure structure is correct
                })

        df = preparar_dataframe(todos_registros)
        insertar_bigquery(df)
        # Añadir esta línea para incluir los resultados en la respuesta HTTP
        resultados_json = df.to_dict(orient="records")

        try:
            if not df.empty:
                headers = {"Content-Type": "application/json"}
                payload = df.to_dict(orient="records")
                with httpx.Client() as client:
                    client.post(ENDPOINT_COCHES_LIMPIOS, headers=headers, json=payload)
        except Exception as e:
            logging.warning(f"No se pudo enviar a /coches/limpios: {str(e)}")

        return {
            "ciudad_destino_aeropuerto": ciudad,
            "fuente": "booking",
            "resultados_por_aeropuerto": resultados_por_aeropuerto,
            "procesados": len(todos_registros),
            "resultados": resultados_json 
        }

    except Exception as e:
        logging.exception("Fallo general en la ejecución de buscar_coches")
        return {"error": str(e)}
