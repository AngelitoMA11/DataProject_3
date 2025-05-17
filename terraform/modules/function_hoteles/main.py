import json, os, httpx
from serpapi import GoogleSearch
from google.cloud import bigquery
import functions_framework
import logging

# Configuración básica
PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET = os.environ.get("DATASET")
TABLE = os.environ.get("TABLE")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
BOOKING_HOST = "booking-com18.p.rapidapi.com"
BOOKING_HEADERS = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": BOOKING_HOST}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Función auxiliar
def extract_value(value, default=None, tipo="str"):
    if value is None: return default
    try: return float(value) if tipo == "float" else int(value) if tipo == "int" else str(value)
    except: return default

# Booking API
def obtener_ufi_destino(ciudad):
    try:
        with httpx.AsyncClient() as client:
            resp = client.get(f"https://{BOOKING_HOST}/stays/auto-complete",
                                  headers=BOOKING_HEADERS, params={"query": ciudad}, timeout=15)
            if resp.status_code != 200: return None, None, None
            data = resp.json()
            if data and isinstance(data, list):
                first_result = data[0]
                return first_result.get("ufi"), first_result.get("latitude"), first_result.get("longitude")
            return None, None, None
    except Exception as e:
        logging.error(f"Error en obtener_ufi_destino: {str(e)}")
        return None, None, None

def buscar_en_booking(payload):
    try:
        ufi, latitude, longitude = obtener_ufi_destino(payload["ciudad"])
        if not ufi or latitude is None or longitude is None:
            return {"error": "No se encontró destino o coordenadas"}

        params = {
            "ufi": ufi,
            "checkinDate": payload["fecha_entrada"],
            "checkoutDate": payload["fecha_vuelta"],
            "adults": str(payload.get("adults", 2)),
            "rooms": str(payload.get("rooms", 1)),
            "latitude": str(latitude),
            "longitude": str(longitude),
            "currency": "EUR"
        }
        with httpx.AsyncClient() as client:
            resp = client.get(f"https://{BOOKING_HOST}/stays/search",
                                   headers=BOOKING_HEADERS, params=params, timeout=30)
            if resp.status_code != 200:
                return {"error": f"Error: {resp.status_code} - {resp.text}"}
            return resp.json()
    except Exception as e:
        return {"error": str(e)}

def limpiar_booking(data):
    hoteles = []
    try:
        if "error" in data: return []
        
        hoteles_raw = data.get('0', [])
        if not isinstance(hoteles_raw, list):
            hoteles_raw = data.get('data', [])
            if not isinstance(hoteles_raw, list): return []

        for hotel_item in hoteles_raw:
            try:
                nombre = extract_value(hotel_item.get('name'))
                direccion = extract_value(hotel_item.get('address'))
                ciudad = extract_value(hotel_item.get('wishlistName'))

                precio = 0
                moneda = 'USD'
                if 'priceBreakdown' in hotel_item and isinstance(hotel_item['priceBreakdown'], dict):
                    gross_price_info = hotel_item['priceBreakdown'].get('grossPrice', {})
                    precio = round(extract_value(gross_price_info.get('value', 0), 0, "float"), 2)
                    moneda = gross_price_info.get('currency', 'USD')
                elif 'value' in hotel_item:
                    precio = round(extract_value(hotel_item['value'], 0, "float"), 2)
                    moneda = extract_value(hotel_item.get('currency', 'USD'))

                fotos = []
                if 'photoUrls' in hotel_item and isinstance(hotel_item['photoUrls'], list):
                    fotos = hotel_item['photoUrls'][:3]
                elif 'photos' in hotel_item and isinstance(hotel_item['photos'], list):
                    for photo_entry in hotel_item['photos']:
                        if isinstance(photo_entry, str) and photo_entry.startswith("http"):
                            fotos.append(photo_entry)
                        elif isinstance(photo_entry, dict) and photo_entry.get('url'):
                            fotos.append(photo_entry['url'])
                    fotos = fotos[:3]

                servicios = []
                if 'facilities' in hotel_item and isinstance(hotel_item['facilities'], list):
                    servicios = [f.get('name') for f in hotel_item['facilities'] if f and 'name' in f][:5]
                elif 'amenities' in hotel_item and isinstance(hotel_item['amenities'], list):
                    servicios = [a.get('name') for a in hotel_item['amenities'] if a and 'name' in a][:5]

                if nombre or precio > 0:
                    hoteles.append({
                        "Nombre": nombre,
                        "Direccion": direccion,
                        "Ciudad": ciudad,
                        "Puntuacion": extract_value(hotel_item.get('reviewScore'), 0, "float"),
                        "NumResenas": extract_value(hotel_item.get('reviewCount'), 0, "int"),
                        "PrecioNoche": precio,
                        "Moneda": moneda,
                        "FechaEntrada": extract_value(hotel_item.get('checkinDate')),
                        "FechaSalida": extract_value(hotel_item.get('checkoutDate')),
                        "Categoria": extract_value(hotel_item.get('propertyClass'), 0, "int"),
                        "Fotos": fotos,
                        "Servicios": servicios,
                        "EnlaceHotel": extract_value(hotel_item.get('url')),
                        "Fuente": "Booking"
                    })
            except: continue
    except Exception as e:
        logging.error(f"Error en limpiar_booking: {str(e)}")
    return hoteles

