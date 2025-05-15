import os
import json
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from serpapi import GoogleSearch

app = FastAPI()

class HotelsRequest(BaseModel):
    q: str
    check_in_date: str
    check_out_date: str
    sort_by: str = "3"
    adults: int = 1
    children: int = 0
    rooms: int = 1
    hotel_class: str | None = None

@app.post("/search-hotels")
async def search_hotels(request: HotelsRequest) -> Dict[str, Any]:
    """
    Cloud function endpoint to search for hotels using SerpApi.
    """
    try:
        api_params = {
            'api_key': os.environ.get('SERPAPI_API_KEY'),
            'engine': 'google_hotels',
            'hl': 'en',
            'gl': 'us',
            'q': request.q,
            'check_in_date': request.check_in_date,
            'check_out_date': request.check_out_date,
            'currency': 'USD',
            'adults': request.adults,
            'num_rooms': request.rooms,
            'sort_by': request.sort_by,
        }

        if request.children > 0:
            print(f"Warning: Children parameter ({request.children}) might need specific format for SerpApi Google Hotels.")

        if request.hotel_class:
            api_params['hotel_class'] = request.hotel_class

        search = GoogleSearch(api_params)
        results_dict = search.get_dict()

        processed_hotels = []
        hotels_list = results_dict.get('properties')
        if not hotels_list and results_dict.get('hotels_results'):
            hotels_list = results_dict.get('hotels_results')
        
        if hotels_list and isinstance(hotels_list, list):
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
                return {
                    "status": "success",
                    "data": processed_hotels
                }
            else:
                raise HTTPException(status_code=404, detail="No se encontraron hoteles procesables en la respuesta de la API.")

        error_message = results_dict.get('error')
        if error_message:
            raise HTTPException(status_code=400, detail=f"Error de la API de hoteles: {error_message}")
        
        raise HTTPException(status_code=404, detail="No se encontró la lista de hoteles en la respuesta de la API.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 