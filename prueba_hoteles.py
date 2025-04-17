import http.client
import urllib.parse
import json
import time

# === CONFIGURACIÓN DEL USUARIO ===
ciudad = "Valencia"
fecha_checkin = "2025-04-17"
fecha_checkout = "2025-04-20"
adults = 2
currency = "EUR"

RAPIDAPI_KEY = "9630d11b3dmshc21bd0426b9a53cp153093jsn46cfb50160a1"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

headers = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': RAPIDAPI_HOST
}

# === 1. Obtener dest_id dinámicamente ===
def obtener_dest_id(ciudad):
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    query = urllib.parse.quote(ciudad)
    conn.request("GET", f"/api/v1/hotels/searchDestination?query={query}", headers=headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))
    for destino in data.get("data", []):
        if destino.get("dest_type") == "city" and destino.get("country") == "Spain":
            return destino.get("dest_id")
    return None

# === 2. Buscar hoteles y extraer hotel_id ===
def buscar_hoteles(dest_id):
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    params = {
        "dest_id": dest_id,
        "dest_type": "city",
        "checkin_date": fecha_checkin,
        "checkout_date": fecha_checkout,
        "adults_number": str(adults),
        "order_by": "popularity",
        "locale": "en-gb",
        "units": "metric",
        "filter_by_currency": currency,
        "page_number": "0"
    }
    query = urllib.parse.urlencode(params)
    conn.request("GET", f"/api/v1/hotels/searchHotels?{query}", headers=headers)
    res = conn.getresponse()
    return json.loads(res.read().decode("utf-8"))

# === 3. Consultar disponibilidad por hotel_id ===
def consultar_disponibilidad(hotel_id):
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    params = {
        "hotel_id": hotel_id,
        "min_date": fecha_checkin,
        "max_date": fecha_checkout,
        "currency_code": currency
    }
    query = urllib.parse.urlencode(params)
    conn.request("GET", f"/api/v1/hotels/getAvailability?{query}", headers=headers)
    res = conn.getresponse()
    return json.loads(res.read().decode("utf-8"))

# === EJECUCIÓN COMPLETA ===
dest_id = obtener_dest_id(ciudad)
if not dest_id:
    print(f"❌ No se encontró ningún 'dest_id' para la ciudad '{ciudad}'")
    exit()

print(f"📍 Ciudad '{ciudad}' → dest_id = {dest_id}")
hoteles = buscar_hoteles(dest_id)
hotel_ids = [h.get("hotel_id") for h in hoteles.get("data", []) if h.get("hotel_id")]

print(f"🏨 Se encontraron {len(hotel_ids)} hoteles. Consultando disponibilidad...")

resultados = {}
for i, hotel_id in enumerate(hotel_ids, 1):
    print(f"🔎 ({i}/{len(hotel_ids)}) Hotel ID: {hotel_id}")
    disponibilidad = consultar_disponibilidad(hotel_id)
    resultados[hotel_id] = disponibilidad
    time.sleep(1)  # evitar bloqueo por rate limit

# === Guardar en JSON
with open("disponibilidad_hoteles.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)

print("✅ Archivo 'disponibilidad_hoteles.json' creado correctamente.")
