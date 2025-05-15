import json
import os
import httpx
import urllib.parse
import pandas as pd
from google.cloud import bigquery
import functions_framework
import google.cloud.logging
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
ENDPOINT_VUELOS_VUELTA = f"{ENDPOINT_BASE}/vuelos/limpios"


# Inicializar cliente de logging
client_logging = google.cloud.logging.Client()
client_logging.setup_logging()
import logging

async def obtener_id_ciudad(ciudad: str) -> str:
    async with httpx.AsyncClient() as client:
        query = urllib.parse.quote(ciudad)
        url = f"https://{FLIGHT_HOTEL_HOST}/api/v1/flights/searchDestination?query={query}"
        resp = await client.get(url, headers=FLIGHT_HOTEL_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        for item in data:
            if "airport" in item.get("type", "").lower():
                return item["id"]
        raise ValueError(f"Aeropuerto no encontrado para {ciudad}")

def construir_parametros_api_vuelo(req: dict, origin_id: str, destination_id: str) -> dict:
    fecha_salida = "-".join(reversed(req["fecha_salida"].split("-")))
    return {
        "fromId": origin_id,
        "toId": destination_id,
        "departDate": fecha_salida,
        "stops": req.get("stops", "none"),
        "adults": str(req.get("adults", 1)),
        "children": req.get("children", "0"),
        "cabinClass": req.get("cabin_class", "ECONOMY"),
        "currency_code": req.get("currency", "EUR")
    }

def procesar_vuelos(ofertas):
    registros = []
    for offer in ofertas:
        segments = offer.get("segments", [])
        if not segments:
            continue

        first_leg = segments[0]["legs"][0] if segments[0].get("legs") else {}
        last_leg = segments[-1]["legs"][-1] if segments[-1].get("legs") else {}

        ciudad_salida = first_leg.get("departureAirport", {}).get("cityName")
        ciudad_llegada = last_leg.get("arrivalAirport", {}).get("cityName")

        salida_dt = first_leg.get("departureTime", "")
        llegada_dt = last_leg.get("arrivalTime", "")
        dia_salida, hora_salida = salida_dt.split("T") if "T" in salida_dt else ("", "")
        dia_llegada, hora_llegada = llegada_dt.split("T") if "T" in llegada_dt else ("", "")

        duracion_segundos = sum(seg.get("totalTime", 0) for seg in segments)
        horas = duracion_segundos // 3600
        minutos = (duracion_segundos % 3600) // 60
        duracion_legible = f"{int(horas)}h {int(minutos)}m"

        escalas = sum(len(seg.get("legs", [])) - 1 for seg in segments)

        ciudades_escala = []
        for seg in segments:
            legs = seg.get("legs", [])
            for i in range(len(legs) - 1):
                city = legs[i].get("arrivalAirport", {}).get("cityName")
                if city:
                    ciudades_escala.append(city)

        try:
            aerolinea = segments[0]["legs"][0]["carriersData"][0]["name"]
        except (IndexError, KeyError, TypeError):
            aerolinea = ""

        precio_total = offer.get("priceBreakdown", {}).get("total", {})
        precio_eur = precio_total.get("units", 0) + precio_total.get("nanos", 0) / 1e9

        registros.append({
            "fuente": "booking",
            "ciudad_salida": ciudad_salida,
            "ciudad_llegada": ciudad_llegada,
            "dia_salida": dia_salida,
            "hora_salida": hora_salida,
            "dia_llegada": dia_llegada,
            "hora_llegada": hora_llegada,
            "aerolinea": aerolinea,
            "precio_eur": round(precio_eur, 2),
            "tipo_trayecto": offer.get("tripType"),
            "duracion": duracion_legible,
            "numero_escalas": escalas,
            "ciudades_escala": ciudades_escala
        })

    return registros

def preparar_dataframe(vuelos):
    df = pd.DataFrame(vuelos)
    if df.empty:
        return df

    df["dia_salida"] = pd.to_datetime(df["dia_salida"], errors="coerce").dt.date
    df["dia_llegada"] = pd.to_datetime(df["dia_llegada"], errors="coerce").dt.date
    df["hora_salida"] = df["hora_salida"].fillna("").astype(str).apply(lambda x: x if ":" in x else "")
    df["hora_llegada"] = df["hora_llegada"].fillna("").astype(str).apply(lambda x: x if ":" in x else "")
    df["ciudad_salida"] = df["ciudad_salida"].fillna("").astype(str)
    df["ciudad_llegada"] = df["ciudad_llegada"].fillna("").astype(str)
    df["aerolinea"] = df["aerolinea"].fillna("").astype(str)
    df["tipo_trayecto"] = df["tipo_trayecto"].fillna("").astype(str)
    df["duracion"] = df["duracion"].fillna("").astype(str)
    df["ciudades_escala"] = df["ciudades_escala"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x)).fillna("")

    return df

