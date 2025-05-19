import json
import os
import requests
from serpapi import GoogleSearch
from google.cloud import bigquery
import functions_framework
import logging
from flask import jsonify
from datetime import datetime

# Configuración básica
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "9a5a4641c80909144e8cff701a3848d40a6c8e3436606c7417a61487d4c3ab74")
PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET = os.environ.get("DATASET")
TABLE = os.environ.get("TABLE")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- SERPAPI ---
def buscar_en_serpapi(payload):
    try:
        ciudad_query = payload['ciudad'].replace(" ", "+")
        params = {
            "api_key": SERPAPI_KEY, 
            "engine": "google_hotels",
            "q": f"{ciudad_query} hotels",
            "check_in_date": payload["fecha_entrada"], 
            "check_out_date": payload["fecha_vuelta"],
            "currency": "EUR", 
            "hl": "es", 
            "gl": "es", 
            "num": "20",
            "adults": str(payload.get("adults", 2))
        }
        if payload.get("max_price"): params["price_max"] = str(payload["max_price"])
        if payload.get("valoracion"): params["guest_rating_min"] = str(payload["valoracion"])
        
        logging.info(f"Parámetros SerpAPI: {params}")
        search = GoogleSearch(params)
        resultados = search.get_dict()
        
        logging.info(f"Claves en respuesta SerpAPI: {list(resultados.keys())}")
        
        return resultados
    except Exception as e:
        logging.error(f"Error en SerpAPI: {str(e)}")
        return {"error": str(e)}

def limpiar_serpapi(data, payload):
    hoteles = []
    
    # Buscar los hoteles en la respuesta
    propiedades = []
    if "properties" in data:
        propiedades = data["properties"]
    elif "hotels_results" in data:
        propiedades = data["hotels_results"]
    else:
        logging.warning(f"No se encontraron hoteles en SerpAPI")
        return hoteles
    
    logging.info(f"Encontrados {len(propiedades)} hoteles en datos crudos de SerpAPI")
    
    for hotel in propiedades:
        try:
            # Inicialización con valores por defecto
            hotel_obj = {
                "property_token": "",
                "type": "",
                "name": "",
                "link": "",
                "latitud": 0.0,
                "longitud": 0.0,
                "precio_noche": 0.0,
                "precio_total": 0.0,
                "moneda": "EUR",
                "fuente_precio": "",
                "puntuacion": 0.0,
                "numero_resenas": 0,
                "puntuacion_ubicacion": 0.0,
                "imagen_principal": "",
                "imagenes": "[]",
                "comodidades": "[]",
                "info_esencial": "[]",
                "lugares_cercanos": "[]",
                "ciudad": payload["ciudad"],
                "fecha_entrada": payload["fecha_entrada"],
                "fecha_salida": payload["fecha_vuelta"],
                "timestamp": int(datetime.now().timestamp())
            }
            
            # Property token
            if "property_token" in hotel:
                hotel_obj["property_token"] = hotel["property_token"]
                
            # Type
            if "type" in hotel:
                hotel_obj["type"] = hotel["type"]
                
            # Name
            if "name" in hotel:
                hotel_obj["name"] = hotel["name"]
            elif "title" in hotel:
                hotel_obj["name"] = hotel["title"]
                
            # Link
            if "link" in hotel:
                hotel_obj["link"] = hotel["link"]
            elif "serpapi_property_details_link" in hotel:
                hotel_obj["link"] = hotel["serpapi_property_details_link"]
                
            # Coordenadas GPS
            if "gps_coordinates" in hotel:
                coords = hotel["gps_coordinates"]
                if "latitude" in coords and "longitude" in coords:
                    hotel_obj["latitud"] = float(coords["latitude"])
                    hotel_obj["longitud"] = float(coords["longitude"])
            elif "latitude" in hotel and "longitude" in hotel:
                hotel_obj["latitud"] = float(hotel["latitude"])
                hotel_obj["longitud"] = float(hotel["longitude"])
                
            # Precio por noche
            if "rate_per_night" in hotel:
                rate = hotel["rate_per_night"]
                if "extracted_lowest" in rate:
                    hotel_obj["precio_noche"] = float(rate["extracted_lowest"])
                    
            # Precio total
            if "total_rate" in hotel:
                rate = hotel["total_rate"]
                if "extracted_lowest" in rate:
                    hotel_obj["precio_total"] = float(rate["extracted_lowest"])
                    
            # Fuente de precio
            if "prices" in hotel and len(hotel["prices"]) > 0:
                price_info = hotel["prices"][0]
                if "source" in price_info:
                    hotel_obj["fuente_precio"] = price_info["source"]
                    
            # Puntuación y reseñas
            if "overall_rating" in hotel:
                hotel_obj["puntuacion"] = float(hotel["overall_rating"])
            elif "rating" in hotel:
                hotel_obj["puntuacion"] = float(hotel["rating"])
                
            if "reviews" in hotel:
                if isinstance(hotel["reviews"], int):
                    hotel_obj["numero_resenas"] = hotel["reviews"]
                else:
                    try:
                        hotel_obj["numero_resenas"] = int(hotel["reviews"])
                    except:
                        pass
                        
            # Puntuación de ubicación
            if "location_rating" in hotel:
                hotel_obj["puntuacion_ubicacion"] = float(hotel["location_rating"])
                
            # Imágenes
            if "images" in hotel and len(hotel["images"]) > 0:
                images = []
                for img in hotel["images"]:
                    if "original_image" in img:
                        images.append(img["original_image"])
                if images:
                    hotel_obj["imagen_principal"] = images[0]
                    hotel_obj["imagenes"] = json.dumps(images)
            elif "thumbnail" in hotel:
                hotel_obj["imagen_principal"] = hotel["thumbnail"]
                hotel_obj["imagenes"] = json.dumps([hotel["thumbnail"]])
                
            # Comodidades
            if "amenities" in hotel:
                hotel_obj["comodidades"] = json.dumps(hotel["amenities"])
                
            # Información esencial
            if "essential_info" in hotel:
                hotel_obj["info_esencial"] = json.dumps(hotel["essential_info"])
                
            # Lugares cercanos
            if "nearby_places" in hotel:
                hotel_obj["lugares_cercanos"] = json.dumps(hotel["nearby_places"])
                
            hoteles.append(hotel_obj)
        except Exception as e:
            logging.error(f"Error procesando hotel: {str(e)}")
    
    return hoteles

