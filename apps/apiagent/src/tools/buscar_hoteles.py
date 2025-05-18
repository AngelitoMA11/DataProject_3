from typing import Optional, Dict, Any
from langchain_core.tools import tool
from datetime import date, timedelta
import requests
import os
from src.utils.logger_config import setup_logger

logger = setup_logger('tools.buscar_hoteles')

@tool
def buscar_hoteles(
    ciudad: str,
    fecha_entrada: str,
    fecha_vuelta: str,
    adults: int = 1,
    valoracion_numerica: int = 4
) -> Dict[str, Any]:
    """
    Busca hoteles disponibles según los criterios especificados.
    
    Args:
        ciudad: Nombre de la ciudad y país en inglés (ej: "Manchester, United Kingdom")
        fecha_entrada: Fecha de entrada en formato YYYY-MM-DD
        fecha_vuelta: Fecha de salida en formato YYYY-MM-DD
        adults: Número de adultos (1-9)
        valoracion_numerica: Valoración esperada del hotel (1-5)
    
    Returns:
        Dict con los resultados de la búsqueda de hoteles
    """
    try:
        # Mapear la valoración numérica al formato esperado por la API
        valoracion_map = {
            1: "2",  # 1 estrella → 2
            2: "4",  # 2 estrellas → 4
            3: "6",  # 3 estrellas → 6
            4: "8",  # 4 estrellas → 8
            5: "10"  # 5 estrellas → 10
        }
        valoracion = valoracion_map.get(valoracion_numerica, "8")  # Por defecto 8 (4 estrellas)
        
        # Preparar el payload
        payload = {
            "ciudad": ciudad,
            "fecha_entrada": fecha_entrada,
            "fecha_vuelta": fecha_vuelta,
            "adults": min(max(1, adults), 9),  # Asegurar que esté entre 1 y 9
            "valoración": valoracion
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
        url_api = f"{base_url}/hoteles"
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(
            url=url_api,
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error en la búsqueda de hoteles: {response.status_code}")
            return {
                "error": f"Error en la búsqueda: {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        logger.error(f"Error al buscar hoteles: {str(e)}")
        return {
            "error": "Error interno",
            "message": str(e)
        }
