# vuelos.py

import os
import requests
import json
import traceback
from typing import Optional, List, Dict, Any, Union # Añadido Union

# --- Autenticación con Google ---
import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token

# --- Langchain ---
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool

# --- Definición de la Cloud Function de Vuelos y su llamada ---
FLIGHTS_CF_URL = "https://europe-west1-dataproject3-458310.cloudfunctions.net/vuelos"

def llamar_api_vuelos_cf(payload_data: Dict[str, Any], authenticated: bool = True) -> Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]: # Tipo de retorno ajustado
    """
    Llama a la Cloud Function 'vuelos'.
    Devuelve el JSON parseado de la respuesta o un dict de error.
    """
    headers = {"Content-Type": "application/json"}
    if authenticated:
        try:
            creds, project = google.auth.default(scopes=['openid', 'email', 'profile'])
            auth_req = google.auth.transport.requests.Request()
            identity_token = id_token.fetch_id_token(auth_req, FLIGHTS_CF_URL)
            headers["Authorization"] = f"Bearer {identity_token}"
        except Exception as e:
            print(f"[llamar_api_vuelos_cf ERROR] Error obteniendo credenciales o token: {e}")
            print("[llamar_api_vuelos_cf] Intentando llamar sin autenticación.")

    try:
        response = requests.post(FLIGHTS_CF_URL, json=payload_data, headers=headers, timeout=120)
        if response.status_code == 200:
            try:
                response_json = response.json()
                # Imprimir aquí la respuesta cruda para depuración es MUY útil
                print(f"[llamar_api_vuelos_cf DEBUG] Respuesta JSON CRUDA de la CF (Vuelos):\n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
                return response_json # Devuelve el JSON parseado directamente
            except requests.exceptions.JSONDecodeError:
                print(f"[llamar_api_vuelos_cf ERROR] Respuesta no es JSON. Texto: {response.text[:500]}")
                return {"error_raw_text": f"API de vuelos devolvió contenido no JSON (status {response.status_code}). Resp: {response.text[:200]}"}
        else:
            error_text = response.text
            print(f"[llamar_api_vuelos_cf ERROR] Error en API vuelos. Status: {response.status_code}. Resp: {error_text[:500]}")
            try:
                error_json = response.json()
                if isinstance(error_json, dict) and "error" in error_json: return {"error_api_details": error_json} # Devuelve el error de la API
                if isinstance(error_json, dict) and "message" in error_json: return {"error_api_message": error_json["message"]}
            except requests.exceptions.JSONDecodeError: pass
            return {"error_api_status": f"Error API vuelos (status {response.status_code}). Resp: {error_text[:200]}"}
    except requests.exceptions.Timeout:
        print(f"[llamar_api_vuelos_cf ERROR] Timeout llamando a {FLIGHTS_CF_URL}.")
        return {"error_request_timeout": f"Timeout llamando a API de vuelos."}
    except requests.exceptions.RequestException as e:
        print(f"[llamar_api_vuelos_cf ERROR] Excepción en la petición: {e}")
        return {"error_request_exception": f"Error de conexión llamando a API de vuelos: {str(e)}"}
    except Exception as e:
        print(f"[llamar_api_vuelos_cf ERROR] Excepción inesperada: {e}")
        traceback.print_exc()
        return {"error_unexpected_cf_call": f"Error inesperado al llamar a API de vuelos: {str(e)}"}

# --- Definición de Inputs para la Herramienta Langchain ---
class FlightsCloudInput(BaseModel):
    ciudad_origen: str = Field(description='Mandatory. The IATA code of the departure city/airport. Example: "MAD" for Madrid.')
    ciudad_destino: str = Field(description='Mandatory. The IATA code of the arrival city/airport. Example: "LHR" for London Heathrow.')
    fecha_salida: str = Field(description='Mandatory. The departure date in YYYY-MM-DD format. Example: "2025-12-01".')
    fecha_vuelta: str = Field(description='Mandatory. The return date in YYYY-MM-DD format. Required if tipo_de_viaje is 1 (round trip). Example: "2025-12-08".')
    adults: int = Field(default=1, description='Number of adult passengers. Defaults to 1. Example: 1.')
    cabin_class: Optional[str] = Field("ECONOMY", description='Optional. Cabin class. Examples: "ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST". Defaults to "ECONOMY".')
    tipo_de_viaje: int = Field(description='Mandatory. Type of trip: 0 for one-way, 1 for round trip. Example: 1.')

@tool(args_schema=FlightsCloudInput)
def flights_finder(
    ciudad_origen: str,
    ciudad_destino: str,
    fecha_salida: str,
    tipo_de_viaje: int,
    fecha_vuelta: Optional[str] = None,
    adults: Optional[int] = 1,
    cabin_class: Optional[str] = "ECONOMY"
) -> List[Dict[str, Any]]: # Mantenemos el tipo de retorno como List[Dict] para el agente
    '''Tool to find flight information using a custom Cloud Function.
    Returns the raw JSON data from the flight API.
    Provide departure city, arrival city, departure date, and trip type (0 for one-way, 1 for round trip).
    For round trips (tipo_de_viaje=1), a return date (fecha_vuelta) is also mandatory.
    Dates must be in YYYY-MM-DD format.
    '''
    print(f"[flights_finder CF RAW] Args: origen='{ciudad_origen}', destino='{ciudad_destino}', salida='{fecha_salida}', tipo_viaje={tipo_de_viaje}, vuelta='{fecha_vuelta}', adultos={adults}, cabina='{cabin_class}'")

    if tipo_de_viaje == 1 and not fecha_vuelta:
        # Devolver una lista con un diccionario de error, como esperan las herramientas
        return [{"error_validation": "Para un viaje de ida y vuelta (tipo_de_viaje=1), se requiere 'fecha_vuelta'."}]

    payload_cf = {
        "ciudad_origen": ciudad_origen,
        "ciudad_destino": ciudad_destino,
        "fecha_salida": fecha_salida,
        "adults": adults,
        "cabin_class": cabin_class,
        "tipo_de_viaje": tipo_de_viaje
    }
    if fecha_vuelta:
        payload_cf["fecha_vuelta"] = fecha_vuelta
    
    api_response_raw = llamar_api_vuelos_cf(payload_cf, authenticated=True)

    # Langchain tools suelen esperar una List[Dict[str, Any]] como resultado.
    # Si api_response_raw es un diccionario (ej. un error), lo envolvemos en una lista.
    # Si api_response_raw ya es una lista (de vuelos), la usamos directamente.
    # Si es None u otro tipo, devolvemos un error genérico.

    if isinstance(api_response_raw, list):
        if not api_response_raw: # Lista vacía de la API (sin vuelos encontrados)
            return [{"message": "No se encontraron vuelos para los criterios especificados."}]
        return api_response_raw # Devuelve la lista de vuelos cruda
    elif isinstance(api_response_raw, dict):
        # Si es un diccionario, probablemente sea un error o un mensaje estructurado de la CF.
        # Lo envolvemos en una lista para cumplir con el tipo de retorno esperado.
        return [api_response_raw] 
    elif api_response_raw is None: # Error crítico en la llamada a la CF
        return [{"error_critical_cf_call": "La llamada a la API de vuelos no devolvió respuesta."}]
    else:
        # Tipo inesperado
        return [{"error_unexpected_response_type": f"Respuesta inesperada de la API de vuelos. Tipo: {type(api_response_raw)}"}]