# SerpAPI
def buscar_en_serpapi(payload):
    try:
        params = {
            "api_key": SERPAPI_KEY, "engine": "Google Hotels",
            "q": f"{payload['ciudad']} Hotel",
            "check_in_date": payload["fecha_entrada"], "check_out_date": payload["fecha_vuelta"],
            "currency": "EUR", "hl": "es", "gl": "es", "adults": str(payload.get("adults", 1))
        }
        if "max_price" in payload: params["max_price"] = str(payload["max_price"])
        if "valoracion" in payload and payload["valoracion"] is not None:
            params["min_rating"] = str(payload["valoracion"])

        search = GoogleSearch(params)
        return search.get_dict()
    except Exception as e:
        return {"error": str(e)}

def limpiar_serpapi(data, payload):
    hoteles = []
    try:
        if "error" in data: return []
        if "properties" not in data: return []
        
        for hotel in data["properties"]:
            try:
                precio = 0
                if "price" in hotel:
                    precio_str = str(hotel["price"]).replace("€", "").replace(".", "").replace(",", ".").strip()
                    try:
                        precio = float(precio_str)
                    except:
                        import re
                        digitos = re.findall(r'\d+', precio_str)
                        if digitos: precio = float("".join(digitos))

                nombre = extract_value(hotel.get("title")) or extract_value(hotel.get("name"))
                if nombre:
                    hoteles.append({
                        "Nombre": nombre,
                        "Direccion": extract_value(hotel.get("address")),
                        "Ciudad": extract_value(payload["ciudad"]),
                        "Puntuacion": extract_value(hotel.get("rating"), 0, "float"),
                        "NumResenas": extract_value(hotel.get("reviews"), 0, "int"),
                        "PrecioNoche": precio,
                        "Moneda": "EUR",
                        "FechaEntrada": payload["fecha_entrada"],
                        "FechaSalida": payload["fecha_vuelta"],
                        "Categoria": extract_value(hotel.get("stars"), 0, "int"),
                        "Fotos": [hotel.get("thumbnail")] if hotel.get("thumbnail") else [],
                        "Servicios": hotel.get("amenities", [])[:5] if "amenities" in hotel else [],
                        "EnlaceHotel": hotel.get("link", ""),
                        "Fuente": "SerpAPI"
                    })
            except: continue
    except Exception as e:
        logging.error(f"Error en limpiar_serpapi: {str(e)}")
    return hoteles

# BigQuery
def insertar_en_bigquery(hoteles):
    if not hoteles: return False
    try:
        if os.environ.get("ENTORNO") == "local":
            logging.info(f"[SIMULACIÓN] Se insertarían {len(hoteles)} hoteles en BigQuery")
            return True
        client = bigquery.Client(project=PROJECT_ID)
        tabla_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"
        errors = client.insert_rows_json(tabla_id, hoteles)
        if errors:
            logging.error(f"BigQuery insert errors: {errors}")
            return False
        return True
    except Exception as e:
        logging.error(f"Error inserting into BigQuery: {str(e)}")
        return False

# Punto de entrada
@functions_framework.http
def buscar_hoteles(request):
    try:
        testing = os.environ.get("ENTORNO") == "local"
        if testing:
            request_json = {
                "ciudad": "New York",
                "fecha_entrada": "2025-06-15",
                "fecha_vuelta": "2025-06-20",
                "adults": 2,
                "rooms": 1,
                "valoracion": 4
            }
        else:
            request_json = request.get_json(silent=True)

        if not request_json or not all(k in request_json for k in ["ciudad", "fecha_entrada", "fecha_vuelta"]):
            return {"error": "Datos incorrectos o incompletos."}, 400

        request_json["adults"] = request_json.get("adults", 2)
        request_json["rooms"] = request_json.get("rooms", 1)
        request_json["valoracion"] = request_json.get("valoracion", None)

        # Búsqueda en ambas APIs
        resultado_booking = buscar_en_booking(request_json)
        hoteles_booking = limpiar_booking(resultado_booking)
        
        resultado_serpapi = buscar_en_serpapi(request_json)
        hoteles_serpapi = limpiar_serpapi(resultado_serpapi, request_json)
        
        hoteles_combinados = hoteles_booking + hoteles_serpapi

        # Filtro por valoración
        if request_json["valoracion"] is not None:
            try:
                min_rating = float(request_json["valoracion"])
                hoteles_combinados = [h for h in hoteles_combinados if h.get("Puntuacion", 0) >= min_rating]
            except: pass

        # Guardar en BigQuery
        if hoteles_combinados:
            insertar_en_bigquery(hoteles_combinados)

        return {
            "success": True,
            "hoteles_encontrados": len(hoteles_combinados),
            "booking_hoteles": len(hoteles_booking),
            "serpapi_hoteles": len(hoteles_serpapi),
            "hoteles": hoteles_combinados
        }, 200

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return {"error": str(e), "success": False}, 500

