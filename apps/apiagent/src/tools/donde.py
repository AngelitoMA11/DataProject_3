import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re
from typing import TypedDict, Annotated, List, Union, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool # Importar @tool
import uuid
import requests

# --- Configuration & Initialization (del código original del explorador) ---
# Estas deberían cargarse una vez en tu entorno principal.
# load_dotenv() # Asegúrate que esto se llame una vez en tu aplicación principal
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") # Aunque no se usa directamente en el flujo principal

# --- System Prompt del Explorador (sin cambios) ---
system_prompt_explorador = """
Rol y Objetivo Primario

Eres el "Explorador de Destinos", un asistente de viajes experto, amigable y muy perspicaz. Tu ÚNICO objetivo principal es ayudar a los usuarios a descubrir y elegir un DESTINO DE VIAJE IDEAL Y ESPECÍFICO (una CIUDAD concreta) basado en sus preferencias, intereses y necesidades. Una vez que el usuario haya confirmado esta CIUDAD específica, tu tarea habrá concluido.

Capacidades Adicionales

Búsqueda de Información: Si necesitas más detalles sobre un destino potencial que el usuario está considerando, para comparar opciones, o para enriquecer tu descripción de un lugar, **no dudes en solicitar una búsqueda**. Para hacerlo, en tu respuesta, incluye la frase [BUSCAR_INFO: "término de búsqueda específico aquí"]. Por ejemplo: [BUSCAR_INFO: "mejores playas cerca de Lisboa en julio"] o [BUSCAR_INFO: "actividades culturales en Kioto para familias"]. Yo realizaré la búsqueda y te daré los resultados para que continúes la conversación. **Utiliza esta herramienta libremente siempre que creas que puede aportar valor al usuario para definir su destino o conocerlo mejor.**

**MUY IMPORTANTE - GESTIÓN DE RESULTADOS DE BÚSQUEDA:**
1. Cuando YO (el sistema) te proporcione resultados de una búsqueda que solicitaste con [BUSCAR_INFO: ...], tu SIGUIENTE RESPUESTA DEBE enfocarse en UTILIZAR Y PRESENTAR esos resultados al usuario para ayudarle a decidir sobre un destino.
2. NO DEBES REPETIR la misma solicitud [BUSCAR_INFO: ...] en la respuesta inmediata después de recibir los resultados para esa misma consulta. Asume que ya tienes la información.
3. Si los resultados que te proporcioné no son suficientes o no son lo que esperabas, explica al usuario qué información adicional necesitas para ayudarle a elegir un destino y, si es necesario, formula una solicitud [BUSCAR_INFO: ...] *diferente* y más específica en tu siguiente turno, o pide al usuario que aclare. NUNCA repitas la misma búsqueda inmediatamente.

Tono y Estilo de Comunicación

Cercano y conversacional, como un amigo entusiasta que adora viajar.
Evita lenguaje corporativo o respuestas genéricas.
Utiliza emoji ocasionalmente para dar vida a la conversación 🌴✈️🏞️.
Personalidad cálida pero profesional, transmitiendo pasión por los viajes.
Ocasionalmente comparte pequeñas anécdotas o datos curiosos sobre destinos.

Proceso de Interacción: Definición del Destino

Tu ÚNICA Y MÁS IMPORTANTE TAREA es ayudar al usuario a elegir una CIUDAD específica. Haz preguntas sobre sus intereses (ej. playa, montaña, cultura, aventura, relax), tipo de viaje deseado, presupuesto general inicial (si lo mencionan espontáneamente, si no, no es prioritario), y cualquier otra preferencia que ayude a concretar una CIUDAD.
**Intenta recordar los intereses principales que el usuario asocia con su elección final de CIUDAD.**

**Usa tu capacidad de [BUSCAR_INFO: ...] proactivamente para obtener más datos sobre CIUDADES que puedan encajar o que el usuario mencione, incluso si no lo pide directamente. El objetivo es ofrecer la mayor cantidad de información relevante posible para ayudarle a decidir.**

Si el usuario da respuestas vagas sobre el destino, sigue preguntando y ofreciendo sugerencias (apoyándote en búsquedas si es útil) hasta que se decida por una CIUDAD específica (e.g., "París", "Kioto", "Roma", "Barcelona").

NO intentes recopilar NINGUNA OTRA INFORMACIÓN (como país de origen, fechas, número de viajeros, etc., a menos que sea estrictamente para diferenciar entre dos ciudades con el mismo nombre, y solo si es absolutamente necesario para definir la CIUDAD). Tu labor termina una vez que la CIUDAD está clara y confirmada.

El objetivo es que el campo "Destino Elegido" del resumen final sea el nombre de una CIUDAD real y específica, y no frases como "aún por decidir", "un lugar cálido" o un país/región.

Finalización de la Conversación

Una vez que el usuario haya elegido una CIUDAD específica y la haya CONFIRMADO CLARAMENTE (por ejemplo, diciendo "Sí, quiero ir a París" o "Perfecto, elijamos Tokio"), y SOLO ENTONCES:
1. En tu respuesta, felicítalo por su elección.
2. Confirma CLARAMENTE la CIUDAD elegida.
3. Si el usuario mencionó intereses específicos para esa CIUDAD durante la conversación, intenta incluirlos brevemente en tu confirmación (ej. "¡Excelente elección ir a Kioto para disfrutar de sus templos y jardines!").
4. Finaliza la conversación INMEDIATAMENTE después de esta confirmación. No hagas más preguntas.

Al finalizar, después de que el usuario confirme la CIUDAD y tú hayas dado tu mensaje de confirmación final, tu respuesta DEBE incluir un resumen MUY BREVE con EXACTAMENTE este formato:

Destino Elegido: [CIUDAD ESPECÍFICA ELEGIDA]
Intereses Clave en Destino: [Intereses mencionados por el usuario para esa CIUDAD, si los hubo, o "No especificados"]

Es CRUCIAL que el campo "Destino Elegido" NUNCA esté vacío o sea una frase genérica. Debe ser una CIUDAD específica. Si el usuario elige un país o región, guíalo suavemente para que elija una ciudad dentro de ese país/región.

Restricciones Clave

Prioridad Absoluta al Destino (CIUDAD): La elección de una CIUDAD específica es tu ÚNICO objetivo. No te desvíes.
NO generar resumen sin CIUDAD clara: Bajo NINGUNA circunstancia generes el resumen final si el campo "Destino Elegido" no es una CIUDAD concreta y confirmada.
Confirmación Explícita: Espera a que el usuario confirme explícitamente su elección de CIUDAD antes de finalizar.
Finalización Inmediata: Una vez que confirmes la elección del usuario, termina la conversación. No sigas preguntando.
NO recopilar datos adicionales: Una vez elegida la CIUDAD, no pidas más información. Tu trabajo ha terminado.
Formato del Resumen Final: El resumen final DEBE seguir el formato especificado con exactitud.
"""

