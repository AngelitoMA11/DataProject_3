import json
import os
import logging
from datetime import datetime
from serpapi import GoogleSearch

# Configuración
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "b74172722f4941a765f54e6b0649b24fa1d30052036066dc25e7953707ec63f4")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Payload de entrada (MODIFICA AQUÍ)
payload = {
    "ciudad": "London, United Kingdom",
    "fecha_entrada": "2025-06-10",
    "fecha_vuelta": "2025-06-15",
    "adults": 2,
    "valoracion": 4.0,
    "max_price": 300
}

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
        if payload.get("max_price"):
            params["price_max"] = str(payload["max_price"])
        if payload.get("valoracion"):
            params["guest_rating_min"] = str(payload["valoracion"])

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
    propiedades = data.get("properties", data.get("hotels_results", []))

    for hotel in propiedades:
        try:
            hotel_obj = {
                "Nombre": hotel.get("name") or hotel.get("title", ""),
                "Latitud": hotel.get("latitude", hotel.get("gps_coordinates", {}).get("latitude", 0.0)),
                "Longitud": hotel.get("longitude", hotel.get("gps_coordinates", {}).get("longitude", 0.0)),
                "PrecioTotal": hotel.get("total_rate", {}).get("extracted_lowest", 0.0),
                "Puntuación": hotel.get("overall_rating", hotel.get("rating", 0.0)),
                "Ciudad": payload["ciudad"],
                "FechaEntrada": payload["fecha_entrada"],
                "FechaSalida": payload["fecha_vuelta"]
            }
            hoteles.append(hotel_obj)
        except Exception as e:
            logging.error(f"Error limpiando hotel: {str(e)}")
    return hoteles

# EJECUCIÓN LOCAL
if __name__ == "__main__":
    logging.info("🔎 Ejecutando búsqueda de hoteles")
    resultados = buscar_en_serpapi(payload)

    # Guardar datos crudos
    with open("resultados_brutos.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    logging.info("📦 Resultados brutos guardados en resultados_brutos.json")

    # Limpiar y guardar resultados con claves formateadas
    hoteles = limpiar_serpapi(resultados, payload)
    with open("resultados_hoteles.json", "w", encoding="utf-8") as f:
        json.dump(hoteles, f, indent=2, ensure_ascii=False)
    logging.info(f"✅ Resultados limpios guardados en resultados_hoteles.json con {len(hoteles)} hoteles")
