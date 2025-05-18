import os
from typing import Optional, List, Dict, Any

# Usaremos langchain.pydantic_v1 consistentemente como en tu ejemplo de hotels_finder
from langchain.pydantic_v1 import BaseModel, Field
from serpapi import GoogleSearch
from langchain_core.tools import tool
import json
import traceback

# --- Definición de la herramienta de Vuelos ---

class FlightsInput(BaseModel):
    """Inputs for finding flight information.""" # Descripción general de la clase
    departure_airport: str = Field(description='Mandatory. The IATA code of the departure airport. Example: "VLC" for Valencia.')
    arrival_airport: str = Field(description='Mandatory. The IATA code of the arrival airport. Example: "FCO" for Rome Fiumicino.')
    outbound_date: str = Field(description='Mandatory. The departure date in YYYY-MM-DD format. Example: "2025-05-15".')
    return_date: Optional[str] = Field(None, description='Optional. The return date in YYYY-MM-DD format for round trips. Example: "2025-05-20". If not provided for a round trip query, ask the user.')
    adults: int = Field(default=1, description='Number of adult passengers. Defaults to 1 if not specified by the user. Example: 1.')
    children: Optional[int] = Field(default=0, description='Optional. Number of children (typically age 2-11). Defaults to 0.')
    infants_in_seat: Optional[int] = Field(default=0, description='Optional. Number of infants occupying a seat. Defaults to 0.')
    infants_on_lap: Optional[int] = Field(default=0, description='Optional. Number of infants on an adult\'s lap (under age 2). Defaults to 0.')

class FlightsInputSchema(BaseModel):
    """
    Wrapper for the flight search parameters.
    The 'params' field must contain all necessary details for the flight search.
    """
    params: FlightsInput = Field(description="Must be a valid JSON object containing all flight search parameters as defined in FlightsInput.")


