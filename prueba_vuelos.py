import http.client
import urllib.parse
import json

# === CONFIGURACIÓN DEL USUARIO ===
ciudad_origen = "Alicante"
ciudad_destino = "London"
fecha_salida = "2025-04-17"
fecha_vuelta = None  # Ejemplo: "2025-04-24"

stops = "none"  # Opciones: "none", "0", "1", "2"
adults = 1
children = "1"  # Ejemplo: "3,7" o "0" si no hay niños
cabin_class = "ECONOMY"  # ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
currency = "EUR"

RAPIDAPI_KEY = ""
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

headers = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': RAPIDAPI_HOST
}

def obtener_id_ciudad(nombre_ciudad):
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    query = urllib.parse.quote(nombre_ciudad)
    conn.request("GET", f"/api/v1/flights/searchDestination?query={query}", headers=headers)
    data = json.loads(conn.getresponse().read().decode("utf-8"))
    
    for destino in data.get("data", []):
        if "AIRPORT" in destino["type"]:
            return destino["id"]
    return None

# Obtener los IDs de origen y destino
from_id = obtener_id_ciudad(ciudad_origen)
to_id = obtener_id_ciudad(ciudad_destino)

# Construir endpoint para buscar vuelos
conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
params = {
    "fromId": from_id,
    "toId": to_id,
    "departDate": fecha_salida,
    "stops": stops,
    "pageNo": "1",
    "adults": str(adults),
    "children": children,
    "cabinClass": cabin_class,
    "currency_code": currency
}
if fecha_vuelta:
    params["returnDate"] = fecha_vuelta

query_string = urllib.parse.urlencode(params)
endpoint = f"/api/v1/flights/searchFlights?{query_string}"

# Realizar la petición y guardar la respuesta
conn.request("GET", endpoint, headers=headers)
resultados = json.loads(conn.getresponse().read().decode("utf-8"))

with open("vuelos_resultado.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)

print("✅ Archivo 'vuelos_resultado.json' creado correctamente.")