# --- Helper Functions del Explorador (sin cambios, deben estar definidas aquí) ---
def extract_final_destination_info(text: str) -> dict:
    data = {"Destino Elegido": "", "intereses": ""} 
    dest_match = re.search(r"Destino Elegido:\s*(.*?)(?=\nIntereses Clave en Destino:|\n\s*$|$)", text, re.IGNORECASE | re.DOTALL)
    if dest_match: data["Destino Elegido"] = dest_match.group(1).strip()
    intereses_match = re.search(r"Intereses Clave en Destino:\s*(.*?)(?=\n\s*$|$)", text, re.IGNORECASE | re.DOTALL)
    if intereses_match: data["intereses"] = intereses_match.group(1).strip()
    return data

def save_to_json(data: dict, filename="travel_data_discovery_langgraph.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\n[INFO] Explorador: Datos guardados en '{filename}'") # Modificado para clarificar
        return True
    except Exception as e:
        print(f"\n[ERROR] Explorador: No se pudo guardar en JSON: {e}")
        return False

def tavily_search(query: str) -> str:
    if not TAVILY_API_KEY: return "Error: Tavily API key no configurada."
    try:
        print(f"[EXPLORADOR_TOOL_CALL] Tavily search: \"{query}\"")
        response = requests.post("https://api.tavily.com/search", json={ "api_key": TAVILY_API_KEY, "query": query, "search_depth": "basic", "include_answer": True, "max_results": 5 })
        response.raise_for_status()
        results = response.json()
        output_parts = []
        if results.get("answer"): output_parts.append(f"Respuesta directa de Tavily: {results['answer']}")
        if results.get("results"):
            sources_info = []
            for r in results["results"]: sources_info.append(f"- Título: {r.get('title', 'N/A')}\n  URL: {r.get('url', 'N/A')}\n  Contenido: {r.get('content', 'No hay contenido adicional aquí.')[:300]}...")
            if sources_info: output_parts.append("Fuentes y fragmentos relevantes:\n" + "\n".join(sources_info))
        if not output_parts: return "No se encontraron resultados directos o detallados en Tavily."
        return "\n\n".join(output_parts)
    except Exception as e: return f"Error durante la búsqueda con Tavily: {e}"

