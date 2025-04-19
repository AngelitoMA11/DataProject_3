import http.client
import urllib.parse
import json
import ssl
import traceback

# Configuración de la API
RAPIDAPI_KEY = "017cb5a280msh6eb35e40c0a8d85p1c66a5jsn09a0cfa0a3b0"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

def hacer_peticion(endpoint, headers, tipo=""):
    """Función genérica para hacer peticiones a la API"""
    print(f"🔍 Consultando {tipo}...")
    print(f"Host: {RAPIDAPI_HOST}")
    print(f"Headers: {headers}")
    
    # Crear un contexto SSL que omita la verificación
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST, context=context)
    print(f"URL completa: {RAPIDAPI_HOST}{endpoint}")
    conn.request("GET", endpoint, headers=headers)
    response = conn.getresponse()
    
    print(f"Código de respuesta: {response.status}")
    
    if response.status != 200:
        print(f"❌ Error {response.status}: {response.reason}")
        # Intentar leer el cuerpo del error para más información
        error_body = response.read().decode("utf-8")
        print(f"Cuerpo del error: {error_body}")
        return None
    
    print(f"✅ Respuesta OK para {tipo}")
    data = json.loads(response.read().decode("utf-8"))
    # Imprimir una versión reducida para debug
    if data:
        if "data" in data:
            print(f"Datos recibidos con estructura correcta")
        else:
            print(f"Estructura de datos inesperada: {list(data.keys())}")
    return data

def buscar_destino_hotel(nombre_ciudad, headers):
    """Busca el ID del destino"""
    endpoint = f"/api/v1/hotels/searchDestination?query={urllib.parse.quote(nombre_ciudad)}"
    data = hacer_peticion(endpoint, headers, "destino")
    
    if not data or "data" not in data:
        return None, None
    
    # Seleccionar el destino con más hoteles que NO sea un aeropuerto
    destinos_con_hoteles = [
        destino for destino in data["data"] 
        if destino.get('hotels', 0) > 0 and destino.get('type') != 'ai'
    ]
    
    if destinos_con_hoteles:
        # Ordenar por número de hoteles y tomar el primero
        destino_seleccionado = max(destinos_con_hoteles, key=lambda x: x.get('hotels', 0))
        print(f"\n=== DESTINO SELECCIONADO ===")
        print(f"Nombre: {destino_seleccionado.get('name', 'N/A')}")
        print(f"ID: {destino_seleccionado['dest_id']}")
        print(f"Hoteles: {destino_seleccionado.get('hotels', 0)}")
        
        return destino_seleccionado["dest_id"], "CITY"
    
    return None, None

def buscar_hoteles(dest_id, search_type, fecha_entrada, fecha_salida, adults, rooms, headers, currency="EUR"):
    """Busca hoteles en el destino"""
    params = {
        "dest_id": dest_id,
        "search_type": search_type,
        "arrival_date": fecha_entrada,
        "departure_date": fecha_salida,
        "adults": str(adults),
        "room_qty": str(rooms),
        "page_number": "1",
        "currency_code": currency,
        "units": "metric",
        "temperature_unit": "c",
        "languagecode": "en-us"
    }
    query = urllib.parse.urlencode(params)
    endpoint = f"/api/v1/hotels/searchHotels?{query}"
    
    # Obtener respuesta original
    hoteles = hacer_peticion(endpoint, headers, "hoteles")
    
    # Imprimir información detallada de los hoteles
    if hoteles and 'data' in hoteles:
        lista_hoteles = hoteles.get('data', {}).get('hotels', [])
        print(f"\n=== INFORMACIÓN DE HOTELES ===")
        print(f"Número de hoteles encontrados: {len(lista_hoteles)}")
        
        # Si no hay hoteles, añadir un mensaje informativo
        if not lista_hoteles:
            hoteles["info_message"] = f"No se encontraron hoteles para {dest_id} en las fechas seleccionadas."
            print(f"⚠️ {hoteles['info_message']}")
        else:
            # Imprimir detalles de cada hotel
            for i, hotel in enumerate(lista_hoteles, 1):
                print(f"\nHotel {i}:")
                hotel_info = hotel.get('property', {})
                print(f"  Nombre: {hotel_info.get('name', 'N/A')}")
                precio = hotel_info.get('priceBreakdown', {}).get('grossPrice', {})
                print(f"  Precio: {precio.get('value', 'N/A')} {precio.get('currency', '')}")
                print(f"  Puntuación: {hotel_info.get('reviewScore', 'N/A')}")
    
    return hoteles

def guardar_json(datos, nombre_archivo):
    """Guarda datos en un archivo JSON"""
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"💾 Archivo '{nombre_archivo}' creado correctamente")

def main(origen, ciudad, entrada, salida, num_adultos=1, num_habitaciones=1, currency="EUR"):
    """Función principal que acepta parámetros de búsqueda incluyendo origen para futura integración con vuelos"""
    # Guardamos el origen aunque no lo usemos todavía (para futura integración con vuelos)
    print(f"\n=== PARÁMETROS DE BÚSQUEDA ===")
    print(f"Origen: {origen}")
    print(f"Destino: {ciudad}")
    print(f"Fecha ida: {entrada}")
    print(f"Fecha vuelta: {salida}")
    print(f"Adultos: {num_adultos}")
    print(f"Habitaciones: {num_habitaciones}")
    
    # Configurar headers
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': RAPIDAPI_HOST
    }
    
    try:
        # 1. Obtener ID del destino y tipo
        print("\n=== BUSCANDO DESTINO ===")
        dest_id, search_type = buscar_destino_hotel(ciudad, headers)
        
        if not dest_id or not search_type:
            print("❌ No se pudo obtener el ID o tipo de destino.")
            return {"error": "No se pudo encontrar el destino especificado"}
        
        print(f"✅ ID de destino para {ciudad}: {dest_id}")
        print(f"✅ Tipo de búsqueda: {search_type}")
        
        # 2. Buscar hoteles
        print("\n=== BUSCANDO HOTELES ===")
        hoteles = buscar_hoteles(dest_id, search_type, entrada, salida, num_adultos, num_habitaciones, headers, currency)
        
        if not hoteles:
            print("❌ No se pudieron encontrar hoteles.")
            return {"error": "No se pudieron encontrar hoteles con los criterios especificados"}
        
        # 3. Verificar estado
        if "status" in hoteles and hoteles["status"] is False:
            print("❌ Error en la respuesta de la API de hoteles")
            error_msg = hoteles.get('message', 'Error desconocido en la API')
            print(f"Mensaje de error: {error_msg}")
            return {"error": error_msg}
        else:
            print("✅ Búsqueda de hoteles completada")
            return hoteles
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        traceback.print_exc()
        return {"error": f"Error inesperado: {str(e)}"}

if __name__ == "__main__":
    # Modo de prueba con valores predeterminados
    resultado = main("Madrid", "London", "2025-04-17", "2025-04-24")
    if resultado:
        guardar_json(resultado, "hoteles_resultados.json")