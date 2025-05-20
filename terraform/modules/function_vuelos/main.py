import http.client
import json
import os
from urllib.parse import urlencode
from serpapi import GoogleSearch
from google.cloud import bigquery
from flask import jsonify
import logging  # Importa la biblioteca de logging

# === CONFIGURACIÓN ===
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET = os.environ.get("DATASET")
TABLE = os.environ.get("TABLE")

# === HEADERS BOOKING ===
RAPIDAPI_HOST = "booking-com18.p.rapidapi.com"
RAPIDAPI_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

# === CONFIGURACIÓN DE LOGGING ===
logging.basicConfig(level=logging.INFO,  # Nivel mínimo de los logs que se capturan
                    format='%(asctime)s - %(levelname)s - %(message)s')

def ms_a_duracion(ms):
    total_min = ms // 60000
    horas = total_min // 60
    minutos = total_min % 60
    return f"{horas}h {minutos}m"

# === BOOKING ===
def buscar_en_booking(payload):
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    params = {
        "fromId": payload["ciudad_origen"],
        "toId": payload["ciudad_destino"],
        "departureDate": payload["fecha_salida"],
        "cabinClass": payload["cabin_class"],
        "numberOfAdults": payload["adults"]
    }
    if payload["tipo_de_viaje"] == 1:
        params["returnDate"] = payload["fecha_vuelta"]
    conn.request("GET", f"/flights/search-return?{urlencode(params)}", headers=RAPIDAPI_HEADERS)
    res = conn.getresponse()
    return json.loads(res.read().decode("utf-8"))

def limpiar_booking(data):
    vuelos = []
    for vuelo in data.get("data", {}).get("flights", []):
        for i, tramo in enumerate(vuelo.get("bounds", [])):
            try:
                seg = tramo["segments"][0]
                airline = seg["marketingCarrier"]["name"]
                logo = seg["marketingCarrier"].get("logoUrl", "")
                salida = seg["departuredAt"].replace("T", " ")
                llegada = tramo["segments"][-1]["arrivedAt"].replace("T", " ")
                duracion = ms_a_duracion(tramo.get("duration", 0))
                escalas = len(tramo["segments"]) - 1
                escalas_en = [s["arrivalAirport"]["name"] for s in tramo["segments"][:-1]]
                precio = round(vuelo["travelerPrices"][0]["price"]["price"]["value"] / 100)
                enlace = vuelo.get("shareableUrl", "")
                vuelos.append({
                    "Compañia": "Booking",
                    "Aerolinea": airline,
                    "PrecioEur": precio,
                    "FechaSalida": salida,
                    "FechaLlegada": llegada,
                    "Duración": duracion,
                    "Escalas": escalas,
                    "EscalasEn": ", ".join(escalas_en),
                    "LogoUrl": logo,
                    "EnlaceCompra": enlace
                })
            except Exception as e:
                logging.error(f"[Booking] Error: {e}", exc_info=True)  # Loguea el error con detalle
    return vuelos

# === SERPAPI ===
def buscar_en_serpapi(payload):
    params = {
        "api_key": SERPAPI_KEY,
        "engine": "google_flights",
        "hl": "es",
        "gl": "es",
        "departure_id": payload["ciudad_origen"],
        "arrival_id": payload["ciudad_destino"],
        "outbound_date": payload["fecha_salida"],
        "currency": "EUR",
        "type": str(payload["tipo_de_viaje"]),
        "adults": str(payload["adults"])
    }
    if payload["tipo_de_viaje"] == 1:
        params["return_date"] = payload["fecha_vuelta"]
    search = GoogleSearch(params)
    return search.get_dict()