def insertar_en_bigquery(df):
    if df.empty:
        return
    client = bigquery.Client(project=PROJECT_ID)
    tabla_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    job = client.load_table_from_dataframe(df, tabla_id)
    job.result()

@functions_framework.http
async def buscar_vuelos(request):
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            logging.error("Cuerpo JSON no válido o ausente.")
            return {"error": "No se proporcionó un cuerpo JSON válido"}
    except Exception as e:
        logging.exception("Error al obtener el JSON de la solicitud.")
        return {"error": f"Error al procesar la solicitud: {str(e)}"}

    try:
        if not all(k in request_json for k in ["ciudad_origen", "ciudad_destino_aeropuerto", "fecha_salida"]):
            logging.error("Faltan campos obligatorios en el JSON de entrada.")
            return {"error": "Faltan datos obligatorios para la búsqueda de vuelos"}

        origin_id = await obtener_id_ciudad(request_json["ciudad_origen"])
        dest_id = await obtener_id_ciudad(request_json["ciudad_destino_aeropuerto"])
        params_ida = construir_parametros_api_vuelo(request_json, origin_id, dest_id)

        url_vuelo = f"https://{FLIGHT_HOTEL_HOST}/api/v1/flights/searchFlights"
        async with httpx.AsyncClient() as client:
            resp_ida = await client.get(url_vuelo, headers=FLIGHT_HOTEL_HEADERS, params=params_ida, timeout=20)
            resp_ida.raise_for_status()
            data_ida = resp_ida.json()

        resultados_vuelos = {"ida": data_ida["data"], "vuelta": None}

        if request_json.get("fecha_vuelta"):
            vuelo_vuelta = {
                "ciudad_origen": request_json["ciudad_destino_aeropuerto"],
                "ciudad_destino_aeropuerto": request_json["ciudad_origen"],
                "fecha_salida": request_json["fecha_vuelta"],
                "stops": request_json.get("stops", "none"),
                "adults": request_json.get("adults", 1),
                "children": request_json.get("children", "0"),
                "cabin_class": request_json.get("cabin_class", "ECONOMY"),
                "currency": request_json.get("currency", "EUR")
            }
            params_vuelta = construir_parametros_api_vuelo(vuelo_vuelta, dest_id, origin_id)
            async with httpx.AsyncClient() as client:
                resp_vuelta = await client.get(url_vuelo, headers=FLIGHT_HOTEL_HEADERS, params=params_vuelta, timeout=20)
                resp_vuelta.raise_for_status()
                vuelos_vuelta = resp_vuelta.json()
                resultados_vuelos["vuelta"] = vuelos_vuelta["data"]

        vuelos_ida = procesar_vuelos(resultados_vuelos["ida"].get("flightOffers", []))
        vuelos_vuelta = []
        if resultados_vuelos["vuelta"]:
            vuelos_vuelta = procesar_vuelos(resultados_vuelos["vuelta"].get("flightOffers", []))

        todos_vuelos = vuelos_ida + vuelos_vuelta
        df = preparar_dataframe(todos_vuelos)
        insertar_en_bigquery(df)

        # Enviar resultados al endpoint /vuelos
        try:
            if not df.empty:
                headers = {"Content-Type": "application/json"}
                payload = df.to_dict(orient="records")
                async with httpx.AsyncClient() as client:
                    await client.post(ENDPOINT_VUELOS_VUELTA, headers=headers, json=payload)
        except Exception as e:
            logging.warning(f"No se pudo enviar a /vuelos: {str(e)}")

        return {"fuente": "booking", "resultados": resultados_vuelos, "procesados": len(todos_vuelos)}

    except Exception as e:
        logging.exception("Fallo general en la ejecución de buscar_vuelos")
        return {"error": str(e)}