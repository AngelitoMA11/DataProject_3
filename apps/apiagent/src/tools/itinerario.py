import os
import google.generativeai as genai
from firecrawl import FirecrawlApp
import json
import re
import traceback
import datetime
import requests
from typing import List, Dict, Any, TypedDict, Optional

from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ItineraryState(TypedDict):
    traveler_data: Dict[str, Any]
    search_queries: Dict[str, str]
    firecrawl_results: List[Dict[str, Any]]
    structured_research_data: Dict[str, Any]
    initial_itinerary: Optional[str]
    places_to_verify: List[str]
    verification_results: Dict[str, Any]
    final_itinerary: Optional[str]
    tavily_api_key: Optional[str]
    errors: List[str]

def parse_spanish_date(date_str: str) -> datetime.datetime:
    if not date_str or not isinstance(date_str, str):
        raise ValueError("La cadena de fecha no puede estar vacía o no ser una cadena.")
    spanish_months = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }
    # Intenta primero YYYY-MM-DD
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass

    parts = date_str.lower().replace(" de ", " ").split()
    if len(parts) != 3:
        raise ValueError(f"Formato de fecha inesperado: '{date_str}'. Se esperaba 'DD Mes YYYY' o 'YYYY-MM-DD'. Obtenido: {parts}")
    
    day_str, month_str, year_str = parts
    try:
        day = int(day_str)
        year = int(year_str)
        month = spanish_months.get(month_str)
        if month is None:
            raise ValueError(f"Nombre de mes desconocido: '{month_str}' en '{date_str}'")
        return datetime.datetime(year, month, day)
    except ValueError as e:
        raise ValueError(f"Error parseando componentes de fecha '{date_str}': {e}")
    except Exception as e:
        raise ValueError(f"Error inesperado parseando fecha '{date_str}': {e}")


