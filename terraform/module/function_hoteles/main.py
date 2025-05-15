import json
import os
import httpx
import urllib.parse
from google.cloud import bigquery
import functions_framework
import google.cloud.logging
import logging
import traceback

# Configuración
PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET = os.environ.get("DATASET")
TABLE = os.environ.get("TABLE")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
FLIGHT_HOTEL_HOST = "booking-com15.p.rapidapi.com"
FLIGHT_HOTEL_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": FLIGHT_HOTEL_HOST
}
ENDPOINT_BASE = os.environ.get("API_DATA_URL")
ENDPOINT_HOTELES_LIMPIOS = f"{ENDPOINT_BASE}/hoteles/limpios"

# Inicializar cliente de logging
client_logging = google.cloud.logging.Client()
client_logging.setup_logging()

def extract_safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def extract_safe_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def extract_safe_string(value, default=""):
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default

async def obtener_id_destino_hotel(ciudad: str):
    async with httpx.AsyncClient() as client:
        query = urllib.parse.quote(ciudad)
        url = f"https://{FLIGHT_HOTEL_HOST}/api/v1/hotels/searchDestination?query={query}"
        resp = await client.get(url, headers=FLIGHT_HOTEL_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            raise ValueError(f"No se encontró ningún destino para '{ciudad}'")
        destino = max(data, key=lambda d: d.get("hotels", 0))
        return destino["dest_id"], destino["search_type"]

def procesar_hoteles(data):
    hoteles_procesados = []
    try:
        hoteles = []
        if 'data' in data and 'hotels' in data['data']:
            hoteles = data['data']['hotels']
        if not hoteles:
            return []
        for hotel in hoteles:
            hotel_procesado = process_hotel_data(hotel, data)
            if hotel_procesado:
                hoteles_procesados.append(hotel_procesado)
    except Exception as e:
        logging.exception("Error al procesar hoteles")
    return hoteles_procesados

def process_hotel_data(hotel, parent_data=None):
    try:
        property_data = hotel.get('property', {})
        price_info = property_data.get('priceBreakdown', {}).get('grossPrice', {})
        price = round(extract_safe_float(price_info.get('value', 0)), 2)
        return {
            "nombre": extract_safe_string(property_data.get('name', '')),
            "direccion": extract_safe_string(hotel.get('accessibilityLabel', '').split('\n')[0] if hotel.get('accessibilityLabel') else ''),
            "ciudad": extract_safe_string(property_data.get('wishlistName', '')),
            "clasificacion": extract_safe_float(property_data.get('qualityClass', 0)),
            "puntuacion_resenas": extract_safe_float(property_data.get('reviewScore', 0)),
            "numero_resenas": extract_safe_int(property_data.get('reviewCount', 0)),
            "precio": price,
            "moneda": "EUR",
            "fecha_entrada": extract_safe_string(property_data.get('checkinDate', '')),
            "fecha_salida": extract_safe_string(property_data.get('checkoutDate', '')),
            "codigo_pais": extract_safe_string(property_data.get('countryCode', '')),
            "clase_propiedad": extract_safe_int(property_data.get('propertyClass', 0)),
            "valoracion_texto": extract_safe_string(property_data.get('reviewScoreWord', ''))
        }
    except Exception as e:
        logging.warning(f"Error al procesar hotel individual: {e}")
        return None

def insertar_en_bigquery(hoteles_procesados):
    try:
        if not hoteles_procesados:
            return False
        client = bigquery.Client(project=PROJECT_ID)
        tabla_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"
        errors = client.insert_rows_json(tabla_id, hoteles_procesados)
        if errors:
            logging.warning(f"Errores al insertar datos en BigQuery: {errors}")
            return False
        return True
    except Exception as e:
        logging.exception("Error al insertar en BigQuery")
        return False

@functions_framework.http
async def buscar_hoteles(request):
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            logging.error("Cuerpo JSON no válido o ausente.")
            return {"error": "No se proporcionó un cuerpo JSON válido"}
    except Exception as e:
        logging.exception("Error al obtener el JSON de la solicitud.")
        return {"error": f"Error al procesar la solicitud: {str(e)}"}

    try:
        if not all(key in request_json for key in ["ciudad_destino_vacaciones", "fecha_salida", "fecha_vuelta"]):
            logging.error("Faltan campos obligatorios en el JSON de entrada.")
            return {"error": "Faltan datos obligatorios para la búsqueda de hoteles"}

        dest_id, search_type = await obtener_id_destino_hotel(request_json["ciudad_destino_vacaciones"])
        params_hotel = {
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": "-".join(reversed(request_json["fecha_salida"].split("-"))),
            "departure_date": "-".join(reversed(request_json["fecha_vuelta"].split("-"))),
            "room_qty": str(request_json.get("rooms", 1))
        }

        url_hotel = f"https://{FLIGHT_HOTEL_HOST}/api/v1/hotels/searchHotels"
        async with httpx.AsyncClient() as client:
            resp_hotel = await client.get(url_hotel, headers=FLIGHT_HOTEL_HEADERS, params=params_hotel, timeout=20)
            resp_hotel.raise_for_status()
            data_hoteles = resp_hotel.json()

        hoteles_procesados = procesar_hoteles(data_hoteles)
        insertar_en_bigquery(hoteles_procesados)

        try:
            if hoteles_procesados:
                headers = {"Content-Type": "application/json"}
                async with httpx.AsyncClient() as client:
                    await client.post(ENDPOINT_HOTELES_LIMPIOS, headers=headers, json=hoteles_procesados)
        except Exception as e:
            logging.warning(f"No se pudo enviar a /hoteles/limpios: {str(e)}")

        return {"fuente": "booking", "resultados": data_hoteles, "procesados": len(hoteles_procesados)}

    except Exception as e:
        logging.exception("Fallo general en la ejecución de buscar_hoteles")
        return {"error": str(e)}