@tool(args_schema=FlightsInputSchema)
def flights_finder(params: FlightsInput) -> List[Dict[str, Any]]:
    '''Tool to find flight information.
    Use this tool when a user asks for flight details.
    Ensure all mandatory parameters (departure_airport, arrival_airport, outbound_date) are extracted from the user query.
    If any mandatory parameter is missing, you MUST ask the user for it before calling this tool.
    The current year is 2025. Dates must be in YYYY-MM-DD format.
    Example of a valid call: {"params": {"departure_airport": "VLC", "arrival_airport": "FCO", "outbound_date": "2025-05-15", "return_date": "2025-05-20", "adults": 1}}
    '''
    print(f"[flights_finder] Recibiendo la instancia de FlightsInput: {params}")

    # Pydantic ya ha realizado la validación de tipos y campos obligatorios
    # si la instancia `params` se ha creado correctamente.
    # El error 'params value is not a valid dict' significa que 'params' en sí mismo no era un dict.
    # La instancia `params: FlightsInput` aquí ya es el objeto validado.

    api_params = {
        'api_key': os.environ.get('SERPAPI_API_KEY'),
        'engine': 'google_flights',
        'hl': 'en',
        'gl': 'us',
        'currency': 'USD',
        'departure_id': params.departure_airport,
        'arrival_id': params.arrival_airport,
        'outbound_date': params.outbound_date,
        'adults': params.adults, # Pydantic se encarga del default
    }

    if params.return_date:
        api_params['return_date'] = params.return_date
    if params.children is not None and params.children > 0:
        api_params['children'] = params.children
    if params.infants_in_seat is not None and params.infants_in_seat > 0:
        api_params['infants_in_seat'] = params.infants_in_seat
    if params.infants_on_lap is not None and params.infants_on_lap > 0:
        api_params['infants_on_lap'] = params.infants_on_lap

    print(f"[flights_finder] Parámetros para SerpApi: {api_params}")

    try:
        search = GoogleSearch(api_params)
        results_dict = search.get_dict()
        # print(f"[flights_finder DEBUG] Respuesta completa de SerpApi:\n{json.dumps(results_dict, indent=2)}")

        processed_flights = []
        flights_list = results_dict.get('best_flights') or \
                       results_dict.get('other_flights') or \
                       results_dict.get('flights')

        if flights_list and isinstance(flights_list, list):
            print(f"[flights_finder] Encontrados {len(flights_list)} vuelos en la lista cruda.")
            for flight_data in flights_list[:5]:
                if not isinstance(flight_data, dict): continue

                price = flight_data.get('price', 'N/A')
                price_str = f"${price}" if isinstance(price, int) else str(price)
                flight_type = flight_data.get('type', 'N/A')
                total_duration = flight_data.get('total_duration', flight_data.get('duration', 'N/A'))
                
                main_leg_info = flight_data.get('flights')
                departure_airport_info = {}
                arrival_airport_info = {}
                airline = flight_data.get('airline', 'N/A')
                stops_str = "N/A"

                if isinstance(main_leg_info, list) and main_leg_info:
                    first_leg = main_leg_info[0]
                    departure_airport_info = first_leg.get('departure_airport', {})
                    arrival_airport_info = main_leg_info[-1].get('arrival_airport', {})
                    if not airline or airline == 'N/A': airline = first_leg.get('airline', 'N/A')
                    num_stops = len(main_leg_info) - 1
                    stops_str = "Directo" if num_stops == 0 else f"{num_stops} parada(s)"
                else:
                    departure_airport_info = flight_data.get('departure_airport', {})
                    arrival_airport_info = flight_data.get('arrival_airport', {})
                    num_stops = flight_data.get('stops')
                    if isinstance(num_stops, int): stops_str = "Directo" if num_stops == 0 else f"{num_stops} parada(s)"
                    elif flight_data.get('layovers'): stops_str = f"{len(flight_data['layovers'])} parada(s)"

                booking_link = flight_data.get('booking_link') or \
                               (flight_data.get('booking_options') and \
                                isinstance(flight_data['booking_options'], list) and \
                                flight_data['booking_options'] and \
                                isinstance(flight_data['booking_options'][0], dict) and \
                                flight_data['booking_options'][0].get('link')) or \
                               flight_data.get('link')

                processed_flights.append({
                    "type": flight_type, "price": price_str, "total_duration": total_duration,
                    "departure_airport": f"{departure_airport_info.get('name', 'N/A')} ({departure_airport_info.get('id', 'N/A')})",
                    "departure_time": departure_airport_info.get('time', 'N/A'),
                    "arrival_airport": f"{arrival_airport_info.get('name', 'N/A')} ({arrival_airport_info.get('id', 'N/A')})",
                    "arrival_time": arrival_airport_info.get('time', 'N/A'),
                    "airline": airline, "stops_details": stops_str,
                    "travel_class": flight_data.get('travel_class', 'N/A'),
                    "booking_link": booking_link if booking_link else "No disponible"
                })
            
            if processed_flights:
                print(f"[flights_finder] Vuelos procesados: {len(processed_flights)}")
                return processed_flights
            
            search_info = results_dict.get('search_information', {})
            if search_info.get('flights_results_state') == "Fully empty":
                return [{"message": "No se encontraron vuelos para los criterios especificados."}]
            return [{"error": "No se encontraron vuelos procesables en la respuesta de la API, aunque la lista de vuelos podría no estar vacía."}]
        else:
            error_message = results_dict.get('error')
            if error_message:
                print(f"[flights_finder] Error de SerpApi: {error_message}")
                return [{"error": f"Error de la API de vuelos: {error_message}"}]
            
            search_info = results_dict.get('search_information', {})
            if search_info.get('flights_results_state') == "Fully empty":
                 print(f"[flights_finder] No se encontraron vuelos según SerpApi. Estado: {search_info.get('flights_results_state')}")
                 return [{"message": "No se encontraron vuelos para los criterios especificados."}]

            print(f"[flights_finder] No se encontró una lista de vuelos válida en la respuesta de SerpApi. Respuesta (primeros 500 chars): {json.dumps(results_dict, indent=2)[:500]}...")
            return [{"error": "No se encontró la lista de vuelos en la respuesta de la API. La estructura podría haber cambiado o no hay vuelos."}]

    except Exception as e:
        print(f"[flights_finder ERROR] Excepción al buscar vuelos: {e}")
        traceback.print_exc()
        return [{"error": f"Excepción en la herramienta de búsqueda de vuelos: {str(e)}"}]