import requests
from langchain_core.tools import tool
from config import DATA_API_URL


@tool
def search_flights(
    ciudad_origen: str,
    ciudad_destino: str,
    fecha_salida: str,
    fecha_vuelta: str,
    stops: int = 0,
    adults: int = 1,
    children: int = 0,
    cabin_class: str = "ECONOMY",
    currency: str = "EUR",
) -> list[dict]:
    """
    Busca vuelos según origen, destino y rango de fechas ISO-8601.
    Devuelve una lista de dicts con precio total, aerolínea, horario
    y URL de reserva.
    """
    url = f"{DATA_API_URL}/vuelos"
    params = {
        "ciudad_origen": ciudad_origen,
        "ciudad_destino": ciudad_destino,
        "fecha_salida": fecha_salida,
        "fecha_vuelta": fecha_vuelta,
        "stops": stops,
        "adults": adults,
        "children": children,
        "cabin_class": cabin_class,
        "currency": currency,
    }
    print(url, params)

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()