# Firecrawl no se usa activamente por el explorador, pero se mantiene si es parte de tu código.
# from firecrawl import FirecrawlApp
# def firecrawl_scrape(url: str) -> str: ...

# --- LangGraph State Definition del Explorador (sin cambios) ---
class TravelAgentState(TypedDict): # Este es el estado INTERNO del explorador
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    user_input: str
    api_configured: bool
    summary_detected: bool 
    extracted_data: dict 
    final_answer_generated: bool 
    search_query: Optional[str]
    search_results: Optional[str]
    has_searched_this_invoke: bool
    last_executed_search_query: Optional[str]

# --- Variables Globales para el Grafo y Modelo del Explorador ---
_explorer_llm_model = None
_explorer_app = None # Este será el grafo compilado del explorador

# --- Nodos del Grafo del Explorador ---
# IMPORTANTE: Debes definir aquí tus funciones:
# explorador_node (MODIFICADA para usar _explorer_llm_model en lugar de llm_model)
# web_search_node (puede usar tavily_search directamente)
# extract_data_node
# save_data_node
# route_after_explorador
# route_after_extraction

# Ejemplo de cómo adaptar explorador_node (DEBES COMPLETAR ESTO CON TU CÓDIGO):
def explorador_node(state: TravelAgentState) -> dict: # Nombre original mantenido por simplicidad
    global _explorer_llm_model # Acceder al modelo LLM específico del explorador
    if not _explorer_llm_model:
        return {"messages": [AIMessage(content="Error: LLM del Explorador no inicializado.")], "summary_detected": False, "search_query": None, "search_results": None, "has_searched_this_invoke": state.get("has_searched_this_invoke", False), "last_executed_search_query": state.get("last_executed_search_query")}

    current_messages = list(state["messages"])
    last_executed_query = state.get("last_executed_search_query")

    if state.get("search_results"):
        print(f"[EXPLORADOR_DEBUG] Añadiendo resultados de búsqueda (para query: '{last_executed_query}') al contexto del LLM.")
        current_messages.append(SystemMessage(content=f"[Resultados de la búsqueda para \"{last_executed_query}\"]:\n{state['search_results']}"))
    
    history_for_gemini = []
    for msg in current_messages:
        if isinstance(msg, SystemMessage) and msg.content != system_prompt_explorador: # Evitar duplicar el prompt del sistema principal del explorador
             history_for_gemini.append({'role': 'user', 'parts': [f"[CONTEXTO DEL SISTEMA/HERRAMIENTA]:\n{msg.content}"]})
        elif isinstance(msg, HumanMessage):
            history_for_gemini.append({'role': 'user', 'parts': [msg.content]})
        elif isinstance(msg, AIMessage):
            history_for_gemini.append({'role': 'model', 'parts': [msg.content]})

    ai_response_text = ""
    try:
        # Asegurar que el historial no esté vacío para start_chat
        if not history_for_gemini: 
             last_user_message_content = [state.get("user_input", "Hola")]
             # Si history_for_gemini está vacío, significa que solo tenemos el mensaje de saludo del sistema
             # y el primer mensaje del usuario. En este caso, el system_prompt_explorador ya está configurado en el modelo.
             # El historial para start_chat puede estar vacío o solo contener el último mensaje del usuario si es el primero.
             # Sin embargo, nuestro estado 'messages' ya contiene el saludo de IA y el primer humano.
             # El enfoque correcto aquí es pasar el historial como está.
             if len(history_for_gemini) <= 1:
                  chat_session = _explorer_llm_model.start_chat(history=[])
                  last_user_message_content = history_for_gemini[0]['parts'] if history_for_gemini else [state.get("user_input", "Hola")]
             else:
                  chat_session = _explorer_llm_model.start_chat(history=history_for_gemini[:-1])
                  last_user_message_content = history_for_gemini[-1]['parts']

        else: # Hay historial
            # Si el último mensaje es del modelo, pero necesitamos enviar uno del usuario (el actual state["user_input"])
            # esto es manejado por cómo se construye `state_for_invoke` en la herramienta.
            # `state_for_invoke["messages"]` ya tendrá el último HumanMessage.
             chat_session = _explorer_llm_model.start_chat(history=history_for_gemini[:-1] if len(history_for_gemini) > 1 else [])
             last_user_message_content = history_for_gemini[-1]['parts']


        print(f"[EXPLORADOR_DEBUG] Enviando a Gemini (último mensaje/contexto): {str(last_user_message_content)[:300]}...")
        # Aquí, send_message espera el contenido actual del usuario.
        # La forma en que se construye `state_for_invoke` en la herramienta asegura que `messages`
        # termina con el HumanMessage actual, así que `history_for_gemini[-1]` es el correcto.
        response = chat_session.send_message(last_user_message_content)
        ai_response_text = response.text
    except Exception as e:
        print(f"Explorador: Error generando response de Gemini: {e}")
        ai_response_text = "Uff, parece que mis mapas mentales se mezclaron un poco. ¿Podrías repetirme eso?"

    search_request_match = re.search(r'\[BUSCAR_INFO:\s*\"(.*?)\"\]', ai_response_text)
    search_query_for_tool = None
    if search_request_match:
        potential_query = search_request_match.group(1).strip()
        if state.get("search_results") and last_executed_query and potential_query.lower() == last_executed_query.lower():
            print(f"[EXPLORADOR_INFO] LLM intentó búsqueda redundante para '{potential_query}'. Se eliminará.")
            ai_response_text = ai_response_text.replace(search_request_match.group(0), "").strip()
        else:
            search_query_for_tool = potential_query
            print(f"[EXPLORADOR_INFO] LLM solicitó búsqueda: '{search_query_for_tool}'")
    
    summary_detected_flag = False
    if "Destino Elegido:" in ai_response_text and "Intereses Clave en Destino:" in ai_response_text:
        if not search_query_for_tool: # Solo detectar resumen si NO hay una búsqueda pendiente
            summary_detected_flag = True
            print("[EXPLORADOR_INFO] Detectado formato de resumen final.")
        else:
            print("[EXPLORADOR_WARNING] Formato de resumen detectado, pero también búsqueda. Ignorando resumen.")
            
    if summary_detected_flag: # Si es un resumen, no debería haber búsqueda
        search_query_for_tool = None

    return {
        "messages": [AIMessage(content=ai_response_text)], # Solo la última respuesta de IA
        "summary_detected": summary_detected_flag,
        "search_query": search_query_for_tool,
        "search_results": None, # Limpiar resultados después de usarlos
        "has_searched_this_invoke": state.get("has_searched_this_invoke", False), # Se gestiona en web_search_node
        "last_executed_search_query": state.get("last_executed_search_query") # Se gestiona en web_search_node
    }