def limpiar_serpapi(data):
    vuelos = []
    url = data.get("search_metadata", {}).get("google_flights_url", "")
    for tipo_raw in ["best_flights", "other_flights"]:
        for vuelo in data.get(tipo_raw, []):
            try:
                segs = vuelo.get("flights", [])
                if not segs:
                    continue
                salida = segs[0]["departure_airport"]["time"]
                llegada = segs[-1]["arrival_airport"]["time"]
                airline = segs[0]["airline"]
                logo = segs[0]["airline_logo"]
                escalas = len(segs) - 1
                escalas_en = [l.get("name") for l in vuelo.get("layovers", [])] if vuelo.get("layovers") else []
                duracion = vuelo.get("total_duration", "No disponible")
                precio = int(str(vuelo.get("price", "0")).replace("€", "").strip())

                vuelos.append({
                    "Compañia": "Google Flights",
                    "Aerolinea": airline,
                    "PrecioEur": precio,
                    "FechaSalida": salida,
                    "FechaLlegada": llegada,
                    "Duración": duracion,
                    "Escalas": escalas,
                    "EscalasEn": ", ".join(escalas_en),
                    "LogoUrl": logo,
                    "EnlaceCompra": url
                })
            except Exception as e:
                logging.error(f"[SerpAPI] Error: {e}", exc_info=True)  # Loguea el error con detalle
    return vuelos

# === BIGQUERY ===
def insertar_en_bigquery(vuelos, PROJECT_ID, DATASET, TABLE):
    client = bigquery.Client(project=PROJECT_ID)
    tabla_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    # 1. Consultar claves existentes (usamos Aerolinea + FechaSalida + FechaLlegada)
    query = f"""
        SELECT Aerolinea, FechaSalida, FechaLlegada
        FROM `{tabla_ref}`
    """
    existentes = client.query(query).result()
    claves_existentes = set((r.Aerolinea, str(r.FechaSalida), str(r.FechaLlegada)) for r in existentes)

    # 2. Filtrar vuelos nuevos
    nuevos_vuelos = [
        v for v in vuelos
        if (v["Aerolinea"], v["FechaSalida"], v["FechaLlegada"]) not in claves_existentes
    ]

    if not nuevos_vuelos:
        logging.info("⏩ No hay vuelos nuevos para insertar.")
        return True

    # 3. Insertar solo los nuevos
    errors = client.insert_rows_json(tabla_ref, nuevos_vuelos)
    if not errors:
        logging.info(f"✅ Insertados {len(nuevos_vuelos)} registros nuevos en BigQuery.")
        return True
    else:
        logging.error(f"❌ Errores al insertar en BigQuery: {errors}")
        return False

# === MAIN (Cloud Function Entry Point) ===
def buscar_vuelos(request):
    """
    Cloud Function que procesa datos de vuelos, los guarda en BigQuery
    y los devuelve como JSON.
    """
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            logging.error("No JSON payload provided", exc_info=True)
            return jsonify({"error": "No JSON payload provided"}), 400

        payload = request_json

        logging.info("🔎 Booking...")
        resultado_booking = buscar_en_booking(payload)
        vuelos_booking = limpiar_booking(resultado_booking)
        logging.info("Resultados de Booking procesados.")

        logging.info("🔎 SerpAPI...")
        resultado_serpapi = buscar_en_serpapi(payload)
        vuelos_serpapi = limpiar_serpapi(resultado_serpapi)
        logging.info("Resultados de SerpAPI procesados.")

        vuelos_combinados = vuelos_booking + vuelos_serpapi

        # Insertar en BigQuery
        insercion_exitosa = insertar_en_bigquery(vuelos_combinados, PROJECT_ID, DATASET, TABLE)

        if insercion_exitosa:
            logging.info("Datos insertados correctamente en BigQuery.  Devolviendo resultados.")
            return jsonify(vuelos_combinados), 200
        else:
            logging.error("Error al insertar datos en BigQuery.", exc_info=True)
            return jsonify({"error": "Error al insertar en BigQuery"}), 500

    except Exception as e:
        logging.error(f"💥 Error general: {e}", exc_info=True) # Loguea el error general con detalle
        return jsonify({"error": f"Error en el procesamiento: {e}"}), 500