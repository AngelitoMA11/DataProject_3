import base64
import json
import os
from google.cloud import bigquery

# Configuración de BigQuery
project_id = "dataproject3-458310"
dataset_id = "booking_data"  # Cambia esto por tu dataset
table_id = "hoteles"        # Cambia esto por tu tabla

# Cliente de BigQuery
client = bigquery.Client(project=project_id)

def procesar_hoteles(event, context):
    """
    Cloud Function que se activa con mensajes de Pub/Sub,
    procesa datos de hoteles y los inserta en BigQuery.
    
    Args:
        event (dict): Evento de Pub/Sub
        context (google.cloud.functions.Context): Metadata del evento
    """
    # Extraer datos del mensaje de Pub/Sub
    if 'data' in event:
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        try:
            data = json.loads(pubsub_message)
            print(f"Mensaje recibido: {type(data)}")
            
            # Procesar resultados
            if 'data' in data:
                resultados = data.get('data', {})
                hoteles = resultados.get('hotels', [])
                
                if not hoteles:
                    print("No se encontraron hoteles en los datos")
                    return
                
                # Preparar datos para BigQuery
                rows_to_insert = []
                for hotel in hoteles:
                    # Extraer los campos deseados
                    hotel_procesado = {
                        "hotel_id": hotel.get("hotel_id"),
                        "name": hotel.get("name"),
                        "address": hotel.get("address", ""),
                        "city": hotel.get("city", ""),
                        "latitude": float(hotel.get("latitude", 0)),
                        "longitude": float(hotel.get("longitude", 0)),
                        "rating": float(hotel.get("rating", 0)),
                        "review_score": float(hotel.get("review_score", 0)),
                        "review_count": int(hotel.get("review_count", 0)),
                        "price": float(hotel.get("price", {}).get("price", 0)),
                        "currency": hotel.get("price", {}).get("currency", ""),
                        "checkin_date": resultados.get("checkin_date", ""),
                        "checkout_date": resultados.get("checkout_date", ""),
                        "timestamp": context.timestamp,
                    }
                    rows_to_insert.append(hotel_procesado)
                
                # Insertar en BigQuery
                if rows_to_insert:
                    table_ref = client.dataset(dataset_id).table(table_id)
                    errors = client.insert_rows_json(table_ref, rows_to_insert)
                    
                    if errors:
                        print(f"Se encontraron errores al insertar datos: {errors}")
                    else:
                        print(f"Insertados {len(rows_to_insert)} hoteles en BigQuery")
            else:
                print("Formato de datos inesperado")
                
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
        except Exception as e:
            print(f"Error al procesar datos: {e}")
    else:
        print("No se encontró 'data' en el evento")