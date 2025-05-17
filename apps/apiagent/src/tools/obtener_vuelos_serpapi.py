from datetime import timedelta
api_key_serpapi = "2a6f69c74ec76ec1770b95c43601c5380fd53be9172899af533393c02a7dd2f8"


def formato_duracion(minutos):
    try:
        return str(timedelta(minutes=minutos))
    except:
        return "N/A"



def obtener_vuelos_serpapi(origen, destino, fecha_ida, fecha_vuelta, api_key):
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "arrival_id": destino,
        "outbound_date": fecha_ida,
        "return_date": fecha_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": api_key
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        data = response.json()
        vuelos = data.get("best_flights", [])[:6]

        opciones = []
        for vuelo in vuelos:
            tramos = vuelo.get("flights", [])
            if not tramos:
                continue

            compañias = list({t.get("airline", "N/A") for t in tramos})
            salida = tramos[0].get("departure_airport", {}).get("time", "N/A")
            llegada = tramos[-1].get("arrival_airport", {}).get("time", "N/A")
            duracion_total = formato_duracion(sum(t.get("duration", 0) for t in tramos))
            escalas = len(tramos) - 1
            precio = vuelo.get("price", "N/A")
            link = vuelo.get("booking_link") or data.get("search_metadata", {}).get("google_flights_url", "https://www.google.com/travel/flights")

            opciones.append({
                "compañias": ", ".join(compañias),
                "salida": salida,
                "llegada": llegada,
                "duración": duracion_total,
                "escalas": escalas,
                "precio": precio,
                "link": link
            })
        return opciones
    except Exception as e:
        print("❌ Error:", e)
        return []

def mostrar_opciones_vuelos(vuelos):
    if not vuelos:
        print("🚫 No se encontraron vuelos.")
        return None

    for i, v in enumerate(vuelos):
        print(f"\n[{i+1}] ✈️ {v['compañias']}")
        print(f"   🕐 {v['salida']} → {v['llegada']} | ⏱️ {v['duración']} | Escalas: {v['escalas']}")
        print(f"   💶 Precio: {v['precio']} EUR")
        print(f"   🌐 Ver vuelo: {v['link']}")

    while True:
        try:
            eleccion = int(input(f"\n✋ Elige el número del vuelo (1-{len(vuelos)}): "))
            if 1 <= eleccion <= len(vuelos):
                return vuelos[eleccion - 1]
            else:
                print("❌ Número fuera de rango.")
        except ValueError:
            print("❌ Entrada inválida.")