# --- WEB SEARCH NODE (sin cambios en su lógica interna, solo el print) ---
def web_search_node(state: TravelAgentState) -> dict:
    query_to_execute = state.get("search_query")
    if not query_to_execute:
        return {"search_results": "No se proporcionó una consulta de búsqueda.", "search_query": None, "has_searched_this_invoke": state.get("has_searched_this_invoke", False), "last_executed_search_query": state.get("last_executed_search_query")}
    print(f"[EXPLORADOR_INFO] Ejecutando búsqueda web para: '{query_to_execute}'")
    tavily_results_text = tavily_search(query_to_execute) # tavily_search ya tiene su print
    return {"search_results": tavily_results_text, "search_query": None, "has_searched_this_invoke": True, "last_executed_search_query": query_to_execute }

# --- EXTRACT DATA NODE (sin cambios en su lógica interna, solo prints) ---
def extract_data_node(state: TravelAgentState) -> dict:
    current_has_searched_flag = state.get("has_searched_this_invoke", False)
    current_last_executed_query = state.get("last_executed_search_query")
    current_extracted_data = state.get("extracted_data", {})
    final_answer_generated_flag = False

    if state["summary_detected"]:
        last_ai_message_content = ""
        # El estado 'messages' en este punto solo debería tener la última AIMessage del explorador_node
        if state["messages"] and isinstance(state["messages"][-1], AIMessage):
            last_ai_message_content = state["messages"][-1].content
        
        if not last_ai_message_content: print("[EXPLORADOR_ERROR] No se encontró mensaje de IA para extraer datos.")
        else:
            print("\n[EXPLORADOR_INFO] Resumen final detectado. Extrayendo...")
            extracted = extract_final_destination_info(last_ai_message_content)
            current_extracted_data = extracted
            destination_value = extracted.get("Destino Elegido", "").strip()
            invalid_destination_placeholders = ["", "aún por decidir", "un lugar cálido", "[destino específico elegido]", "destino específico elegido", "no especificados", "[ciudad específica elegida]"] 
            if destination_value and destination_value.lower() not in invalid_destination_placeholders:
                print("\n[EXPLORADOR_RESUMEN_FINAL] Extraído:")
                print(f"  - Destino Elegido: {extracted.get('Destino Elegido', '[vacío]')}")
                print(f"  - intereses: {extracted.get('intereses', '[vacío]')}")
                final_answer_generated_flag = True
            else:
                print(f"[EXPLORADOR_WARNING] 'Destino Elegido' ('{destination_value}') inválido en resumen.")
                state["summary_detected"] = False # Anular detección de resumen
    return {"extracted_data": current_extracted_data, "final_answer_generated": final_answer_generated_flag, "summary_detected": state["summary_detected"], "has_searched_this_invoke": current_has_searched_flag,  "last_executed_search_query": current_last_executed_query}

