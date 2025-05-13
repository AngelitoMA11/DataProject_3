import json
import os
import httpx
import urllib.parse
from google.cloud import bigquery
import functions_framework

# Configuración
PROJECT_ID = os.getenv("PROJECT_ID", "dataproject3-458310")
DATASET = os.getenv("DATASET", "app_viajes")
TABLE = os.getenv("TABLE", "hoteles")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "9630d11b3dmshc21bd0426b9a53cp153093jsn46cfb50160a1")
FLIGHT_HOTEL_HOST = "booking-com15.p.rapidapi.com"
FLIGHT_HOTEL_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": FLIGHT_HOTEL_HOST
}

def extract_safe_float(value, default=0.0):
    """Extrae un valor flotante de manera segura"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def extract_safe_int(value, default=0):
    """Extrae un valor entero de manera segura"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def extract_safe_string(value, default=""):
    """Extrae un valor string de manera segura"""
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default

async def obtener_id_destino_hotel(ciudad: str):
    """Busca el ID del destino para hoteles"""
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
    """
    Procesa los datos de hoteles recibidos y devuelve una lista de registros procesados
    """
    hoteles_procesados = []
    
    try:
        # Extraer la lista de hoteles del mensaje
        hoteles = []
        if 'data' in data and 'hotels' in data['data']:
            hoteles = data['data']['hotels']
        
        if not hoteles:
            return []
        
        # Procesar los datos de los hoteles
        for hotel in hoteles:
            hotel_procesado = process_hotel_data(hotel, data)
            if hotel_procesado:
                hoteles_procesados.append(hotel_procesado)
                
    except Exception as e:
        print(f"Error al procesar hoteles: {e}")
        
    return hoteles_procesados

def process_hotel_data(hotel, parent_data=None):
    """
    Procesa los datos de un hotel individual y extrae la información relevante
    """
    try:
        # Extraer datos de la propiedad (si existe)
        property_data = hotel.get('property', {})
        
        # Extraer información de precios
        price_info = property_data.get('priceBreakdown', {}).get('grossPrice', {})
        price = extract_safe_float(price_info.get('value', 0))
        
        # Redondear el precio a 2 decimales
        price = round(price, 2)
        
        # Crear el objeto de datos procesados
        hotel_procesado = {
            "nombre": extract_safe_string(property_data.get('name', '')),
            "direccion": extract_safe_string(hotel.get('accessibilityLabel', '').split('\n')[0] if hotel.get('accessibilityLabel') else ''),
            "ciudad": extract_safe_string(property_data.get('wishlistName', '')),
            "clasificacion": extract_safe_float(property_data.get('qualityClass', 0)),
            "puntuacion_resenas": extract_safe_float(property_data.get('reviewScore', 0)),
            "numero_resenas": extract_safe_int(property_data.get('reviewCount', 0)),
            "precio": price,
            "moneda": "EUR",  # Fijamos la moneda como EUR
            "fecha_entrada": extract_safe_string(property_data.get('checkinDate', '')),
            "fecha_salida": extract_safe_string(property_data.get('checkoutDate', '')),
            "codigo_pais": extract_safe_string(property_data.get('countryCode', '')),
            "clase_propiedad": extract_safe_int(property_data.get('propertyClass', 0)),
            "valoracion_texto": extract_safe_string(property_data.get('reviewScoreWord', ''))
        }
        
        return hotel_procesado
        
    except Exception as e:
        print(f"Error al procesar hotel individual: {e}")
        return None

def insertar_en_bigquery(hoteles_procesados):
    """
    Inserta los datos procesados en BigQuery
    """
    try:
        if not hoteles_procesados:
            return False
            
        client = bigquery.Client(project=PROJECT_ID)
        tabla_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"
        
        # Insertar filas
        errors = client.insert_rows_json(tabla_id, hoteles_procesados)
        
        if errors:
            print(f"Se encontraron errores al insertar datos: {errors}")
            return False
        else:
            return True
            
    except Exception as e:
        print(f"Error al insertar en BigQuery: {e}")
        return False

@functions_framework.http
async def buscar_hoteles(request):
    """
    Cloud Function que busca hoteles, procesa datos y guarda en BigQuery
    """
    # Extraer body del request
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return {"error": "No se proporcionó un cuerpo JSON válido"}
    except Exception as e:
        return {"error": f"Error al procesar la solicitud: {str(e)}"}
    
    try:
        # Verificar datos necesarios
        if not all(key in request_json for key in ["ciudad_destino_vacaciones", "fecha_salida", "fecha_vuelta"]):
            return {"error": "Faltan datos obligatorios para la búsqueda de hoteles"}
        
        # Buscar ID de destino
        dest_id, search_type = await obtener_id_destino_hotel(request_json["ciudad_destino_vacaciones"])
        
        # Construir parámetros para búsqueda de hoteles
        params_hotel = {
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": "-".join(reversed(request_json["fecha_salida"].split("-"))),
            "departure_date": "-".join(reversed(request_json["fecha_vuelta"].split("-"))),
            "room_qty": str(request_json.get("rooms", 1))
        }
        
        # Buscar hoteles
        url_hotel = f"https://{FLIGHT_HOTEL_HOST}/api/v1/hotels/searchHotels"
        async with httpx.AsyncClient() as client:
            resp_hotel = await client.get(url_hotel, headers=FLIGHT_HOTEL_HEADERS, params=params_hotel, timeout=20)
            resp_hotel.raise_for_status()
            data_hoteles = resp_hotel.json()
        
        # Procesar los hoteles
        hoteles_procesados = procesar_hoteles(data_hoteles)
        
        # Insertar en BigQuery
        insertar_en_bigquery(hoteles_procesados)
        
        # Devolver resultados para la respuesta
        return {"fuente": "booking", "resultados": data_hoteles, "procesados": len(hoteles_procesados)}
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"error": str(e)}