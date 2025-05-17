import os
from typing import Optional, List, Dict, Any
from langgraph.prebuilt import ToolNode
from langchain.pydantic_v1 import BaseModel, Field
from serpapi import GoogleSearch
import json
import traceback

class HotelsInput(BaseModel):
    q: str = Field(description='Location of the hotel')
    check_in_date: str = Field(description='Check-in date. The format is YYYY-MM-DD. e.g. 2024-06-22')
    check_out_date: str = Field(description='Check-out date. The format is YYYY-MM-DD. e.g. 2024-06-28')
    sort_by: Optional[str] = Field("3", description='Parameter is used for sorting the results. 3 is sort by pricing. 8 is sort by rating. and 13 is sort by most reviews.')
    adults: Optional[int] = Field(1, description='Number of adults. Default to 1.')
    children: Optional[int] = Field(0, description='Number of children. Default to 0.')
    rooms: Optional[int] = Field(1, description='Number of rooms. Default to 1.')
    hotel_class: Optional[str] = Field(None, description='Parameter defines to include only certain hotel class in the results. for example- 2,3,4')

def hotels_finder(params: HotelsInput) -> List[Dict[str, Any]]:
    '''
    Find hotels using the Google Hotels engine via SerpApi.
    Returns a list of hotel details.
    '''
    print(f"[hotels_finder] Recibiendo parámetros para la tool: {params}")

    api_params = {
        'api_key': os.environ.get('SERPAPI_API_KEY'),
        'engine': 'google_hotels',
        'hl': 'en',
        'gl': 'us',
        'q': params.q,
        'check_in_date': params.check_in_date,
        'check_out_date': params.check_out_date,
        'currency': 'USD',
        'adults': params.adults,
        'num_rooms': params.rooms,
        'sort_by': params.sort_by,
    }

    if params.children is not None and params.children > 0:
        print(f"  Advertencia: El parámetro 'children' ({params.children}) podría necesitar un formato específico como 'children_ages' para SerpApi Google Hotels.")

    if params.hotel_class:
        api_params['hotel_class'] = params.hotel_class

    print(f"[hotels_finder] Parámetros para SerpApi: {api_params}")

    try:
        search = GoogleSearch(api_params)
        results_dict = search.get_dict()

        processed_hotels = []
        hotels_list = results_dict.get('properties')
        if not hotels_list and results_dict.get('hotels_results'):
            hotels_list = results_dict.get('hotels_results')
        
        if hotels_list and isinstance(hotels_list, list):
            print(f"[hotels_finder] Encontrados {len(hotels_list)} hoteles en la lista cruda.")
            for hotel_data in hotels_list[:5]:
                if not isinstance(hotel_data, dict): continue

                name = hotel_data.get('name', 'Nombre no disponible')
                price_str = hotel_data.get('price')
                total_price_str = hotel_data.get('total_price')
                rate_breakdown = hotel_data.get('rate_per_night', {}).get('extracted_price')
                
                price_info = "Precio no disponible"
                if price_str:
                    price_info = price_str
                elif rate_breakdown:
                    price_info = f"${rate_breakdown} por noche (aprox)"

                if total_price_str:
                    price_info += f" (Total: {total_price_str})"

                rating = hotel_data.get('overall_rating', 'N/A')
                reviews = hotel_data.get('reviews', 'N/A')
                link = hotel_data.get('link')

                description = hotel_data.get('type', hotel_data.get('description', ''))
                if isinstance(description, list): description = ', '.join(description)

                processed_hotels.append({
                    "name": name,
                    "price_info": price_info,
                    "rating": f"{rating} ({reviews} reviews)" if rating != 'N/A' else "N/A",
                    "description": description[:150] + "..." if description and len(description) > 150 else description,
                    "link": link
                })
            
            if processed_hotels:
                print(f"[hotels_finder] Hoteles procesados: {len(processed_hotels)}")
                return processed_hotels
            else:
                print("[hotels_finder] La lista de hoteles estaba vacía o no se pudieron procesar.")
                return [{"error": "No se encontraron hoteles procesables en la respuesta de la API."}]

        else:
            error_message = results_dict.get('error')
            if error_message:
                print(f"[hotels_finder] Error de SerpApi: {error_message}")
                return [{"error": f"Error de la API de hoteles: {error_message}"}]
            
            print(f"[hotels_finder] No se encontró la lista de hoteles en la respuesta. Respuesta: {json.dumps(results_dict, indent=2)[:500]}...")
            return [{"error": "No se encontró la lista de hoteles en la respuesta de la API. La estructura podría haber cambiado."}]

    except Exception as e:
        print(f"[hotels_finder ERROR] Excepción al buscar hoteles: {e}")
        traceback.print_exc()
        return [{"error": f"Excepción en la herramienta de búsqueda de hoteles: {str(e)}"}]

# Create LangGraph tool
hotels_tool = ToolNode(
    name="hotels_finder",
    description="Find hotels using the Google Hotels engine via SerpApi. Returns a list of hotel details.",
    function=hotels_finder,
    input_schema=HotelsInput
)