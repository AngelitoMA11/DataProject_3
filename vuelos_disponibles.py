import json
from datetime import datetime

with open("vuelos_resultado.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for tipo, vuelos in data.items():  # tipo: "ida" o "vuelta"
    ofertas = vuelos.get("flightOffers", [])
    if not ofertas:
        print(f"❌ No hay vuelos disponibles de {tipo}.\n")
        continue

    print(f"✈️ Vuelos de {tipo} encontrados: {len(ofertas)}\n")
    vuelos_mostrados = set()

    for i, oferta in enumerate(ofertas, 1):
        segmento = oferta["segments"][0]
        leg = segmento["legs"][0]
        carriers = leg.get("carriersData", [])
        aerolineas = [c["name"] for c in carriers if "name" in c]
        aerolinea_principal = aerolineas[0] if aerolineas else "Desconocida"

        salida = segmento["departureTime"]
        llegada = segmento["arrivalTime"]
        origen = segmento["departureAirport"]["name"]
        destino = segmento["arrivalAirport"]["name"]

        clave_unica = (salida, llegada, aerolinea_principal)
        if clave_unica in vuelos_mostrados:
            continue
        vuelos_mostrados.add(clave_unica)

        precio_info = oferta["priceBreakdown"]["total"]
        precio_total = precio_info["units"] + precio_info["nanos"] / 1e9

        print(f"🛫 Vuelo {i}")
        print(f"Aerolínea: {aerolinea_principal}")
        print(f"Origen: {origen} | Destino: {destino}")
        print(f"Salida: {datetime.fromisoformat(salida)}")
        print(f"Llegada: {datetime.fromisoformat(llegada)}")
        print(f"Precio total: {precio_total:.2f} {precio_info['currencyCode']}")
        print("-" * 40)
