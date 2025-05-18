from typing import Optional, Dict, Any
from langchain_core.tools import tool
from datetime import date, timedelta
import requests
import os
from src.utils.logger_config import setup_logger

logger = setup_logger('tools.buscar_vuelos')

@tool
def buscar_vuelos(
    ciudad_origen: str,
    ciudad_destino: str,
    fecha_salida: str,
    fecha_vuelta: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "ECONOMY",
    tipo_de_viaje: str = "Ida y Vuelta"
) -> Dict[str, Any]:
    """
    Busca vuelos disponibles según los criterios especificados.
    
    Args:
        ciudad_origen: Código IATA de la ciudad de origen (ej: "MAD")
        ciudad_destino: Código IATA de la ciudad de destino (ej: "BCN")
        fecha_salida: Fecha de salida en formato YYYY-MM-DD
        fecha_vuelta: Fecha de vuelta en formato YYYY-MM-DD (opcional para viajes de ida y vuelta)
        adults: Número de adultos (1-9)
        cabin_class: Clase de cabina ("ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST")
        tipo_de_viaje: Tipo de viaje ("Ida y Vuelta" o "Solo Ida")
    
    Returns:
        Dict con los resultados de la búsqueda de vuelos
    """
    try:
        # Validar y transformar el tipo de viaje
        tipo_de_viaje_num = 1 if tipo_de_viaje == "Ida y Vuelta" else 2
        
        # Validar fechas
        if tipo_de_viaje_num == 1 and not fecha_vuelta:
            fecha_vuelta = (date.fromisoformat(fecha_salida) + timedelta(days=7)).isoformat()
        
        # Preparar el payload
        payload = {
            "ciudad_origen": ciudad_origen.upper(),
            "ciudad_destino": ciudad_destino.upper(),
            "fecha_salida": fecha_salida,
            "fecha_vuelta": fecha_vuelta,
            "adults": min(max(1, adults), 9),  # Asegurar que esté entre 1 y 9
            "cabin_class": cabin_class.upper(),
            "tipo_de_viaje": tipo_de_viaje_num
        }
        
        # Obtener la URL base del entorno
        base_url = os.environ.get("DATA_API_URL")
        if not base_url:
            logger.warning("DATA_API_URL no está configurada en el entorno")
            return {
                "error": "Configuración incompleta",
                "message": "La URL de la API no está configurada"
            }
        
        # Realizar la petición
        url_api = f"{base_url}/vuelos"
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(
            url=url_api,
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error en la búsqueda de vuelos: {response.status_code}")
            return {
                "error": f"Error en la búsqueda: {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        logger.error(f"Error al buscar vuelos: {str(e)}")
        return {
            "error": "Error interno",
            "message": str(e)
        }
