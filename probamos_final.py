import json
import pandas as pd
from google.cloud import bigquery

# Configuración
INPUT_JSON = "respuesta_vuelos.json"
PROJECT_ID = "dataproject3-458310"
DATASET = "app_viajes"
TABLE = "vuelos"

def procesar_vuelos(ofertas):
    registros = []
    for offer in ofertas:
        segments = offer.get("segments", [])
        if not segments:
            continue

        first_leg = segments[0]["legs"][0] if segments[0].get("legs") else {}
        last_leg = segments[-1]["legs"][-1] if segments[-1].get("legs") else {}

        ciudad_salida = first_leg.get("departureAirport", {}).get("cityName")
        ciudad_llegada = last_leg.get("arrivalAirport", {}).get("cityName")

        salida_dt = first_leg.get("departureTime", "")
        llegada_dt = last_leg.get("arrivalTime", "")
        dia_salida, hora_salida = salida_dt.split("T") if "T" in salida_dt else ("", "")
        dia_llegada, hora_llegada = llegada_dt.split("T") if "T" in llegada_dt else ("", "")

        duracion_segundos = sum(seg.get("totalTime", 0) for seg in segments)
        horas = duracion_segundos // 3600
        minutos = (duracion_segundos % 3600) // 60
        duracion_legible = f"{int(horas)}h {int(minutos)}m"

        escalas = sum(len(seg.get("legs", [])) - 1 for seg in segments)

        ciudades_escala = []
        for seg in segments:
            legs = seg.get("legs", [])
            for i in range(len(legs) - 1):
                city = legs[i].get("arrivalAirport", {}).get("cityName")
                if city:
                    ciudades_escala.append(city)

        try:
            aerolinea = segments[0]["legs"][0]["carriersData"][0]["name"]
        except (IndexError, KeyError, TypeError):
            aerolinea = ""

        precio_total = offer.get("priceBreakdown", {}).get("total", {})
        precio_eur = precio_total.get("units", 0) + precio_total.get("nanos", 0) / 1e9

        registros.append({
            "fuente": "booking",
            "ciudad_salida": ciudad_salida,
            "ciudad_llegada": ciudad_llegada,
            "dia_salida": dia_salida,
            "hora_salida": hora_salida,
            "dia_llegada": dia_llegada,
            "hora_llegada": hora_llegada,
            "aerolinea": aerolinea,
            "precio_eur": round(precio_eur, 2),
            "tipo_trayecto": offer.get("tripType"),
            "duracion": duracion_legible,
            "numero_escalas": escalas,
            "ciudades_escala": ciudades_escala
        })

    return registros

def preparar_dataframe(vuelos):
    df = pd.DataFrame(vuelos)

    # Conversión de fechas
    df["dia_salida"] = pd.to_datetime(df["dia_salida"], errors="coerce").dt.date
    df["dia_llegada"] = pd.to_datetime(df["dia_llegada"], errors="coerce").dt.date

    # Conversión segura a string y manejo de valores nulos
    df["hora_salida"] = df["hora_salida"].fillna("").astype(str).apply(
        lambda x: x if ":" in x else ""  # Ensure valid time format
    )
    df["hora_llegada"] = df["hora_llegada"].fillna("").astype(str).apply(
        lambda x: x if ":" in x else ""  # Ensure valid time format
    )
    df["ciudad_salida"] = df["ciudad_salida"].fillna("").astype(str)
    df["ciudad_llegada"] = df["ciudad_llegada"].fillna("").astype(str)
    df["aerolinea"] = df["aerolinea"].fillna("").astype(str)
    df["tipo_trayecto"] = df["tipo_trayecto"].fillna("").astype(str)
    df["duracion"] = df["duracion"].fillna("").astype(str)
    df["ciudades_escala"] = df["ciudades_escala"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else str(x)
    ).fillna("")

    return df

def insertar_en_bigquery(df):
    client = bigquery.Client(project=PROJECT_ID)
    tabla_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    job = client.load_table_from_dataframe(df, tabla_id)
    job.result()

    print(f"{len(df)} filas insertadas en BigQuery")

def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    ida = data.get("ida", {}).get("flightOffers", [])
    vuelta = data.get("vuelta", {}).get("flightOffers", [])

    vuelos = procesar_vuelos(ida) + procesar_vuelos(vuelta)
    df = preparar_dataframe(vuelos)
    insertar_en_bigquery(df)

if __name__ == "__main__":
    main()
