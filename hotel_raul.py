import http.client
import urllib.parse
import json
import ssl

# Configuración
ciudad_destino = "London"
fecha_entrada = "2025-04-17"
fecha_salida = "2025-04-24"
adults = 1
rooms = 1
currency = "EUR"

# API RapidAPI
RAPIDAPI_KEY = "017cb5a280msh6eb35e40c0a8d85p1c66a5jsn09a0cfa0a3b0"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"
headers = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': RAPIDAPI_HOST
}

def hacer_peticion(endpoint, tipo=""):
    """Función genérica para hacer peticiones a la API"""
    print(f"🔍 Consultando {tipo}...")
    
    # Crear un contexto SSL que omita la verificación
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST, context=context)
    print(f"URL: {endpoint}")
    conn.request("GET", endpoint, headers=headers)
    response = conn.getresponse()
    
    if response.status != 200:
        print(f"❌ Error {response.status}: {response.reason}")
        return None
    
    print(f"✅ Respuesta OK para {tipo}")
    return json.loads(response.read().decode("utf-8"))

def buscar_destino_hotel(nombre_ciudad):
    """Busca el ID del destino"""
    endpoint = f"/api/v1/hotels/searchDestination?query={nombre_ciudad}"
    data = hacer_peticion(endpoint, "destino")
    
    if not data or "data" not in data:
        print("No se encontraron datos de destino")
        return None, None
    
    # Seleccionar el destino con más hoteles
    destino_seleccionado = max(data["data"], key=lambda x: x.get('hotels', 0))
    print("\n=== DESTINO SELECCIONADO ===")
    print(f"Nombre: {destino_seleccionado.get('name', 'N/A')}")
    print(f"ID: {destino_seleccionado.get('dest_id', 'N/A')}")
    
    return destino_seleccionado["dest_id"], "CITY"

def buscar_hoteles(dest_id, search_type):
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
    return hacer_peticion(endpoint, "hoteles")

def imprimir_hoteles(hoteles):
    """Imprime información detallada de los hoteles"""
    print("\n=== ESTRUCTURA COMPLETA DE DATOS ===")
    print(json.dumps(hoteles, indent=2))
    
    print("\n=== INFORMACIÓN DE HOTELES ===")
    
    # Verificar si hay datos de hoteles
    if not hoteles or 'data' not in hoteles:
        print("No se encontraron datos de hoteles")
        return
    
    # Obtener la lista de hoteles
    lista_hoteles = hoteles.get('data', {}).get('hotels', [])
    
    # Imprimir número de hoteles
    print(f"Número total de hoteles: {len(lista_hoteles)}")
    
    # Iterar y mostrar información de cada hotel
    for i, hotel in enumerate(lista_hoteles, 1):
        print(f"\nHotel {i}:")
        # Imprimir todas las claves del hotel para ver la estructura exacta
        for clave, valor in hotel.items():
            print(f"  {clave}: {valor}")

def guardar_json(datos, nombre_archivo):
    """Guarda datos en un archivo JSON"""
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"💾 Archivo '{nombre_archivo}' creado correctamente")

def main():
    # 1. Obtener ID del destino y tipo
    print("\n=== BUSCANDO DESTINO ===")
    dest_id, search_type = buscar_destino_hotel(ciudad_destino)
    
    if not dest_id or not search_type:
        print("❌ No se pudo obtener el ID o tipo de destino.")
        return
    
    print(f"✅ ID de destino para {ciudad_destino}: {dest_id}")
    print(f"✅ Tipo de búsqueda: {search_type}")
    
    # 2. Buscar hoteles
    print("\n=== BUSCANDO HOTELES ===")
    hoteles = buscar_hoteles(dest_id, search_type)
    
    if not hoteles:
        print("❌ No se pudieron encontrar hoteles.")
        return
    
    # 3. Imprimir información de hoteles
    imprimir_hoteles(hoteles)
    
    # 4. Guardar JSON
    guardar_json(hoteles, "hoteles_resultados.json")
    
    # 5. Verificar estado
    if "status" in hoteles and hoteles["status"] is False:
        print("❌ Error en la respuesta de la API de hoteles")
        if "message" in hoteles:
            print(f"Mensaje de error: {hoteles['message']}")
    else:
        print("✅ Búsqueda de hoteles completada")

if __name__ == "__main__":
    main()