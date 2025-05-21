# hoteles.py

import os
import requests
import json
import traceback
from typing import Optional, List, Dict, Any

import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token

from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool

CLOUD_FUNCTION_URL = "https://europe-west1-dataproject3-458310.cloudfunctions.net/hoteles"

def llamar_api_hoteles_cf(payload_data: Dict[str, Any], authenticated: bool = True) -> Optional[Dict[str, Any]]:
    headers = {
        "Content-Type": "application/json"
    }
    if authenticated:
        try:
            creds, project = google.auth.default(scopes=['openid', 'email', 'profile'])
            auth_req = google.auth.transport.requests.Request()
            identity_token = id_token.fetch_id_token(auth_req, CLOUD_FUNCTION_URL)
            headers["Authorization"] = f"Bearer {identity_token}"
        except Exception as e:
            print(f"[llamar_api_hoteles_cf ERROR] Error obteniendo credenciales o token: {e}")
            print("[llamar_api_hoteles_cf] Intentando llamar sin autenticación (puede fallar si es requerida).")
    try:
        response = requests.post(CLOUD_FUNCTION_URL, json=payload_data, headers=headers, timeout=60)
        if response.status_code == 200:
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                print(f"[llamar_api_hoteles_cf ERROR] Respuesta no es JSON. Texto: {response.text[:500]}")
                return {"error_raw_text": f"La API devolvió un contenido no JSON (status {response.status_code}). Respuesta: {response.text[:200]}"}
        else:
            # ... (manejo de errores sin cambios) ...
            error_text = response.text
            print(f"[llamar_api_hoteles_cf ERROR] Error en la API. Status: {response.status_code}. Respuesta: {error_text[:500]}")
            try:
                error_json = response.json()
                if isinstance(error_json, dict) and "error" in error_json: return {"error_api": f"Error de la API (status {response.status_code}): {error_json['error']}"}
                if isinstance(error_json, dict) and "message" in error_json: return {"error_api": f"Error de la API (status {response.status_code}): {error_json['message']}"}
            except requests.exceptions.JSONDecodeError: pass
            return {"error_api": f"Error de la API (status {response.status_code}). Respuesta: {error_text[:200]}"}
    except requests.exceptions.RequestException as e:
        print(f"[llamar_api_hoteles_cf ERROR] Excepción en la petición: {e}")
        return {"error_request": f"Error de conexión llamando a la API: {str(e)}"}
    except Exception as e:
        print(f"[llamar_api_hoteles_cf ERROR] Excepción inesperada: {e}")
        traceback.print_exc()
        return {"error_unexpected": f"Error inesperado al llamar a la API: {str(e)}"}


class HotelsFinderCloudInput(BaseModel):
    ciudad: str = Field(description='Location (city) of the hotel. e.g., "París", "Nueva York"')
    fecha_entrada: str = Field(description='Check-in date. The format is YYYY-MM-DD. e.g. "2025-05-21"')
    fecha_vuelta: str = Field(description='Check-out date. The format is YYYY-MM-DD. e.g. "2025-05-25"')
    adults: Optional[int] = Field(1, description='Number of adults. Default to 1.')
    max_price: Optional[float] = Field(None, description='Maximum total price for the stay. e.g., 250.0')
    valoracion: Optional[float] = Field(None, description='Minimum hotel rating (e.g., 4.0 for 4 stars and above).')

@tool(args_schema=HotelsFinderCloudInput)
def hotels_finder(
    ciudad: str,
    fecha_entrada: str,
    fecha_vuelta: str,
    adults: Optional[int] = 1,
    max_price: Optional[float] = None,
    valoracion: Optional[float] = None
) -> List[Dict[str, Any]]:
    '''
    Finds hotels using a custom Google Cloud Function.
    Provide the city, check-in date (YYYY-MM-DD), and check-out date (YYYY-MM-DD).
    Optionally, specify adults, max_price, and valoracion.
    Returns a list of hotel details: name, price, rating, and hotel's check-in/out dates.
    '''
    print(f"[hotels_finder] Args recibidos: ciudad='{ciudad}', fecha_entrada='{fecha_entrada}', fecha_vuelta='{fecha_vuelta}', adults={adults}, max_price={max_price}, valoracion={valoracion}")

    payload_cf = {
        "ciudad": ciudad,
        "fecha_entrada": fecha_entrada,
        "fecha_vuelta": fecha_vuelta,
        "adults": adults
    }
    if adults is not None: payload_cf["adults"] = adults
    if max_price is not None: payload_cf["max_price"] = max_price
    if valoracion is not None: payload_cf["valoracion"] = valoracion
    
    api_response = llamar_api_hoteles_cf(payload_cf, authenticated=True) 

    if api_response is None: return [{"error": "Error crítico al contactar el servicio de hoteles."}]
    if "error_request" in api_response: return [{"error": api_response["error_request"]}]
    if "error_api" in api_response: return [{"error": api_response["error_api"]}]
    if "error_raw_text" in api_response: return [{"error": api_response["error_raw_text"]}]
    if "error_unexpected" in api_response: return [{"error": api_response["error_unexpected"]}]
    
    processed_hotels = []
    if isinstance(api_response, list):
        hotels_list_from_cf = api_response
        if not hotels_list_from_cf: return [{"message": "No se encontraron hoteles que coincidan."}]

        for i, hotel_data in enumerate(hotels_list_from_cf):
            if not isinstance(hotel_data, dict):
                continue
            name = hotel_data.get('Nombre') 
            price_total_value = hotel_data.get('PrecioTotal')
            rating_value = hotel_data.get('Puntuación')
            fecha_entrada_api = hotel_data.get('FechaEntrada')
            fecha_salida_api = hotel_data.get('FechaSalida')
            hotel_url = hotel_data.get('URL')
            hotel_images = hotel_data.get('Imagenes')

            if name and price_total_value is not None and rating_value is not None:
                price_info = f"Total: {price_total_value}"
                rating_str = "N/A"
                if rating_value is not None:
                    try: rating_str = f"{float(rating_value):.1f}"
                    except (ValueError, TypeError): rating_str = str(rating_value)
                
                hotel_output = { "name": name, "price_info": price_info, "rating": rating_str }
                if fecha_entrada_api: hotel_output["hotel_check_in_date"] = fecha_entrada_api
                if fecha_salida_api: hotel_output["hotel_check_out_date"] = fecha_salida_api
                if hotel_url: 
                    hotel_output["url"] = hotel_url
                if hotel_images and isinstance(hotel_images, list):
                    hotel_output["images"] = hotel_images
                processed_hotels.append(hotel_output)
        
        if processed_hotels: return processed_hotels
        else: return [{"message": "No se encontraron hoteles con información completa que coincidan con los criterios."}]
    elif isinstance(api_response, dict): 
        if "error" in api_response: return [{"error": f"API error: {api_response['error']}"}]
        if "message" in api_response: return [{"message": api_response['message']}]
        return [{"error": "Respuesta dict inesperada de la API."}]
    else: 
        return [{"error": "Respuesta API inesperada/mal formateada."}]