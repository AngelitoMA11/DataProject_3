from datetime import datetime

def preparar_json_para_buscador_vuelos(contexto_user):
    fecha_inicio = contexto_user.get("fechas", {}).get("inicio")
    fecha_fin = contexto_user.get("fechas", {}).get("fin")

    # Asegurar formato correcto: YYYY-MM-DD
    def normalizar(fecha_str):
        try:
            return datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except:
            return fecha_str  # ya está bien

    return {
        "departure_id": contexto_user.get("iata_origen"),
        "arrival_id": contexto_user.get("destino_elegido", {}).get("iata"),
        "outbound_date": normalizar(fecha_inicio),
        "return_date": normalizar(fecha_fin),
        "currency": "EUR",
        "hl": "es",
        "engine": "google_flights",
        "api_key": api_key_serpapi
    }
