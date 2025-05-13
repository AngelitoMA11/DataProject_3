import json
import os
import httpx
import urllib.parse
import pandas as pd
from google.cloud import bigquery
import functions_framework

# Configuración
PROJECT_ID = os.getenv("PROJECT_ID", "dataproject3-458310")
DATASET = os.getenv("DATASET", "app_viajes")
TABLE = os.getenv("TABLE", "coches")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "9630d11b3dmshc21bd0426b9a53cp153093jsn46cfb50160a1")
CAR_HOST = "booking-com18.p.rapidapi.com"
CAR_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": CAR_HOST
}
DEFAULT_RATE = float(os.getenv("USD_TO_EUR_RATE", "0.9"))

async def obtener_pickup_ids(ciudad: str) -> list:
    """
    Busca todos los IDs de tipo 'airport' para la ciudad indicada.
    Retorna una lista de IDs o lanza ValueError si no encuentra ninguno.
    """
    async with httpx.AsyncClient() as client:
        query = urllib.parse.quote(ciudad)
        url = f"https://{CAR_HOST}/car/auto-complete?query={query}"
        resp = await client.get(url, headers=CAR_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        airport_ids = [item.get("id") for item in data if item.get("type", "").lower() == "airport"]
        if not airport_ids:
            raise ValueError(f"No se encontraron aeropuertos para {ciudad}")
        return airport_ids

def procesar_alquileres(data, ciudad, rate=DEFAULT_RATE):
    registros = []
    # Extraer lista de resultados
    resultados = data.get('data', {}).get('search_results', [])
    
    for res in resultados:
        proveedor = res.get('content', {}).get('supplier', {}).get('name', '')
        modelo = res.get('vehicle_info', {}).get('v_name', '')

        # Categoría y asientos
        label = res.get('vehicle_info', {}).get('label', '')
        categoria = label.split(' with')[0] if label else None
        asientos = res.get('vehicle_info', {}).get('seats')

        # Transmisión
        transmision = None
        for spec in res.get('content', {}).get('vehicleSpecs', []):
            if spec.get('icon', '').startswith("TRANSMISSION_"):
                transmision = spec.get('text')
                break

        # Precio USD → EUR
        pr = res.get('pricing_info', {}) or {}
        raw = pr.get('drive_away_price') if pr.get('drive_away_price') is not None else pr.get('price')
        try:
            usd = float(raw or 0)
        except (ValueError, TypeError):
            usd = 0.0
        precio = round(usd * rate, 2)

        registros.append({
            'Ciudad': ciudad,
            'Compañía': proveedor,
            'Vehículo': modelo,
            'Categoría': categoria,
            'Asientos': asientos,
            'Transmisión': transmision,
            'Precio': precio
        })

    return registros

def preparar_dataframe(registros):
    df = pd.DataFrame(registros)
    
    if df.empty:
        return df
        
    # Asegurar tipos sencillos
    df['Asientos'] = df['Asientos'].fillna(0).astype(int)
    df['Precio'] = df['Precio'].fillna(0.0)
    for col in ['Ciudad','Compañía','Vehículo','Categoría','Transmisión']:
        df[col] = df[col].fillna('').astype(str)
    return df

def insertar_bigquery(df):
    if df.empty:
        return
        
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    job = client.load_table_from_dataframe(df, table_id)
    job.result()  # Esperar a completar

@functions_framework.http
async def buscar_coches(request):
    """
    Cloud Function que busca alquileres de coches, procesa datos y guarda en BigQuery
    """
    # Extraer body del request
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return {"error": "No se proporcionó un cuerpo JSON válido"}
    except Exception as e:
        return {"error": f"Error al procesar la solicitud: {str(e)}"}
    
    try:
        # Verificar datos necesarios
        if not all(key in request_json for key in ["ciudad_destino_aeropuerto", "fecha_salida", "fecha_vuelta"]):
            return {"error": "Faltan datos obligatorios para la búsqueda de coches"}
        
        ciudad = request_json["ciudad_destino_aeropuerto"]
        
        # Buscar IDs de puntos de recogida
        pickup_ids = await obtener_pickup_ids(ciudad)
        
        # Preparar fechas
        pick_up_date = "-".join(reversed(request_json["fecha_salida"].split("-")))
        drop_off_date = "-".join(reversed(request_json["fecha_vuelta"].split("-")))
        pick_up_time = "10:00"
        drop_off_time = "10:00"
        
        todos_registros = []
        resultados_por_aeropuerto = []
        
        # Para cada aeropuerto, realizar búsqueda
        for pid in pickup_ids:
            params_car = {
                "pickUpId": pid,
                "pickUpDate": pick_up_date,
                "pickUpTime": pick_up_time,
                "dropOffDate": drop_off_date,
                "dropOffTime": drop_off_time
            }
            
            url_car = f"https://{CAR_HOST}/car/search"
            async with httpx.AsyncClient() as client:
                resp_car = await client.get(url_car, headers=CAR_HEADERS, params=params_car, timeout=20)
                resp_car.raise_for_status()
                data_coches = resp_car.json()
            
            # Procesar los resultados
            registros = procesar_alquileres(data_coches, ciudad)
            todos_registros.extend(registros)
            
            # Guardar para la respuesta
            resultados_por_aeropuerto.append({
                "pickUpId": pid,
                "resultados": data_coches
            })
        
        # Preparar DataFrame y guardar en BigQuery
        df = preparar_dataframe(todos_registros)
        insertar_bigquery(df)
        
        # Devolver resultados para la respuesta
        return {
            "ciudad_destino_aeropuerto": ciudad,
            "fuente": "booking",
            "resultados_por_aeropuerto": resultados_por_aeropuerto,
            "procesados": len(todos_registros)
        }
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"error": str(e)}