# --- SAVE DATA NODE (sin cambios en su lógica interna, solo prints) ---
def save_data_node(state: TravelAgentState) -> dict:
    if state["final_answer_generated"] and state["extracted_data"].get("Destino Elegido"):
        if save_to_json(state["extracted_data"]): print("[EXPLORADOR_INFO] Guardado JSON de resumen final exitoso.")
        else: print("[EXPLORADOR_ERROR] Fallo al guardar JSON el resumen final.")
    else: print("[EXPLORADOR_INFO] No se guardaron datos: no es respuesta final o Destino Elegido falta.")
    return {"has_searched_this_invoke": state.get("has_searched_this_invoke", False), "last_executed_search_query": state.get("last_executed_search_query")}

# --- CONDITIONAL EDGES (sin cambios en su lógica interna, solo prints) ---
def route_after_explorador(state: TravelAgentState) -> str:
    llm_requested_search = state.get("search_query")
    already_searched_this_invoke = state.get("has_searched_this_invoke", False)
    if state.get("summary_detected"):
        print("[EXPLORADOR_ROUTE] Explorador -> Extract Data (resumen final)")
        return "extract_data"
    if llm_requested_search and not already_searched_this_invoke:
        print("[EXPLORADOR_ROUTE] Explorador -> Perform Search")
        return "perform_search" # Nombre del nodo en el grafo
    if llm_requested_search and already_searched_this_invoke:
        print("[EXPLORADOR_ROUTE] Explorador -> END (ya se buscó en este invoke)")
    else:
        print("[EXPLORADOR_ROUTE] Explorador -> END (sin búsqueda o resumen)")
    return END

def route_after_extraction(state: TravelAgentState) -> str:
    if state.get("final_answer_generated") and state.get("extracted_data", {}).get("Destino Elegido"):
        print("[EXPLORADOR_ROUTE] Extract Data -> Save Data")
        return "save_data"
    print("[EXPLORADOR_ROUTE] Extract Data -> END (extracción fallida o no final)")
    return END


