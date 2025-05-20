import json
import os
import logging
from datetime import datetime
from serpapi import GoogleSearch
from flask import jsonify
from google.cloud import bigquery

# === CONFIGURACIÓN ===
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET = os.environ.get("DATASET")
TABLE = os.environ.get("TABLE")

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === SERPAPI ===
def buscar_en_serpapi(payload):
    params = {
        "api_key": SERPAPI_KEY,
        "engine": "google_hotels",
        "q": f"{payload['ciudad']} hoteles",
        "check_in_date": payload["fecha_entrada"],
        "check_out_date": payload["fecha_vuelta"],
        "currency": "EUR",
        "hl": "es",
        "gl": "es",
        "num": "40",
        "adults": str(payload.get("adults", 2))
    }
    if payload.get("max_price"):
        params["price_max"] = str(payload["max_price"])
    if payload.get("valoracion"):
        params["guest_rating_min"] = str(payload["valoracion"])

    search = GoogleSearch(params)
    return search.get_dict()

def limpiar_hoteles(data, payload):
    hoteles = []
    propiedades = data.get("properties", data.get("hotels_results", []))

    for hotel in propiedades:
        try:
            imagenes = [img.get("original_image") for img in hotel.get("images", []) if "original_image" in img]
            hoteles.append({
                "Nombre": hotel.get("name") or hotel.get("title", ""),
                "Latitud": hotel.get("latitude", hotel.get("gps_coordinates", {}).get("latitude", 0.0)),
                "Longitud": hotel.get("longitude", hotel.get("gps_coordinates", {}).get("longitude", 0.0)),
                "PrecioTotal": hotel.get("total_rate", {}).get("extracted_lowest", 0.0),
                "Puntuación": hotel.get("overall_rating", hotel.get("rating", 0.0)),
                "Ciudad": payload["ciudad"],
                "FechaEntrada": payload["fecha_entrada"],
                "FechaSalida": payload["fecha_vuelta"],
                "URL": hotel.get("link", ""),
                "Imagenes": imagenes
            })
        except Exception as e:
            logging.error(f"[SerpAPI] Error limpiando hotel: {e}", exc_info=True)
    return hoteles

# === BIGQUERY ===
def insertar_en_bigquery(hoteles):
    client = bigquery.Client(project=PROJECT_ID)
    tabla_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    # 1. Leer claves existentes en la tabla
    query = f"""
        SELECT Nombre, FechaEntrada, FechaSalida
        FROM `{tabla_ref}`
    """
    existentes = client.query(query).result()
    claves_existentes = set((r.Nombre, str(r.FechaEntrada), str(r.FechaSalida)) for r in existentes)

    # 2. Filtrar hoteles nuevos
    nuevos_hoteles = [
        h for h in hoteles
        if (h["Nombre"], h["FechaEntrada"], h["FechaSalida"]) not in claves_existentes
    ]

    if not nuevos_hoteles:
        logging.info("⏩ No hay hoteles nuevos para insertar.")
        return True

    # 3. Insertar solo los nuevos
    errors = client.insert_rows_json(tabla_ref, nuevos_hoteles)
    if not errors:
        logging.info(f"✅ Insertados {len(nuevos_hoteles)} hoteles en BigQuery.")
        return True
    else:
        logging.error(f"❌ Errores al insertar en BigQuery: {errors}")
        return False
# === CLOUD FUNCTION ENTRY POINT ===
def buscar_hoteles(request):
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return jsonify({"error": "No se proporcionó un JSON"}), 400

        payload = request_json
        logging.info(f"🔍 Buscando hoteles en {payload['ciudad']} del {payload['fecha_entrada']} al {payload['fecha_vuelta']}")

        resultado = buscar_en_serpapi(payload)
        hoteles = limpiar_hoteles(resultado, payload)

        exito = insertar_en_bigquery(hoteles)
        if exito:
            return jsonify(hoteles), 200
        else:
            return jsonify({"error": "Error al insertar en BigQuery"}), 500

    except Exception as e:
        logging.error(f"💥 Error general: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
