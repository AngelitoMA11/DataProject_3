#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para leer mensajes de la suscripción de Pub/Sub, procesar los datos de hoteles
e insertarlos directamente en BigQuery.
"""

import json
import time
import os
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1
from google.cloud import bigquery

# Configuración
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "dataproject3-458310")
SUBSCRIPTION_NAME = os.getenv("PUBSUB_SUBSCRIPTION", "projects/dataproject3-458310/subscriptions/hoteles-sub")
DATASET_ID = "app_viajes"  # Cambiado a app_viajes
TABLE_ID = "hoteles"
TIMEOUT = 60  # Segundos para esperar mensajes

# Cliente de Pub/Sub para suscriptor
subscriber = pubsub_v1.SubscriberClient()

# Cliente de BigQuery
bq_client = bigquery.Client(project=PROJECT_ID)

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
            "direccion": extract_safe_string(hotel.get('accessibilityLabel', '').split('\n')[0]),
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
            "timestamp": parent_data.get('timestamp', int(time.time() * 1000)) if parent_data else int(time.time() * 1000)
        }
        
        # Agregar datos adicionales si están disponibles
        if 'mainPhotoId' in property_data:
            hotel_procesado['id_foto_principal'] = extract_safe_string(property_data['mainPhotoId'])
        
        if 'photoUrls' in property_data and property_data['photoUrls']:
            hotel_procesado['url_foto'] = extract_safe_string(property_data['photoUrls'][0])
        
        return hotel_procesado
        
    except Exception as e:
        print(f"Error al procesar hotel individual: {e}")
        return None

def insert_into_bigquery(hoteles_procesados):
    """
    Inserta los datos procesados en BigQuery
    
    Args:
        hoteles_procesados: Lista de hoteles procesados para insertar
        
    Returns:
        bool: True si la inserción fue exitosa, False en caso contrario
    """
    try:
        if not hoteles_procesados:
            print("No hay datos para insertar en BigQuery")
            return False
            
        # Referencia a la tabla
        table_ref = bq_client.dataset(DATASET_ID).table(TABLE_ID)
        
        # Insertar filas
        errors = bq_client.insert_rows_json(table_ref, hoteles_procesados)
        
        if errors:
            print(f"Se encontraron errores al insertar datos: {errors}")
            return False
        else:
            print(f"Insertados {len(hoteles_procesados)} hoteles en BigQuery correctamente")
            return True
            
    except Exception as e:
        print(f"Error al insertar en BigQuery: {e}")
        return False

def process_message(message):
    """
    Procesa un mensaje individual de Pub/Sub
    """
    try:
        # Decodificar el mensaje
        payload = message.data.decode("utf-8")
        print(f"Mensaje recibido: {payload[:100]}...")  # Imprime los primeros 100 caracteres
        
        # Parsear el JSON
        data = json.loads(payload)
        
        # Verificar la estructura del mensaje
        if not isinstance(data, dict):
            print("El mensaje no es un objeto JSON válido")
            message.ack()
            return []
        
        # Extraer la lista de hoteles del mensaje
        hoteles = []
        if 'data' in data and 'hotels' in data['data']:
            hoteles = data['data']['hotels']
        
        if not hoteles:
            print("No se encontraron hoteles en el mensaje")
            message.ack()
            return []
        
        print(f"Se encontraron {len(hoteles)} hoteles para procesar")
        
        # Procesar los datos de los hoteles
        hoteles_procesados = []
        for hotel in hoteles:
            hotel_procesado = process_hotel_data(hotel, data)
            if hotel_procesado:
                hoteles_procesados.append(hotel_procesado)
        
        # Confirmar que el mensaje ha sido procesado
        message.ack()
        
        # Devolver los datos procesados
        return hoteles_procesados
        
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        message.ack()
        return []
    except Exception as e:
        print(f"Error general al procesar mensaje: {e}")
        message.ack()
        return []

def procesar_e_insertar(mensaje_procesado):
    """
    Procesa un mensaje e inserta los datos en BigQuery
    """
    # Procesar el mensaje
    hoteles_procesados = process_message(mensaje_procesado)
    
    if hoteles_procesados:
        # Mostrar datos procesados (para depuración)
        print(f"Datos procesados (primeros 2 hoteles):")
        for i, hotel in enumerate(hoteles_procesados[:2]):
            print(f"Hotel {i+1}: {json.dumps(hotel, indent=2)}")
        
        if len(hoteles_procesados) > 2:
            print(f"... y {len(hoteles_procesados) - 2} hoteles más")
        
        # Insertar en BigQuery
        resultado = insert_into_bigquery(hoteles_procesados)
        return resultado
    else:
        print("No hay datos para insertar en BigQuery")
        return False

def leer_pubsub_e_insertar():
    """
    Lee mensajes de la suscripción de Pub/Sub, procesa los datos e inserta en BigQuery
    """
    try:
        processed_messages = 0
        successful_inserts = 0
        
        # Callback al recibir mensaje
        def callback(message):
            nonlocal processed_messages, successful_inserts
            print(f"Recibido mensaje con ID: {message.message_id}")
            if procesar_e_insertar(message):
                successful_inserts += 1
            processed_messages += 1
            
        # Iniciar la recepción de mensajes
        streaming_pull_future = subscriber.subscribe(
            SUBSCRIPTION_NAME, callback=callback
        )
        print(f"Escuchando mensajes en {SUBSCRIPTION_NAME}...")
        
        # Esperar por mensajes durante un tiempo limitado
        try:
            # Bloquear hasta que el tiempo expire o se reciban mensajes
            streaming_pull_future.result(timeout=TIMEOUT)
        except TimeoutError:
            streaming_pull_future.cancel()
            streaming_pull_future.result()
        finally:
            print(f"Finalizado el tiempo de escucha: {TIMEOUT} segundos")
            print(f"Mensajes procesados: {processed_messages}")
            print(f"Inserciones exitosas: {successful_inserts}")
        
        return successful_inserts > 0
        
    except Exception as e:
        print(f"Error al leer de Pub/Sub: {e}")
        return False
    finally:
        # Asegurarse de cerrar la conexión del subscriptor
        subscriber.close()

def main():
    """
    Función principal
    """
    print("Iniciando lectura de Pub/Sub e inserción en BigQuery...")
    resultado = leer_pubsub_e_insertar()
    
    if resultado:
        print("Proceso completado exitosamente")
    else:
        print("No se insertaron datos o ocurrieron errores durante el proceso")

if __name__ == "__main__":
    main()