# --- BIGQUERY ---
def insertar_en_bigquery(hoteles):
    if not hoteles: 
        return False
        
    try:
        client = bigquery.Client(project=PROJECT_ID)
        tabla_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"
        
        errors = client.insert_rows_json(tabla_id, hoteles)
        
        if errors:
            logging.error(f"Error BigQuery: {errors}")
            return False
            
        logging.info(f"✅ Insertados {len(hoteles)} hoteles en BigQuery.")
        return True
    except Exception as e:
        logging.error(f"Error en BigQuery: {str(e)}")
        return False

# --- CLOUD FUNCTION ---
@functions_framework.http
def buscar_hoteles(request):
    try:
        # Obtener payload
        request_json = request.get_json(silent=True)
        if not request_json:
            return jsonify({"error": "No se proporcionó un payload JSON"}), 400
        
        # Adaptación de campos (para soportar diferentes formatos)
        payload = {}
        
        # Ciudad
        if "ciudad" in request_json:
            payload["ciudad"] = request_json["ciudad"]
        elif "ciudad_destino" in request_json:
            payload["ciudad"] = request_json["ciudad_destino"]
        else:
            return jsonify({"error": "Se requiere ciudad o ciudad_destino"}), 400
            
        # Fechas
        if "fecha_entrada" in request_json and "fecha_vuelta" in request_json:
            payload["fecha_entrada"] = request_json["fecha_entrada"]
            payload["fecha_vuelta"] = request_json["fecha_vuelta"]
        elif "fecha_salida" in request_json and "fecha_vuelta" in request_json:
            payload["fecha_entrada"] = request_json["fecha_salida"]
            payload["fecha_vuelta"] = request_json["fecha_vuelta"]
        else:
            return jsonify({"error": "Se requieren fechas de entrada y salida"}), 400
            
        # Parámetros adicionales
        payload["adults"] = request_json.get("adults", 2)
        payload["valoracion"] = request_json.get("valoracion")
        
        logging.info(f"Búsqueda de hoteles en {payload['ciudad']} del {payload['fecha_entrada']} al {payload['fecha_vuelta']}")

        # Buscar con SerpAPI
        logging.info("🔎 Buscando hoteles...")
        resultado_serpapi = buscar_en_serpapi(payload)
        hoteles = limpiar_serpapi(resultado_serpapi, payload)
        logging.info(f"Total de hoteles procesados: {len(hoteles)}")

        # Filtrar por valoración si se especificó
        if payload.get("valoracion"):
            try:
                min_rating = float(payload["valoracion"])
                hoteles_filtrados = [h for h in hoteles if h["puntuacion"] >= min_rating]
                logging.info(f"Filtrado por valoración ≥{min_rating}: {len(hoteles_filtrados)} hoteles")
                hoteles = hoteles_filtrados
            except:
                pass

        # Insertar en BigQuery
        insertar_en_bigquery(hoteles)

        # Devolver resultados
        return jsonify({
            "success": True,
            "hoteles_encontrados": len(hoteles),
            "hoteles": hoteles
        }), 200
    except Exception as e:
        logging.error(f"💥 Error general: {str(e)}")
        return jsonify({
            "error": str(e), 
            "success": False
        }), 500