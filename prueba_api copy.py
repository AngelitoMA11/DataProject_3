from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx
import os
import urllib.parse
import json
import ssl
import http.client

app = FastAPI()

# === Config RapidAPI ===
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "9630d11b3dmshc21bd0426b9a53cp153093jsn46cfb50160a1")
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

# === Modelos con campos iguales a los del formulario Streamlit ===
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

class HotelRequest(BaseModel):
    ciudad_destino: str
    fecha_entrada: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    fecha_salida: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    adults: int = Field(1, ge=1)
    rooms: int = Field(1, ge=1)
    currency: str = "EUR"

# === Funciones de apoyo ===
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
        "fromId": origin_id,
        "toId": destination_id,
        "departDate": req.fecha_salida,
        "stops": req.stops,
        "adults": str(req.adults),
        "children": req.children,
        "cabinClass": req.cabin_class,
        "currency_code": req.currency
    }
    if req.fecha_vuelta:
        params["returnDate"] = req.fecha_vuelta
    return params

# === Búsqueda de destino para hoteles ===
async def buscar_destino_hotel(client: httpx.AsyncClient, nombre_ciudad):
    query = urllib.parse.quote(nombre_ciudad)
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination?query={query}"
    
    resp = await client.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    
    data = resp.json()
    
    # Seleccionar el destino con más hoteles que NO sea un aeropuerto
    destinos_con_hoteles = [
        destino for destino in data.get("data", []) 
        if destino.get('hotels', 0) > 0 and destino.get('type') != 'ai'
    ]
    
    if destinos_con_hoteles:
        # Ordenar por número de hoteles y tomar el primero
        destino_seleccionado = max(destinos_con_hoteles, key=lambda x: x.get('hotels', 0))
        return destino_seleccionado["dest_id"], "CITY"
    
    return None, None

# === Endpoints ===
@app.post("/buscar-vuelo/")
async def buscar_vuelo(req: VueloRequest):
    async with httpx.AsyncClient() as client:
        # Vuelos de ida
        origin_id = await obtener_id_ciudad(client, req.ciudad_origen)
        destination_id = await obtener_id_ciudad(client, req.ciudad_destino)
        
        url = f"https://{RAPIDAPI_HOST}/api/v1/flights/searchFlights"
        
        # Vuelos de ida
        params_ida = construir_parametros_api_vuelo(req, origin_id, destination_id)
        resp_ida = await client.get(url, headers=HEADERS, params=params_ida, timeout=20)
        resp_ida.raise_for_status()
        vuelos_ida = resp_ida.json()
        
        # Vuelos de vuelta
        vuelos_vuelta = None
        if req.fecha_vuelta:
            req_vuelta = VueloRequest(
                ciudad_origen=req.ciudad_destino,
                ciudad_destino=req.ciudad_origen,
                fecha_salida=req.fecha_vuelta,
                fecha_vuelta=None,
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
        
        return {
            "ida": vuelos_ida["data"],
            "vuelta": vuelos_vuelta["data"] if vuelos_vuelta else None
        }

@app.post("/buscar-hotel/")
async def buscar_hotel(req: HotelRequest):
    async with httpx.AsyncClient() as client:
        # Buscar destino
        dest_id, search_type = await buscar_destino_hotel(client, req.ciudad_destino)
        
        if not dest_id or not search_type:
            raise HTTPException(status_code=404, detail="No se encontró el destino")
        
        # Parámetros para búsqueda de hoteles
        params = {
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": req.fecha_entrada,
            "departure_date": req.fecha_salida,
            "adults": str(req.adults),
            "room_qty": str(req.rooms),
            "page_number": "1",
            "currency_code": req.currency,
            "units": "metric",
            "temperature_unit": "c",
            "languagecode": "en-us"
        }
        
        url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchHotels"
        resp = await client.get(url, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()
        hoteles = resp.json()
        
        # Procesar y limpiar datos
        lista_hoteles = []
        for hotel in hoteles.get('data', {}).get('hotels', []):
            try:
                hotel_prop = hotel.get('property', {})
                precio = hotel_prop.get('priceBreakdown', {}).get('grossPrice', {})
                
                hotel_detalle = {
                    'nombre': hotel_prop.get('name', 'N/A'),
                    'precio': {
                        'valor': precio.get('value', 'N/A'),
                        'moneda': precio.get('currency', 'N/A')
                    },
                    'puntuacion': {
                        'nota': hotel_prop.get('reviewScore', 'N/A'),
                        'descripcion': hotel_prop.get('reviewScoreWord', 'N/A')
                    }
                }
                lista_hoteles.append(hotel_detalle)
            except Exception as e:
                print(f"Error procesando hotel: {e}")
        
        # Actualizar datos en la respuesta original
        hoteles['data']['hotels'] = lista_hoteles
        
        return hoteles