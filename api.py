from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import httpx
import os
import urllib.parse
from google.cloud import pubsub_v1
import json

app = FastAPI()

# === Configuración ===
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "9630d11b3dmshc21bd0426b9a53cp153093jsn46cfb50160a1")
# Hosts para vuelos/hoteles y coches
FLIGHT_HOTEL_HOST = "booking-com15.p.rapidapi.com"
CAR_HOST = "booking-com18.p.rapidapi.com"

# Cabeceras para cada servicio
COMMON_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY
}
FLIGHT_HOTEL_HEADERS = {**COMMON_HEADERS, "x-rapidapi-host": FLIGHT_HOTEL_HOST}
CAR_HEADERS = {**COMMON_HEADERS, "x-rapidapi-host": CAR_HOST}

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "dataproject3-458310")
TOPIC_VUELOS = f"projects/{PROJECT_ID}/topics/vuelos"
TOPIC_HOTELES = f"projects/{PROJECT_ID}/topics/hoteles"
TOPIC_COHES = f"projects/{PROJECT_ID}/topics/coches"

publisher = pubsub_v1.PublisherClient()

def publicar_mensaje(topic_path: str, mensaje: dict):
    data = json.dumps(mensaje).encode("utf-8")
    future = publisher.publish(topic_path, data=data)
    return future.result()

# === Modelos de petición ===
class VueloRequest(BaseModel):
    ciudad_origen: str
    ciudad_destino_aeropuerto: str
    fecha_salida: str = Field(..., pattern=r"^\d{2}-\d{2}-\d{4}$")
    fecha_vuelta: str | None = Field(None, pattern=r"^\d{2}-\d{2}-\d{4}$")
    stops: str = "none"
    adults: int = Field(1, ge=1)
    children: str = "0"
    cabin_class: str = "ECONOMY"
    currency: str = "EUR"

class HotelRequest(BaseModel):
    ciudad_destino_vacaciones: str
    fecha_entrada: str
    fecha_salida: str
    rooms: int = 1

