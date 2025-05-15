import os
import json
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from serpapi import GoogleSearch

app = FastAPI()

class FlightsRequest(BaseModel):
    departure_airport: str
    arrival_airport: str
    outbound_date: str
    return_date: str | None = None
    adults: int = 1
    children: int = 0
    infants_in_seat: int = 0
    infants_on_lap: int = 0

@app.post("/search-flights")
async def search_flights(request: FlightsRequest) -> Dict[str, Any]:
    """
    Cloud function endpoint to search for flights using SerpApi.
    """
    try:
        api_params = {
            'api_key': os.environ.get("SERPAPI_API_KEY"),
            'engine': 'google_flights',
            'hl': 'en',
            'gl': 'us',
            'currency': 'USD',
            'departure_id': request.departure_airport,
            'arrival_id': request.arrival_airport,
            'outbound_date': request.outbound_date,
            'adults': request.adults,
        }

        if request.return_date:
            api_params['return_date'] = request.return_date
        if request.children > 0:
            api_params['children'] = request.children
        if request.infants_in_seat > 0:
            api_params['infants_in_seat'] = request.infants_in_seat
        if request.infants_on_lap > 0:
            api_params['infants_on_lap'] = request.infants_on_lap

        search = GoogleSearch(api_params)
        results_dict = search.get_dict()

        processed_flights = []
        flights_list = results_dict.get('best_flights') or \
                      results_dict.get('other_flights') or \
                      results_dict.get('flights')

        if flights_list and isinstance(flights_list, list):
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
                    if not airline or airline == 'N/A': 
                        airline = first_leg.get('airline', 'N/A')
                    num_stops = len(main_leg_info) - 1
                    stops_str = "Directo" if num_stops == 0 else f"{num_stops} parada(s)"
                else:
                    departure_airport_info = flight_data.get('departure_airport', {})
                    arrival_airport_info = flight_data.get('arrival_airport', {})
                    num_stops = flight_data.get('stops')
                    if isinstance(num_stops, int): 
                        stops_str = "Directo" if num_stops == 0 else f"{num_stops} parada(s)"
                    elif flight_data.get('layovers'): 
                        stops_str = f"{len(flight_data['layovers'])} parada(s)"

                booking_link = flight_data.get('booking_link') or \
                             (flight_data.get('booking_options') and \
                              isinstance(flight_data['booking_options'], list) and \
                              flight_data['booking_options'] and \
                              isinstance(flight_data['booking_options'][0], dict) and \
                              flight_data['booking_options'][0].get('link')) or \
                             flight_data.get('link')

                processed_flights.append({
                    "type": flight_type,
                    "price": price_str,
                    "total_duration": total_duration,
                    "departure_airport": f"{departure_airport_info.get('name', 'N/A')} ({departure_airport_info.get('id', 'N/A')})",
                    "departure_time": departure_airport_info.get('time', 'N/A'),
                    "arrival_airport": f"{arrival_airport_info.get('name', 'N/A')} ({arrival_airport_info.get('id', 'N/A')})",
                    "arrival_time": arrival_airport_info.get('time', 'N/A'),
                    "airline": airline,
                    "stops_details": stops_str,
                    "travel_class": flight_data.get('travel_class', 'N/A'),
                    "booking_link": booking_link if booking_link else "No disponible"
                })
            
            if processed_flights:
                return {
                    "status": "success",
                    "data": processed_flights
                }
            
            search_info = results_dict.get('search_information', {})
            if search_info.get('flights_results_state') == "Fully empty":
                raise HTTPException(status_code=404, detail="No se encontraron vuelos para los criterios especificados.")
            
            raise HTTPException(status_code=404, detail="No se encontraron vuelos procesables en la respuesta de la API.")

        error_message = results_dict.get('error')
        if error_message:
            raise HTTPException(status_code=400, detail=f"Error de la API de vuelos: {error_message}")
        
        search_info = results_dict.get('search_information', {})
        if search_info.get('flights_results_state') == "Fully empty":
            raise HTTPException(status_code=404, detail="No se encontraron vuelos para los criterios especificados.")

        raise HTTPException(status_code=404, detail="No se encontró la lista de vuelos en la respuesta de la API.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 