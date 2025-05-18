import os
from typing import Optional, List, Dict, Any # Añadir List, Dict, Any

from serpapi import GoogleSearch # Cambiado de serpapi directo a GoogleSearch
from langchain.pydantic_v1 import BaseModel, Field # O from pydantic import BaseModel, Field
from langchain_core.tools import tool
import json # Para imprimir
import traceback # Para depurar

# ... (tus clases HotelsInput y HotelsInputSchema sin cambios) ...
class HotelsInput(BaseModel):
    q: str = Field(description='Location of the hotel')
    check_in_date: str = Field(description='Check-in date. The format is YYYY-MM-DD. e.g. 2024-06-22')
    check_out_date: str = Field(description='Check-out date. The format is YYYY-MM-DD. e.g. 2024-06-28')
    sort_by: Optional[str] = Field("3", description='Parameter is used for sorting the results. 3 is sort by pricing. 8 is sort by rating. and 13 is sort by most reviews.') # Dar un valor por defecto útil
    adults: Optional[int] = Field(1, description='Number of adults. Default to 1.')
    children: Optional[int] = Field(0, description='Number of children. Default to 0.')
    rooms: Optional[int] = Field(1, description='Number of rooms. Default to 1.')
    hotel_class: Optional[str] = Field(None, description='Parameter defines to include only certain hotel class in the results. for example- 2,3,4')

class HotelsInputSchema(BaseModel):
    params: HotelsInput


@tool(args_schema=HotelsInputSchema)
def hotels_finder(params: HotelsInput) -> List[Dict[str, Any]]: # Cambiar el tipo de retorno
    '''
    Find hotels using the Google Hotels engine via SerpApi.
    Returns a list of hotel details.
    '''
    print(f"[hotels_finder] Recibiendo parámetros para la tool: {params}")

    # Asegúrate de que los parámetros se pasen correctamente a SerpApi
    # El `params` que recibe la función es una instancia de HotelsInput
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
        'num_rooms': params.rooms, # El parámetro de SerpApi podría ser 'num_rooms'
        'sort_by': params.sort_by,
    }
    # Añadir children y hotel_class solo si tienen valor
    if params.children is not None and params.children > 0: # SerpApi espera un string para children_ages
        # Google Hotels en SerpApi a veces espera `children_ages`
        # Por simplicidad, si solo es número de niños, podría no ser directamente soportado así.
        # Consulta la documentación de SerpApi para Google Hotels y el parámetro `children`.
        # Podría ser algo como `children_ages=10,5` (si tienes las edades) o un formato específico.
        # Si solo tienes el número de niños, puede que tengas que omitirlo o encontrar el parámetro correcto.
        # api_params['children_num'] = params.children # Ejemplo, verifica el nombre correcto
        print(f"  Advertencia: El parámetro 'children' ({params.children}) podría necesitar un formato específico como 'children_ages' para SerpApi Google Hotels.")

    if params.hotel_class:
        api_params['hotel_class'] = params.hotel_class # Asegúrate que sea el nombre correcto, ej. 'htl_class'

    print(f"[hotels_finder] Parámetros para SerpApi: {api_params}")

    try:
        search = GoogleSearch(api_params)
        results_dict = search.get_dict() # Obtener el diccionario completo

        # print(f"[hotels_finder DEBUG] Respuesta completa de SerpApi:\n{json.dumps(results_dict, indent=2)}") # Descomentar para depurar

        processed_hotels = []
        
        # La estructura de la respuesta de 'google_hotels' puede variar.
        # Comúnmente, los hoteles están en 'properties' o a veces en 'hotels_results'.
        # También puede haber una sección 'knowledge_graph' para un hotel específico si la búsqueda es muy precisa.

        hotels_list = results_dict.get('properties') # Intenta con 'properties'
        if not hotels_list and results_dict.get('hotels_results'): # Fallback a 'hotels_results'
            hotels_list = results_dict.get('hotels_results')
        
        if hotels_list and isinstance(hotels_list, list):
            print(f"[hotels_finder] Encontrados {len(hotels_list)} hoteles en la lista cruda.")
            for hotel_data in hotels_list[:5]: # Tomar los primeros 5
                if not isinstance(hotel_data, dict): continue

                name = hotel_data.get('name', 'Nombre no disponible')
                price_str = hotel_data.get('price') # Suele ser un string como "$123"
                total_price_str = hotel_data.get('total_price') # A veces disponible
                rate_breakdown = hotel_data.get('rate_per_night', {}).get('extracted_price') # Otra forma de obtener precio
                
                price_info = "Precio no disponible"
                if price_str:
                    price_info = price_str
                elif rate_breakdown:
                    price_info = f"${rate_breakdown} por noche (aprox)" # Asumir USD si no hay moneda

                # Para el total, si existe
                if total_price_str:
                    price_info += f" (Total: {total_price_str})"


                rating = hotel_data.get('overall_rating', 'N/A') # O 'rating'
                reviews = hotel_data.get('reviews', 'N/A')
                link = hotel_data.get('link') # Puede que no siempre esté

                # La descripción o tipo
                description = hotel_data.get('type', hotel_data.get('description', ''))
                if isinstance(description, list): description = ', '.join(description)


                processed_hotels.append({
                    "name": name,
                    "price_info": price_info,
                    "rating": f"{rating} ({reviews} reviews)" if rating != 'N/A' else "N/A",
                    "description": description[:150] + "..." if description and len(description) > 150 else description, # Acortar descripciones largas
                    "link": link
                })
            
            if processed_hotels:
                print(f"[hotels_finder] Hoteles procesados: {len(processed_hotels)}")
                return processed_hotels
            else:
                print("[hotels_finder] La lista de hoteles estaba vacía o no se pudieron procesar.")
                return [{"error": "No se encontraron hoteles procesables en la respuesta de la API."}]

        else:
            # Si no hay 'properties' ni 'hotels_results', podría haber un error o una estructura diferente
            error_message = results_dict.get('error')
            if error_message:
                print(f"[hotels_finder] Error de SerpApi: {error_message}")
                return [{"error": f"Error de la API de hoteles: {error_message}"}]
            
            print(f"[hotels_finder] No se encontró la lista de hoteles ('properties' o 'hotels_results') en la respuesta. Respuesta: {json.dumps(results_dict, indent=2)[:500]}...")
            return [{"error": "No se encontró la lista de hoteles en la respuesta de la API. La estructura podría haber cambiado."}]

    except Exception as e:
        print(f"[hotels_finder ERROR] Excepción al buscar hoteles: {e}")
        import traceback
        traceback.print_exc()
        return [{"error": f"Excepción en la herramienta de búsqueda de hoteles: {str(e)}"}]