# === Auxiliares para vuelos y hoteles ===
async def obtener_id_ciudad(client: httpx.AsyncClient, ciudad: str) -> str:
    query = urllib.parse.quote(ciudad)
    url = f"https://{FLIGHT_HOTEL_HOST}/api/v1/flights/searchDestination?query={query}"
    resp = await client.get(url, headers=FLIGHT_HOTEL_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    for item in data:
        if "airport" in item.get("type", "").lower():
            return item["id"]
    raise HTTPException(404, detail=f"Aeropuerto no encontrado para {ciudad}")

async def obtener_id_destino_hotel(client: httpx.AsyncClient, ciudad: str):
    query = urllib.parse.quote(ciudad)
    url = f"https://{FLIGHT_HOTEL_HOST}/api/v1/hotels/searchDestination?query={query}"
    resp = await client.get(url, headers=FLIGHT_HOTEL_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if not data:
        raise HTTPException(404, detail=f"No se encontró ningún destino para '{ciudad}'")
    destino = max(data, key=lambda d: d.get("hotels", 0))
    return destino["dest_id"], destino["search_type"]

# === Auxiliar para coches ===
async def obtener_pickup_ids(client: httpx.AsyncClient, ciudad: str) -> list[str]:
    """
    Busca todos los IDs de tipo 'airport' para la ciudad indicada.
    Retorna una lista de IDs o lanza HTTPException si no encuentra ninguno.
    """
    query = urllib.parse.quote(ciudad)
    url = f"https://{CAR_HOST}/car/auto-complete?query={query}"
    resp = await client.get(url, headers=CAR_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    airport_ids = [item.get("id") for item in data if item.get("type", "").lower() == "airport"]
    if not airport_ids:
        raise HTTPException(404, detail=f"No se encontraron aeropuertos para {ciudad}")
    return airport_ids


# === Construcción de parámetros ===
def construir_parametros_api_vuelo(req: VueloRequest, origin_id: str, destination_id: str) -> dict:
    fecha_salida = "-".join(reversed(req.fecha_salida.split("-")))
    params = {
        "fromId": origin_id,
        "toId": destination_id,
        "departDate": fecha_salida,
        "stops": req.stops,
        "adults": str(req.adults),
        "children": req.children,
        "cabinClass": req.cabin_class,
        "currency_code": req.currency
    }
    return params

# === Endpoint principal ===
@app.post("/buscar/")
async def buscar_todo(request: Request):
    body = await request.json()
    resultados = {}

    async with httpx.AsyncClient() as client:
        # Vuelos
        if all(k in body for k in ["ciudad_origen", "ciudad_destino_aeropuerto", "fecha_salida"]):
            try:
                origin_id = await obtener_id_ciudad(client, body["ciudad_origen"])
                dest_id = await obtener_id_ciudad(client, body["ciudad_destino_aeropuerto"])
                vuelo_req = VueloRequest(**{k: body[k] for k in VueloRequest.model_fields if k in body})
                params_ida = construir_parametros_api_vuelo(vuelo_req, origin_id, dest_id)
                url_vuelo = f"https://{FLIGHT_HOTEL_HOST}/api/v1/flights/searchFlights"
                resp_ida = await client.get(url_vuelo, headers=FLIGHT_HOTEL_HEADERS, params=params_ida, timeout=20)
                resp_ida.raise_for_status()
                data_ida = resp_ida.json()
                vuelos_vuelta = None
                if body.get("fecha_vuelta"):
                    vuelo_vuelta = VueloRequest(
                        ciudad_origen=body["ciudad_destino_aeropuerto"],
                        ciudad_destino_aeropuerto=body["ciudad_origen"],
                        fecha_salida=body["fecha_vuelta"],
                        fecha_vuelta=None,
                        stops=body.get("stops", "none"),
                        adults=body.get("adults", 1),
                        children=body.get("children", "0"),
                        cabin_class=body.get("cabin_class", "ECONOMY"),
                        currency=body.get("currency", "EUR")
                    )
                    params_vuelta = construir_parametros_api_vuelo(vuelo_vuelta, dest_id, origin_id)
                    resp_vuelta = await client.get(url_vuelo, headers=FLIGHT_HOTEL_HEADERS, params=params_vuelta, timeout=20)
                    resp_vuelta.raise_for_status()
                    vuelos_vuelta = resp_vuelta.json()
                resultados["vuelos"] = {"fuente": "booking", "resultados": {"ida": data_ida["data"], "vuelta": vuelos_vuelta["data"] if vuelos_vuelta else None}}
                publicar_mensaje(TOPIC_VUELOS, resultados["vuelos"]["resultados"])
            except Exception as e:
                resultados["vuelos"] = {"error": str(e)}

        # Hoteles
        if all(k in body for k in ["ciudad_destino_vacaciones", "fecha_salida", "fecha_vuelta"]):
            try:
                dest_id, search_type = await obtener_id_destino_hotel(client, body["ciudad_destino_vacaciones"])
                hotel_req = HotelRequest(
                    ciudad_destino_vacaciones=body["ciudad_destino_vacaciones"],
                    fecha_entrada=body["fecha_salida"],
                    fecha_salida=body["fecha_vuelta"],
                    rooms=body.get("rooms", 1)
                )
                params_hotel = {
                    "dest_id": dest_id,
                    "search_type": search_type,
                    "arrival_date": "-".join(reversed(hotel_req.fecha_entrada.split("-"))),
                    "departure_date": "-".join(reversed(hotel_req.fecha_salida.split("-"))),
                    "room_qty": str(hotel_req.rooms)
                }
                url_hotel = f"https://{FLIGHT_HOTEL_HOST}/api/v1/hotels/searchHotels"
                resp_hotel = await client.get(url_hotel, headers=FLIGHT_HOTEL_HEADERS, params=params_hotel, timeout=20)
                resp_hotel.raise_for_status()
                data_hoteles = resp_hotel.json()
                resultados["hoteles"] = {"fuente": "booking", "resultados": data_hoteles}
                publicar_mensaje(TOPIC_HOTELES, resultados["hoteles"]["resultados"])
            except Exception as e:
                resultados["hoteles"] = {"error": str(e)}

        # Coches
        if all(key in body for key in ["ciudad_destino_aeropuerto", "fecha_salida", "fecha_vuelta"]):
            try:
                pickup_ids = await obtener_pickup_ids(client, body["ciudad_destino_aeropuerto"])  # noqa: E1101
                resultados_coches = []
                pick_up_date = "-".join(reversed(body["fecha_salida"].split("-")))
                drop_off_date = "-".join(reversed(body["fecha_vuelta"].split("-")))
                pick_up_time = "10:00"
                drop_off_time = "10:00"

                # Para cada aeropuerto, realizar búsqueda y publicar individualmente
                for pid in pickup_ids:
                    params_car = {
                        "pickUpId": pid,
                        "pickUpDate": pick_up_date,
                        "pickUpTime": pick_up_time,
                        "dropOffDate": drop_off_date,
                        "dropOffTime": drop_off_time
                    }
                    url_car = f"https://{CAR_HOST}/car/search"
                    resp_car = await client.get(url_car, headers=CAR_HEADERS, params=params_car, timeout=20)
                    resp_car.raise_for_status()
                    data_coches = resp_car.json()

                    # Construir mensaje con ciudad y resultados
                    mensaje_car = {
                        "ciudad_destino_aeropuerto": body["ciudad_destino_aeropuerto"],
                        "pickUpId": pid,
                        "resultados": data_coches
                    }
                    # Publicar en Pub/Sub
                    publicar_mensaje(TOPIC_COHES, mensaje_car)

                    # Agregar al array de resultados finales
                    resultados_coches.append(mensaje_car)

                resultados["coches"] = {
                    "ciudad_destino_aeropuerto": body["ciudad_destino_aeropuerto"],
                    "fuente": "booking",
                    "resultados_por_aeropuerto": resultados_coches
                }
            except Exception as e:
                resultados["coches"] = {"error": str(e)}

    return resultados