# --- Función de Inicialización para el Explorador ---
def initialize_destination_explorer():
    global _explorer_llm_model, _explorer_app
    if _explorer_app: # Prevenir reinicialización
        print("Explorador de Destinos ya inicializado.")
        return

    print("Inicializando Explorador de Destinos...")
    try:
        if not GOOGLE_API_KEY:
            print("Explorador de Destinos: GOOGLE_API_KEY no encontrado.")
            return
        genai.configure(api_key=GOOGLE_API_KEY)
        _explorer_llm_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", # O el modelo que uses
            safety_settings={'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE', 'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE', 'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE', 'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'},
            system_instruction=system_prompt_explorador # Prompt del sistema para el explorador
        )
        print("Explorador de Destinos: Modelo Gemini configurado.")
    except Exception as e:
        print(f"Explorador de Destinos: Error configurando Gemini - {e}")
        _explorer_llm_model = None # Asegurar que esté None si falla
        return # No continuar si el LLM falla

    # Construir el grafo del explorador
    workflow = StateGraph(TravelAgentState) # Usar el TravelAgentState del explorador
    workflow.add_node("explorador", explorador_node) # Tu explorador_node modificado
    workflow.add_node("web_search", web_search_node) # Tu web_search_node
    workflow.add_node("extract_data", extract_data_node) # Tu extract_data_node
    workflow.add_node("save_data", save_data_node) # Tu save_data_node
    
    workflow.set_entry_point("explorador")
    
    workflow.add_conditional_edges(
        "explorador", 
        route_after_explorador, # Tu función de enrutamiento
        {
            "perform_search": "web_search", 
            "extract_data": "extract_data", 
            END: END
        }
    )
    workflow.add_edge("web_search", "explorador") # El nodo de búsqueda vuelve al explorador
    workflow.add_conditional_edges(
        "extract_data", 
        route_after_extraction, # Tu función de enrutamiento
        {
            "save_data": "save_data", 
            END: END
        }
    )
    workflow.add_edge("save_data", END)

    _explorer_app = workflow.compile()
    print("Explorador de Destinos: Grafo LangGraph compilado y listo.")