def verify_with_tavily(place_name: str, destination: str, api_key: Optional[str]):
    if not api_key:
        return {"status": "unknown", "message": "Tavily API key no configurada"}
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": f"¿Está {place_name} en {destination} abierto actualmente? ¿Cuáles son los horarios de apertura?",
            "search_depth": "basic", "include_answer": True, "max_results": 3
        }
        headers = {"content-type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        result = response.json()
        if "answer" in result and result["answer"]:
            return {"status": "success", "information": result["answer"],
                    "sources": [source["url"] for source in result.get("results", [])[:2] if source.get("url")]}
        return {"status": "no_answer", "message": "No se encontró respuesta específica o la respuesta estaba vacía.", "raw_result": result}
    except requests.exceptions.RequestException as e:
        print(f"  -> HTTP Error en verificación Tavily para {place_name}: {e}")
        return {"status": "error", "message": f"Error HTTP: {e}"}
    except Exception as e:
        print(f"  -> Error en verificación Tavily para {place_name}: {e}")
        return {"status": "error", "message": str(e)}

def on_firecrawl_activity(activity_data):
    pass

_firecrawl_client = None
_genai_configured = False

def get_firecrawl_client(api_key: str):
    global _firecrawl_client
    if not api_key: raise ValueError("Itinerary Tool: Firecrawl API key no configurada.")
    if _firecrawl_client is None or _firecrawl_client.api_key != api_key:
        _firecrawl_client = FirecrawlApp(api_key=api_key)
    return _firecrawl_client

def configure_genai(api_key: str):
    global _genai_configured
    if not api_key: raise ValueError("Itinerary Tool: Google API key no configurada.")
    if not _genai_configured:
        genai.configure(api_key=api_key)
        _genai_configured = True

# --- LangGraph Node Definitions ---
def generate_queries_node(state: ItineraryState) -> Dict[str, Any]:
    print(f"    [ItineraryTool Node DEBUG] Entrando a: generate_queries_node para {state['traveler_data'].get('destination')}")
    traveler_data = state['traveler_data']
    errors = state.get('errors', []).copy()
    intereses_str = traveler_data.get("intereses", "información general")
    if isinstance(intereses_str, list): intereses_str = ", ".join(intereses_str)

    prompt_text = f"""Basado en Destino: {traveler_data["destination"]}, Intereses: {intereses_str}.
Genera preguntas de búsqueda concisas (una por interés principal, máximo 2-3) para investigación web usando Firecrawl.
Formato de salida:
## [interés_1]
Consulta específica para interés_1

## [interés_2]
Consulta específica para interés_2"""
    search_queries = {}
    try:
        configure_genai(os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            safety_settings={'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE', 'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                             'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE', 'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'}
        )
        response = model.generate_content(prompt_text)
        raw_text = response.text
        # Regex mejorada para capturar interés y query
        sections = re.findall(r"##\s*\[([^\]]+)\]\s*\n(.*?)(?=\n\n##|\n*$)", raw_text, re.DOTALL | re.IGNORECASE)
        search_queries = {interest.strip(): query.strip() for interest, query in sections if query.strip()}
        if not search_queries and intereses_str:
            first_interest = intereses_str.split(',')[0].strip()
            search_queries = {first_interest: f"información completa sobre {first_interest} y otros intereses como {intereses_str} en {traveler_data['destination']}"}
            errors.append(f"Fallo al parsear queries; usando query general para '{first_interest}'.")
        print(f"      Queries generadas: {search_queries}")
    except Exception as e:
        error_msg = f"Error en generate_queries_node: {type(e).__name__} {e}"; print(f"      ERROR: {error_msg}")
        errors.append(error_msg)
        if not search_queries and intereses_str:
             first_interest = intereses_str.split(',')[0].strip()
             search_queries = {first_interest: f"información sobre {intereses_str} en {traveler_data['destination']}"}
    return {"search_queries": search_queries, "errors": errors}


def perform_research_node(state: ItineraryState) -> Dict[str, Any]:
    print(f"    [ItineraryTool Node DEBUG] Entrando a: perform_research_node con queries: {list(state.get('search_queries', {}).keys())}")
    search_queries = state.get('search_queries', {})
    errors = state.get('errors', []).copy()
    firecrawl_results = []
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

    if not firecrawl_api_key:
        errors.append("Firecrawl API key no encontrada en perform_research_node.")
        return {"firecrawl_results": [], "errors": errors}
    
    firecrawl_client = get_firecrawl_client(firecrawl_api_key)

    if not search_queries:
        errors.append("No hay search_queries para perform_research_node.")
        return {"firecrawl_results": [], "errors": errors}

    for interest, query_text in search_queries.items():
        print(f"      Investigando '{interest}': \"{query_text[:50]}...\"")
        try:
            results = firecrawl_client.deep_research(query=query_text, max_depth=1, max_urls=2, time_limit=180, on_activity=on_firecrawl_activity)
            final_analysis, sources, error_val = None, [], None
            if hasattr(results, 'data') and results.data:
                final_analysis = getattr(results.data, 'finalAnalysis', None)
                if hasattr(results.data, 'sources') and results.data.sources:
                    sources = [s.model_dump() if hasattr(s, 'model_dump') else s for s in results.data.sources]
            elif isinstance(results, dict):
                final_analysis, sources, error_val = results.get('finalAnalysis'), results.get('sources', []), results.get('error')
            if hasattr(results, 'error') and results.error: error_val = str(results.error)
            firecrawl_results.append({"interest": interest, "query": query_text, "final_analysis": final_analysis, "sources": sources, "error": error_val})
            if error_val: errors.append(f"Error Firecrawl para '{interest}': {error_val}")
        except Exception as e:
            error_msg = f"Excepción en deep_research para '{query_text}': {type(e).__name__} {e}"
            print(f"        ERROR: {error_msg}");
            errors.append(error_msg)
            firecrawl_results.append({"interest": interest, "query": query_text, "final_analysis": None, "sources": [], "error": str(e)})
    output = {"firecrawl_results": firecrawl_results, "errors": errors}
    print(f"    [ItineraryTool Node DEBUG] Saliendo de: perform_research_node, resultados: {len(firecrawl_results)}")
    return output



def process_research_node(state: ItineraryState) -> Dict[str, Any]:
    print(f"    [ItineraryTool Node DEBUG] Entrando a: process_research_node")
    firecrawl_results = state.get('firecrawl_results', [])
    errors = state.get('errors', []).copy()
    structured_data = {}

    if not firecrawl_results:
        errors.append("No hay resultados de Firecrawl para procesar.")
        return {"structured_research_data": {}, "errors": errors}

    for result_item in firecrawl_results:
        interest = result_item.get("interest", "desconocido")
        final_analysis = result_item.get("final_analysis")
        sources = result_item.get("sources", [])
        research_error = result_item.get("error")

        # Cada 'interest' tendrá su propia entrada en structured_data
        if research_error and not final_analysis:
            structured_data[interest] = {"status": "failed_research", "error": str(research_error), "full_analysis": None, "sources": []}
        elif not final_analysis:
            structured_data[interest] = {"status": "no_data", "error": "No se encontró análisis de Firecrawl.", "full_analysis": None, "sources": sources}
        else:
            structured_data[interest] = {"status": "success", "full_analysis": final_analysis, "sources": sources, "warning": str(research_error) if research_error else None}
            
    return {"structured_research_data": structured_data, "errors": errors}


def generate_itinerary_node(state: ItineraryState) -> Dict[str, Any]:
    print(f"    [ItineraryTool Node DEBUG] Entrando a: generate_itinerary_node")
    structured_data = state.get('structured_research_data', {})
    traveler_data = state['traveler_data']
    errors = state.get('errors', []).copy()
    trip_days = 3
    dep_date_str, arr_date_str = traveler_data.get("departure_date"), traveler_data.get("arrival_date")
    flight_details = traveler_data.get("flight_details")
    hotel_details = traveler_data.get("hotel_details")

    try:
        if dep_date_str and arr_date_str:
            departure = parse_spanish_date(dep_date_str)
            arrival = parse_spanish_date(arr_date_str)
            calculated_days = (arrival - departure).days + 1
            if calculated_days > 0: trip_days = calculated_days
            else: errors.append(f"Fechas inválidas (salida después de llegada), usando {trip_days} días por defecto.")
        else: errors.append(f"Fechas de salida o llegada no especificadas, usando {trip_days} días por defecto.")
    except ValueError as ve: errors.append(f"Error parseando fechas: {ve}, usando {trip_days} días por defecto.")
    
    context_parts = ["INVESTIGACIÓN PARA ITINERARIO:"]
    has_research_data = False
    for interest, data_for_interest in structured_data.items(): # Iterar sobre el dict
        if data_for_interest.get("status") == "success" and data_for_interest.get("full_analysis"):
            has_research_data = True
            context_parts.append(f"\n## Investigación sobre {interest.upper()}:\n{data_for_interest['full_analysis']}")
            if data_for_interest.get("sources"):
                source_links = [s.get("url") for s in data_for_interest["sources"] if isinstance(s, dict) and s.get("url")]
                if source_links:
                    context_parts.append(f"Fuentes principales para {interest}: {', '.join(source_links)}")
        elif data_for_interest.get("error") or data_for_interest.get("status") == "no_data":
             context_parts.append(f"\n## Investigación sobre {interest.upper()}: {data_for_interest.get('error', 'No se encontró información detallada.')}")
    
    if not has_research_data and not errors: # Solo si no hay data Y no hay errores previos que expliquen por qué
        context_parts.append(f"No se pudo obtener información detallada de la web. Generar itinerario general para {traveler_data['destination']} basado en los intereses: {traveler_data['intereses']}.")
    
    research_context = "\n".join(context_parts)
    max_context_len = 28000 
    if len(research_context) > max_context_len:
        research_context = research_context[:max_context_len] + "\n... (contexto truncado)"
        errors.append("Contexto de investigación truncado debido a su longitud.")

    prompt_text = f"""Eres un experto planificador de viajes. Crea un itinerario detallado y atractivo.
Destino: {traveler_data['destination']}
Fechas: Desde {dep_date_str or 'N/A'} hasta {arr_date_str or 'N/A'} (Total: {trip_days} días)
Intereses del Viajero: {traveler_data.get('intereses', 'Generales')}
Información de Vuelo (si provista): {flight_details or 'No provista'}
Información de Hotel (si provista): {hotel_details or 'No provista'}

Contexto de Investigación Adicional:
{research_context}

Instrucciones para el Itinerario:
- Formato: Markdown.
- Encabezado principal: "Itinerario para [Destino] ([Fechas]) - Intereses: [Intereses]"
- Estructura: Día por día (Ej: "Día 1: [Fecha si es posible] - [Título Temático del Día]").
- Por cada día:
    - Mañana (aprox. 9:00-13:00): 1-2 actividades principales.
    - Comida (aprox. 13:00-14:00): Sugerencia de tipo de comida o restaurante (opcional, indicar si es solo sugerencia).
    - Tarde (aprox. 14:00-18:00): 1-2 actividades.
    - Noche (opcional): Sugerencia de cena o actividad nocturna.
- Descripciones: Breves pero atractivas (2-3 frases por actividad).
- Logística: Incluir nombres de lugares específicos. Mencionar si se requieren reservas o compra anticipada de entradas.
- Consejos: Un "Consejo del día" relevante al final de cada día.
- Tono: Entusiasta y útil.
- Idioma: Español.
- Realismo: Asegúrate que las actividades por día sean logísticamente posibles.
Ten en cuenta que estamos a 21 de mayo de 2025, y el itinerario es para un viaje a {traveler_data['destination']}.
No digas nada de antes de la fecha, ni menciones que eres un modelo de IA.
Genera el itinerario ahora."""
    itinerary_md = "## Lo sentimos\nNo se pudo generar el itinerario debido a un error interno."
    try:
        configure_genai(os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash", 
            safety_settings={'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE', 'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE', 
                             'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE', 'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'}
        )
        response = model.generate_content(prompt_text)
        itinerary_md = response.text
    except Exception as e: 
        error_msg = f"Error en generate_itinerary_node llamando a Gemini: {type(e).__name__} {e}"; 
        print(f"      ERROR: {error_msg}"); 
        errors.append(error_msg)
        itinerary_md = f"## Error al Generar Itinerario\nOcurrió un problema durante la generación: {error_msg}"
    
    return {"initial_itinerary": itinerary_md, "errors": errors}


def extract_places_node(state: ItineraryState) -> Dict[str, Any]:
    print(f"    [ItineraryTool Node DEBUG] Entrando a: extract_places_node")
    initial_itinerary = state.get('initial_itinerary')
    traveler_data = state['traveler_data'] 
    errors = state.get('errors', []).copy()
    places = []

    if not initial_itinerary or "No se pudo generar" in initial_itinerary or "Error al Generar Itinerario" in initial_itinerary:
        errors.append("No hay itinerario válido para extraer lugares.")
        return {"places_to_verify": [], "errors": errors}

    prompt_text = f"""Del siguiente itinerario para un viaje a {traveler_data.get('destination', 'un destino')}, 
extrae hasta 7 nombres ÚNICOS y específicos de lugares mencionados que sean atracciones turísticas, museos, restaurantes notables, parques importantes u otros puntos de interés que un viajero visitaría.
No extraigas nombres de ciudades, barrios generales, tipos de comida, o frases como "Comida informal".
Prioriza lugares que se beneficiarían de una verificación de horarios o disponibilidad.
Devuelve la lista como un array JSON de strings. Si no hay lugares específicos, devuelve un array vacío.

Itinerario:
---
{initial_itinerary[:4000]} 
---
Array JSON de lugares:"""
    try:
        configure_genai(os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={"response_mime_type": "application/json"},
            safety_settings={'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE', 'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE', 
                             'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE', 'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'}
        )
        response = model.generate_content(prompt_text)
        
        try:
            places_list_from_llm = json.loads(response.text)
            if isinstance(places_list_from_llm, list):
                places = [str(p).strip() for p in places_list_from_llm if isinstance(p, str) and str(p).strip()]
                places = list(dict.fromkeys(places))[:7] 
            else:
                errors.append(f"Extracción de lugares devolvió JSON pero no una lista: {type(places_list_from_llm)}")
                print(f"      WARN: Extracción de lugares (JSON) no fue una lista. Texto: '{response.text[:100]}...'")
        except json.JSONDecodeError as jde:
            errors.append(f"Fallo al decodificar JSON de extracción de lugares: {jde}. Texto: {response.text[:100]}")
            print(f"      WARN: Fallo JSON en extract_places. Texto: '{response.text[:100]}...'")
            # Fallback a regex si JSON falla
            raw_places = re.findall(r'\b[A-Z][A-Za-zÀ-ÖØ-öø-ÿ\'\s.-]{5,}[A-Za-zÀ-ÖØ-öø-ÿ\']\b', initial_itinerary)
            ignore_keywords = ["día", "mañana", "tarde", "noche", "consejo", "almuerzo", "comida", "cena", 
                               "restaurante", "museo", "parque", "jardín", "catedral", "iglesia",
                               "barrio", "calle", "plaza", "avenida", "distrito", "ciudad",
                               traveler_data.get('destination','').split(',')[0]
                              ] + [s.strip() for s in traveler_data.get('intereses','').split(',')]
            
            filtered_places = []
            for p_raw in raw_places:
                p = p_raw.strip(" .,;")
                is_generic = any(kw.lower() in p.lower() for kw in ignore_keywords)
                has_multiple_words = len(p.split()) > 1
                if has_multiple_words and not is_generic:
                    filtered_places.append(p)
            places = list(dict.fromkeys(filtered_places))[:7]

        print(f"      Lugares extraídos para verificar: {places}")
    except Exception as e: 
        error_msg = f"Error en extract_places_node llamando a Gemini: {type(e).__name__} {e}"
        print(f"      ERROR: {error_msg}")
        errors.append(error_msg)
    
    return {"places_to_verify": places, "errors": errors}

       
def verify_places_node(state: ItineraryState) -> Dict[str, Any]:
    print(f"    [ItineraryTool Node DEBUG] Entrando a: verify_places_node")
    places_to_verify = state.get('places_to_verify', [])
    traveler_data = state['traveler_data']
    tavily_api_key = state.get('tavily_api_key')
    errors = state.get('errors', []).copy()
    verification_results = {}

    if not tavily_api_key:
        print("      WARN: Tavily API key no disponible. Saltando verificación de lugares.")
        return {"verification_results": {"status": "skipped_no_key", "message": "Tavily API key no configurada."}, "errors": errors}
    
    if not places_to_verify:
        print("      INFO: No hay lugares para verificar.")
        return {"verification_results": {}, "errors": errors}

    for place in places_to_verify:
        destination_name = traveler_data.get('destination', "") 
        print(f"      Verificando '{place}' en '{destination_name}' con Tavily...")
        verification_results[place] = verify_with_tavily(place, destination_name, tavily_api_key)
    
    return {"verification_results": verification_results, "errors": errors}


def enhance_itinerary_node(state: ItineraryState) -> Dict[str, Any]:
    print(f"    [ItineraryTool Node DEBUG] Entrando a: enhance_itinerary_node")
    initial_itinerary = state.get('initial_itinerary', "")
    verification_results = state.get('verification_results', {})
    errors = state.get('errors', []).copy()

    if not initial_itinerary or "No se pudo generar" in initial_itinerary or "Error al Generar Itinerario" in initial_itinerary:
        errors.append("No hay itinerario válido para mejorar.")
        return {"final_itinerary": initial_itinerary, "errors": errors}

    if not verification_results or verification_results.get("status") == "skipped_no_key" or not any(v_res.get("status") == "success" for v_res in verification_results.values() if isinstance(v_res, dict)):
        print("      INFO: No hay resultados de verificación útiles o se saltó. Devolviendo itinerario inicial.")
        return {"final_itinerary": initial_itinerary, "errors": errors}

    verification_section_parts = ["\n\n## ✅ Verificación de Lugares (Información Reciente)\n"]
    has_useful_verification_info = False
    for place, result_data in sorted(verification_results.items()):
        if isinstance(result_data, dict):
            if result_data.get("status") == "success" and result_data.get("information"):
                has_useful_verification_info = True
                verification_section_parts.append(f"### {place}\n{result_data['information']}")
                if result_data.get("sources"):
                    verification_section_parts.append("Fuentes: " + ", ".join(f"<{s}>" for s in result_data['sources'] if s))
                verification_section_parts.append("\n")
            elif result_data.get("status") == "no_answer":
                # Considerar si añadir esto o no. Por ahora, lo omitimos si no hay info positiva.
                # has_useful_verification_info = True
                # verification_section_parts.append(f"### {place}\nNo se encontró información específica sobre horarios o estado actual. Se recomienda verificar directamente con el lugar.\n")
                pass

    if not has_useful_verification_info:
        print("      INFO: No se encontró información de verificación útil (solo 'no_answer' o errores). Devolviendo itinerario inicial.")
        return {"final_itinerary": initial_itinerary, "errors": errors}

    enhanced_itinerary = initial_itinerary
    verification_text = "".join(verification_section_parts)
    
    possible_insertion_points = [
        r'^(##\s*(?:Consejos\s*Finales|Recomendaciones\s*Generales|Notas\s*Adicionales)\b)',
        r'^(##\s*Fin\s*del\s*Itinerario\b)'
    ]
    inserted = False
    for pattern in possible_insertion_points:
        match = re.search(pattern, enhanced_itinerary, re.MULTILINE | re.IGNORECASE)
        if match:
            insert_pos = match.start()
            enhanced_itinerary = enhanced_itinerary[:insert_pos].rstrip() + "\n\n" + verification_text.rstrip() + "\n\n" + enhanced_itinerary[insert_pos:]
            inserted = True
            break
    
    if not inserted:
        enhanced_itinerary = enhanced_itinerary.rstrip() + "\n\n" + verification_text.rstrip()
    
    print(f"    [ItineraryTool Node DEBUG] Saliendo de: enhance_itinerary_node, itinerario {'mejorado.' if has_useful_verification_info else 'sin cambios.'}")
    return {"final_itinerary": enhanced_itinerary, "errors": errors}


def save_results_node(state: ItineraryState) -> Dict[str, Any]:
    print(f"    [ItineraryTool Node DEBUG] Entrando a: save_results_node")
    final_itinerary_md = state.get('final_itinerary', state.get('initial_itinerary'))
    errors = state.get('errors', []).copy()

    if not final_itinerary_md or \
       any(err_indicator in final_itinerary_md for err_indicator in ["No se pudo generar", "Lo sentimos", "Error al Generar Itinerario", "Error Crítico Interno"]):
        
        error_details = "; ".join(list(set(errors))) if errors else "Causa desconocida."
        final_itinerary_md = (f"## Error en la Generación del Itinerario\n\n"
                              f"Lamentablemente, no se pudo generar un itinerario completo en esta ocasión.\n"
                              f"Detalles del problema: {error_details}\n\n"
                              f"Por favor, intente de nuevo más tarde o con diferentes parámetros.")
        if "Fallo en generación de itinerario final." not in errors:
             errors.append("Fallo en generación de itinerario final.")
    
    output = {"final_itinerary": final_itinerary_md, "errors": list(set(errors))} 
    print(f"    [ItineraryTool Node DEBUG] Saliendo de: save_results_node, itinerario final (primeras 50 chars): {str(final_itinerary_md)[:50].replace(os.linesep,' ')}")
    return output

def should_verify(state: ItineraryState) -> str:
    if bool(state.get('tavily_api_key')) and \
       state.get('places_to_verify') and \
       not (isinstance(state.get('verification_results'), dict) and \
            state.get('verification_results', {}).get('status') == 'skipped_no_key'):
        print("      [ItineraryTool CondEdge] extract_places -> verify_places")
        return "verify_places"
    print("      [ItineraryTool CondEdge] extract_places -> enhance_itinerary (saltando verificación)")
    return "enhance_itinerary"

_compiled_itinerary_app_tool = None 
def get_compiled_itinerary_app_tool():
    global _compiled_itinerary_app_tool
    if _compiled_itinerary_app_tool is None:
        print("  [ItineraryTool] Compilando grafo interno por primera vez...")
        workflow = StateGraph(ItineraryState)
        workflow.add_node("generate_queries", generate_queries_node)
        workflow.add_node("perform_research", perform_research_node)
        workflow.add_node("process_research", process_research_node)
        workflow.add_node("generate_itinerary", generate_itinerary_node)
        workflow.add_node("extract_places", extract_places_node)
        workflow.add_node("verify_places", verify_places_node)
        workflow.add_node("enhance_itinerary", enhance_itinerary_node)
        workflow.add_node("save_results", save_results_node)

        workflow.set_entry_point("generate_queries")
        workflow.add_edge("generate_queries", "perform_research")
        workflow.add_edge("perform_research", "process_research")
        workflow.add_edge("process_research", "generate_itinerary")
        workflow.add_edge("generate_itinerary", "extract_places")
        workflow.add_conditional_edges(
            "extract_places", 
            should_verify, 
            {"verify_places": "verify_places", "enhance_itinerary": "enhance_itinerary"}
        )
        workflow.add_edge("verify_places", "enhance_itinerary")
        workflow.add_edge("enhance_itinerary", "save_results")
        workflow.add_edge("save_results", END)
        
        _compiled_itinerary_app_tool = workflow.compile()
        print("  [ItineraryTool] Grafo interno compilado.")
    return _compiled_itinerary_app_tool

class ItineraryGeneratorToolInput(BaseModel):
    destination: str = Field(description="El destino del viaje (ej., 'Lisboa, Portugal').")
    departure_date: str = Field(description="Fecha de salida en lenguaje natural español (ej., '21 de mayo de 2025' o '2025-05-20').")
    arrival_date: str = Field(description="Fecha de regreso en lenguaje natural español (ej., '28 de mayo de 2025' o '2025-05-28').")
    intereses: str = Field(description="Intereses del viajero, separados por comas si son varios (ej., 'arte callejero, comida local, historia').")
    flight_details: Optional[str] = Field(default=None, description="Detalles del vuelo si ya se conocen (opcional).")
    hotel_details: Optional[str] = Field(default=None, description="Detalles del hotel si ya se conocen (opcional).")


@tool(args_schema=ItineraryGeneratorToolInput)
def comprehensive_itinerary_generator_tool(
    destination: str,
    departure_date: str,
    arrival_date: str,
    intereses: str,
    flight_details: Optional[str] = None,
    hotel_details: Optional[str] = None
) -> str:
    """
    Use this tool to generate a detailed travel itinerary for a specific destination and dates.
    Generates a comprehensive, personalized travel itinerary using deep web research and optional real-time verification.
    Requires GOOGLE_API_KEY, FIRECRAWL_API_KEY. TAVILY_API_KEY is optional for verification.
    Input dates should be in Spanish natural language (e.g., '21 de mayo de 2025') or YYYY-MM-DD.
    Returns a detailed itinerary in Markdown format.
    """
    print(f"🚀 [ItineraryTool] Iniciando para Destino: '{destination}', Fechas: {departure_date} a {arrival_date}, Intereses: '{intereses}'")
    if flight_details: print(f"  Flight Details: {flight_details}")
    if hotel_details: print(f"  Hotel Details: {hotel_details}")

    google_key = os.getenv("GOOGLE_API_KEY")
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    tavily_key_to_use = os.getenv("TAVILY_API_KEY")

    if not google_key: return "Error en ItineraryTool: GOOGLE_API_KEY no configurada en el entorno."
    if not firecrawl_key: return "Error en ItineraryTool: FIRECRAWL_API_KEY no configurada en el entorno."
    if not tavily_key_to_use: print("  [ItineraryTool WARN] TAVILY_API_KEY no configurada. Verificación deshabilitada.")

    try:
        configure_genai(google_key)
    except Exception as e:
        print(f"  [ERROR ItineraryTool] Fallo al configurar Google GenAI: {e}")
        return f"Error en ItineraryTool: Configuración API Google fallida - {str(e)}"

    app = get_compiled_itinerary_app_tool()

    initial_state: ItineraryState = {
        "traveler_data": {
            "destination": destination, "departure_date": departure_date, 
            "arrival_date": arrival_date, "intereses": intereses,
            "flight_details": flight_details, "hotel_details": hotel_details
        },
        "search_queries": {}, "firecrawl_results": [], "structured_research_data": {}, 
        "initial_itinerary": None, "places_to_verify": [], "verification_results": {}, 
        "final_itinerary": None, "tavily_api_key": tavily_key_to_use, "errors": []
    }

    final_graph_state = None
    accumulated_errors_from_stream = []

    print("  [ItineraryTool] Invocando stream del grafo interno...")
    try:
        for event_part in app.stream(initial_state, {"recursion_limit": 25}, stream_mode="values"):
            final_graph_state = event_part 

            current_errors_in_state = final_graph_state.get('errors', [])
            if current_errors_in_state:
                for err_msg in current_errors_in_state:
                    if err_msg not in accumulated_errors_from_stream:
                        accumulated_errors_from_stream.append(err_msg)
        
        print("  [ItineraryTool] Stream del grafo interno completado.")
        
        if not isinstance(final_graph_state, dict):
            final_error_message = (f"El grafo interno no produjo un estado de diccionario válido como salida final "
                                   f"(final_graph_state es tipo {type(final_graph_state)}).")
            if not accumulated_errors_from_stream:
                accumulated_errors_from_stream.append(final_error_message)
            error_summary = "; ".join(list(set(accumulated_errors_from_stream)))
            print(f"  [ItineraryTool ERROR] {final_error_message}. Errores acumulados: {error_summary}")
            return f"Error en ItineraryTool: Proceso interno falló gravemente. Detalles: {error_summary}"

        final_itinerary_markdown = final_graph_state.get("final_itinerary")
        errors_in_final_state = final_graph_state.get("errors", []) 
        all_unique_errors = list(set(accumulated_errors_from_stream + errors_in_final_state))

        if not final_itinerary_markdown or \
           any(err_indicator in final_itinerary_markdown for err_indicator in ["No se pudo generar", "Lo sentimos", "Error Crítico Interno", "Error al Generar Itinerario", "Error en la Generación del Itinerario"]):
            
            error_summary = "; ".join(all_unique_errors) if all_unique_errors else "Error desconocido en la generación del itinerario."
            print(f"  [ItineraryTool ERROR] Itinerario no satisfactorio o con errores finales. Errores: {error_summary}")
            response_content = final_itinerary_markdown if final_itinerary_markdown else f"No se pudo generar el itinerario. Problemas: {error_summary}"
            if all_unique_errors and "Advertencias/Errores" not in response_content and "Problemas Adicionales" not in response_content:
                 response_content += "\n\n---\n⚠️ **Problemas Adicionales (Tool Interna):**\n" + "\n".join(f"- {e}" for e in all_unique_errors)
            return response_content.strip()

        if all_unique_errors:
            final_itinerary_markdown += "\n\n---\n⚠️ **Advertencias/Información Adicional (Tool Interna):**\n" + "\n".join(f"- {e}" for e in all_unique_errors)
        
        print(f"  [ItineraryTool] Itinerario generado exitosamente para '{destination}'. Longitud: {len(final_itinerary_markdown)}")
        return final_itinerary_markdown.strip()

    except Exception as e:
        print(f"  [ERROR ItineraryTool] Excepción CRÍTICA durante la ejecución del stream del grafo interno: {type(e).__name__}: {e}")
        traceback.print_exc()
        error_context = "; ".join(list(set(accumulated_errors_from_stream))) if accumulated_errors_from_stream else "Sin errores específicos del stream antes de la excepción."
        return (f"Error crítico irrecuperable en ItineraryTool ({type(e).__name__}: {e}). "
                f"Errores previos del stream: {error_context}")