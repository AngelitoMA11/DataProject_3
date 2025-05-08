import json
import time
import os
import base64
import logging
from google.cloud import bigquery

# Configuración
PROJECT_ID = os.getenv("PROJECT_ID", "dataproject3-458310")
DATASET = os.getenv("DATASET", "app_viajes")
TABLE = os.getenv("TABLE", "hoteles")

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
            logging.info("No se encontraron hoteles en el mensaje")
            return []
        
        logging.info(f"Se encontraron {len(hoteles)} hoteles para procesar")
        
        # Procesar los datos de los hoteles
        for hotel in hoteles:
            hotel_procesado = process_hotel_data(hotel, data)
            if hotel_procesado:
                hoteles_procesados.append(hotel_procesado)
                
    except Exception as e:
        logging.exception(f"Error al procesar hoteles: {e}")
        
    return hoteles_procesados

def process_hotel_data(hotel, parent_data=None):
    """
    Procesa los datos de un hotel individual y extrae la información relevante
    """
    try:
        # Extraer el ID del hotel
        hotel_id = extract_safe_string(hotel.get('hotel_id', ''))
        
        # Extraer datos de la propiedad (si existe)
        property_data = hotel.get('property', {})
        
        # Extraer información de precios
        price_info = property_data.get('priceBreakdown', {}).get('grossPrice', {})
        price = extract_safe_float(price_info.get('value', 0))
        currency = extract_safe_string(price_info.get('currency', ''))
        
        # Crear el objeto de datos procesados con nombres de columnas en español
        hotel_procesado = {
            "id_hotel": hotel_id,
            "nombre": extract_safe_string(property_data.get('name', '')),
            "direccion": extract_safe_string(hotel.get('accessibilityLabel', '').split('\n')[0] if hotel.get('accessibilityLabel') else ''),
            "ciudad": extract_safe_string(property_data.get('wishlistName', '')),
            "latitud": extract_safe_float(property_data.get('latitude', 0)),
            "longitud": extract_safe_float(property_data.get('longitude', 0)),
            "clasificacion": extract_safe_float(property_data.get('qualityClass', 0)),
            "puntuacion_resenas": extract_safe_float(property_data.get('reviewScore', 0)),
            "numero_resenas": extract_safe_int(property_data.get('reviewCount', 0)),
            "precio": price,
            "moneda": currency,
            "fecha_entrada": extract_safe_string(property_data.get('checkinDate', '')),
            "fecha_salida": extract_safe_string(property_data.get('checkoutDate', '')),
            "codigo_pais": extract_safe_string(property_data.get('countryCode', '')),
            "clase_propiedad": extract_safe_int(property_data.get('propertyClass', 0)),
            "valoracion_texto": extract_safe_string(property_data.get('reviewScoreWord', '')),
            "id_foto_principal": extract_safe_string(property_data.get('mainPhotoId', '')),
            "url_foto": extract_safe_string(property_data.get('photoUrls', [''])[0] if property_data.get('photoUrls') else ''),
            "timestamp": parent_data.get('timestamp', int(time.time() * 1000)) if parent_data else int(time.time() * 1000)
        }
        
        return hotel_procesado
        
    except Exception as e:
        logging.exception(f"Error al procesar hotel individual: {e}")
        return None

def insertar_en_bigquery(hoteles_procesados):
    """
    Inserta los datos procesados en BigQuery
    """
    try:
        if not hoteles_procesados:
            logging.info("No hay datos para insertar en BigQuery")
            return False
            
        client = bigquery.Client(project=PROJECT_ID)
        tabla_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"
        
        # Insertar filas
        errors = client.insert_rows_json(tabla_id, hoteles_procesados)
        
        if errors:
            logging.error(f"Se encontraron errores al insertar datos: {errors}")
            return False
        else:
            logging.info(f"Insertados {len(hoteles_procesados)} hoteles en BigQuery correctamente")
            return True
            
    except Exception as e:
        logging.exception(f"Error al insertar en BigQuery: {e}")
        return False

def limpieza_hoteles(event, context):
    """
    Función de entrada para Cloud Functions, se activa cuando un mensaje
    llega a la topic de Pub/Sub
    """
    logging.info("📥 Evento recibido en limpieza_hoteles: %s", event)
    try:
        # Decodificar el mensaje de Pub/Sub (base64)
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        data = json.loads(pubsub_message)
        
        # Procesar los datos de hoteles
        hoteles_procesados = procesar_hoteles(data)
        
        # Si hay datos procesados, insertarlos en BigQuery
        if hoteles_procesados:
            # Mostrar datos procesados (para depuración)
            logging.info(f"Datos procesados (primera muestra): {json.dumps(hoteles_procesados[0], indent=2)}")
            logging.info(f"Total de hoteles procesados: {len(hoteles_procesados)}")
            
            # Insertar en BigQuery
            insertar_en_bigquery(hoteles_procesados)
        else:
            logging.warning("No se encontraron hoteles para procesar")
            
    except Exception as e:
        logging.exception("💥 Error en limpieza_hoteles: %s", e)