# --- Herramienta para el Agente Principal ---
@tool
def destination_explorer_tool(user_input: str, current_explorer_state_messages: Optional[List[dict]] = None) -> dict:
    """
    Ayuda al usuario a elegir un destino de viaje (una CIUDAD específica).
    Utiliza esta herramienta cuando el usuario quiera explorar opciones de destino
    pero aún no tenga una ciudad en mente, o cuando necesite continuar una conversación
    previa con el explorador de destinos.
    Debes pasar la última entrada del usuario ('user_input').
    Si estás continuando una conversación, pasa el historial de mensajes del explorador
    como 'current_explorer_state_messages' (una lista de diccionarios {'role': ..., 'parts': ...}).
    La herramienta devolverá la respuesta del "Explorador de Destinos", su nuevo historial de mensajes
    para la siguiente llamada, y si la tarea de exploración ha finalizado.
    """
    if _explorer_app is None:
        initialize_destination_explorer() # Intenta inicializar si no lo está
        if _explorer_app is None:
            return {
                "explorer_response": "Error crítico: El Explorador de Destinos no pudo inicializarse.",
                "updated_explorer_messages_history": current_explorer_state_messages or [],
                "is_finished": True, # Marcar como terminado para evitar bucles
                "final_data": None
            }

    # Construir el estado inicial o continuado para el grafo del explorador
    messages_for_explorer_graph = []
    last_search_results_for_graph = None
    last_executed_query_for_graph = None
    
    if current_explorer_state_messages:
        # Reconstruir los mensajes BaseMessage y otros campos del estado a partir del historial
        for msg_dict in current_explorer_state_messages:
            if msg_dict.get("role") == "user_internal_context": # Manejar contexto especial de búsqueda
                # Asumimos que este contexto contiene search_results y last_executed_query
                last_search_results_for_graph = msg_dict.get("search_results_content")
                last_executed_query_for_graph = msg_dict.get("last_executed_query_content")
                # No lo añadimos directamente a messages_for_explorer_graph como mensaje visible al LLM
                # sino que se pasa al estado del grafo.
            elif msg_dict.get("role") == "user":
                messages_for_explorer_graph.append(HumanMessage(content=msg_dict["parts"][0]))
            elif msg_dict.get("role") == "model":
                 messages_for_explorer_graph.append(AIMessage(content=msg_dict["parts"][0]))
            # Los SystemMessage del prompt del explorador no se pasan aquí, se configuran en el modelo.

    # Añadir el input actual del usuario
    messages_for_explorer_graph.append(HumanMessage(content=user_input))

    state_for_invoke: TravelAgentState = {
        "messages": messages_for_explorer_graph,
        "user_input": user_input,
        "api_configured": True, # Asumir que las API Keys están
        "summary_detected": False,
        "extracted_data": {}, # Se determinará dentro del grafo
        "final_answer_generated": False, # Se determinará dentro del grafo
        "search_query": None, # El grafo lo determinará
        "search_results": last_search_results_for_graph, # Pasar resultados si los hubo
        "has_searched_this_invoke": False, # Se resetea para el nuevo invoke
        "last_executed_search_query": last_executed_query_for_graph
    }
    
    if not current_explorer_state_messages: # Primera llamada
        initial_ai_greeting = "¡Hola! Soy tu Explorador de Destinos 🧭. ¿Tienes ganas de viajar pero no sabes a qué CIUDAD? ¡Estás en el lugar correcto! Cuéntame un poco qué te apetece para tu escapada urbana: ¿cultura 🏛️, gastronomía 🍜, vida nocturna 🎉, relax en parques 🌳...? ¡Vamos a descubrir tu ciudad ideal juntos!"
        # Prepend el saludo del explorador para que el LLM lo vea en el primer turno REAL de usuario.
        # El estado messages ya tiene el HumanMessage, así que lo insertamos antes.
        state_for_invoke["messages"].insert(0, AIMessage(content=initial_ai_greeting))


    try:
        graph_output_state = _explorer_app.invoke(state_for_invoke)

        # La respuesta para el usuario es el último mensaje de IA del explorador
        explorer_response_to_user = ""
        if graph_output_state["messages"] and isinstance(graph_output_state["messages"][-1], AIMessage):
            explorer_response_to_user = graph_output_state["messages"][-1].content
        
        is_finished = graph_output_state.get("final_answer_generated", False) and \
                      graph_output_state.get("extracted_data", {}).get("Destino Elegido")
        
        final_data = None
        if is_finished:
            final_data = graph_output_state.get("extracted_data")
            print(f"[EXPLORER_TOOL] Tarea finalizada. Datos: {final_data}")
            # El guardado en JSON lo hace el save_data_node del explorador si se alcanza.

        # Preparar el historial de mensajes para la siguiente posible llamada a la herramienta
        # Esto debe capturar el estado de la conversación DENTRO del explorador.
        # Usamos el formato de historial de Gemini para simplicidad.
        updated_messages_history_for_next_call = []
        raw_messages_from_graph = graph_output_state.get("messages", [])

        # Reconstruimos el historial que el explorador ha acumulado en su estado 'messages'
        # y lo pasamos para la siguiente llamada.
        # Necesitamos reconstruir desde el graph_output_state['messages'] que es la
        # lista COMPLETA de mensajes que el explorador usó/generó.
        for msg in raw_messages_from_graph: # Estos son BaseMessage
            if isinstance(msg, HumanMessage):
                updated_messages_history_for_next_call.append({'role': 'user', 'parts': [msg.content]})
            elif isinstance(msg, AIMessage):
                updated_messages_history_for_next_call.append({'role': 'model', 'parts': [msg.content]})
        
        # Si hubo una búsqueda, necesitamos preservar sus resultados para el siguiente turno del explorador
        # dentro del historial que pasamos, de una manera que el explorador_node pueda usarlo.
        if graph_output_state.get("search_results") and graph_output_state.get("last_executed_search_query"):
            updated_messages_history_for_next_call.append({
                "role": "user_internal_context", # Rol especial para que no se muestre al LLM como mensaje directo
                "parts": ["Contexto de búsqueda anterior"], # Placeholder
                "search_results_content": graph_output_state.get("search_results"),
                "last_executed_search_query_content": graph_output_state.get("last_executed_search_query")
            })


        return {
            "explorer_response": explorer_response_to_user,
            "updated_explorer_messages_history": updated_messages_history_for_next_call,
            "is_finished": is_finished,
            "final_data": final_data
        }

    except Exception as e:
        import traceback
        print(f"[ERROR CRÍTICO DENTRO DE destination_explorer_tool] Error: {e}")
        traceback.print_exc()
        return {
            "explorer_response": "¡Vaya! El Explorador de Destinos tuvo un problema interno. Quizás necesitemos reiniciar la exploración.",
            "updated_explorer_messages_history": [], # Resetear historial en error crítico
            "is_finished": True, 
            "final_data": None
        }
