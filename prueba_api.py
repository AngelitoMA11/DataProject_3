from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx
import os
import urllib.parse
import json

app = FastAPI()

# === Config RapidAPI ===
RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY", "9630d11b3dmshc21bd0426b9a53cp153093jsn46cfb50160a1")
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

# === Modelo con campos iguales a los del formulario Streamlit ===
class VueloRequest(BaseModel):
    ciudad_origen: str
    ciudad_destino: str
    fecha_salida: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    fecha_vuelta: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    stops: str = "none"
    adults: int = Field(1, ge=1)
    children: str = "0"
    cabin_class: str = "ECONOMY"
    currency: str = "EUR"

# === Resolver IDs de ciudad ===
async def obtener_id_ciudad(client: httpx.AsyncClient, ciudad: str) -> str:
    query = urllib.parse.quote(ciudad)
    url = f"https://{RAPIDAPI_HOST}/api/v1/flights/searchDestination?query={query}"
    resp = await client.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    for item in data:
        if "airport" in item.get("type", "").lower():
            return item["id"]

    raise HTTPException(404, detail=f"Aeropuerto no encontrado para {ciudad}")

def construir_parametros_api_vuelo(req: VueloRequest, origin_id: str, destination_id: str) -> dict:
    params = {
        "fromId":        origin_id,
        "toId":          destination_id,
        "departDate":    req.fecha_salida,
        "stops":         req.stops,
        "adults":        str(req.adults),
        "children":      req.children,
        "cabinClass":    req.cabin_class,
        "currency_code": req.currency
    }
    if req.fecha_vuelta:
        params["returnDate"] = req.fecha_vuelta
    return params

@app.post("/buscar-vuelo/")
async def buscar_vuelo(req: VueloRequest):
    async with httpx.AsyncClient() as client:
        origin_id = await obtener_id_ciudad(client, req.ciudad_origen)
        destination_id = await obtener_id_ciudad(client, req.ciudad_destino)
        url = f"https://{RAPIDAPI_HOST}/api/v1/flights/searchFlights"

        # Vuelos de ida
        params_ida = construir_parametros_api_vuelo(req, origin_id, destination_id)
        resp_ida = await client.get(url, headers=HEADERS, params=params_ida, timeout=20)
        resp_ida.raise_for_status()
        vuelos_ida = resp_ida.json()

        # Vuelos de vuelta
        req_vuelta = VueloRequest(
            ciudad_origen=req.ciudad_destino,
            ciudad_destino=req.ciudad_origen,
            fecha_salida=req.fecha_vuelta,
            fecha_vuelta=None,  # Ya no hace falta
            stops=req.stops,
            adults=req.adults,
            children=req.children,
            cabin_class=req.cabin_class,
            currency=req.currency
        )
        params_vuelta = construir_parametros_api_vuelo(req_vuelta, destination_id, origin_id)
        resp_vuelta = await client.get(url, headers=HEADERS, params=params_vuelta, timeout=20)
        resp_vuelta.raise_for_status()
        vuelos_vuelta = resp_vuelta.json()

        # Fusión del resultado
        return {
            "ida": vuelos_ida["data"],      # solo el campo que te interesa
            "vuelta": vuelos_vuelta["data"]
        }

