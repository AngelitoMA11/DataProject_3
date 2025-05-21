import os
import google.generativeai as genai
import json
import re
from typing import TypedDict, Annotated, List, Union, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
import uuid
import requests

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --- Helper Function: Tavily Search ---
def tavily_search(query: str) -> str:
    if not TAVILY_API_KEY or "YOUR_TAVILY_API_KEY" in TAVILY_API_KEY: # Añadida comprobación placeholder
        return "Error: Tavily API key no configurada o es un placeholder."
    try:
        print(f"[PLANNER_TOOL_CALL] Tavily search: \"{query}\"")
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "include_raw_content": False,
                "max_results": 5
            }
        )
        response.raise_for_status()
        results = response.json()
        
        output_parts = []
        if results.get("answer"):
            output_parts.append(f"Respuesta directa de Tavily: {results['answer']}")

        if results.get("results"):
            sources_info = []
            for r in results["results"]:
                sources_info.append(
                    f"- Título: {r.get('title', 'N/A')}\n  URL: {r.get('url', 'N/A')}\n  Contenido relevante: {r.get('content', 'No hay contenido adicional aquí.')[:500]}..."
                )
            if sources_info:
                output_parts.append("Fuentes y fragmentos relevantes:\n" + "\n".join(sources_info))
        
        if not output_parts:
            return "No se encontraron resultados directos o detallados en Tavily para esta consulta. Intenta reformular tu búsqueda."
        return "\n\n".join(output_parts)
    except requests.exceptions.HTTPError as e:
        return f"Error HTTP durante la búsqueda con Tavily: {e}. Respuesta: {e.response.text if e.response else 'N/A'}"
    except Exception as e:
        return f"Error durante la búsqueda con Tavily: {e}"

# --- LangGraph State Definition del Planificador (con búsqueda) ---
class ItineraryPlannerState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    user_input: str # El input original del usuario que disparó esta invocación de la herramienta
    # Campos para la búsqueda
    search_query: Optional[str] # Query que el LLM solicita buscar
    search_results: Optional[str] # Resultados de la búsqueda para pasar al LLM
    # last_executed_search_query es crucial para evitar bucles y para el contexto de los resultados
    last_executed_search_query: Optional[str]

# --- Variables Globales para el Grafo y Modelo del Planificador ---
_planner_llm_model = None
_planner_app = None

# --- Nodos del Grafo del Planificador ---
def planner_node(state: ItineraryPlannerState) -> dict:
    global _planner_llm_model
    if not _planner_llm_model:
        # Debería ser manejado por la inicialización, pero como fallback:
        return {"messages": [AIMessage(content="Error crítico: LLM del Planificador Preciso no inicializado.")]}

    current_messages_for_llm = list(state["messages"]) # Estos ya son BaseMessage
    last_executed_query_from_state = state.get("last_executed_search_query")
    search_results_from_state = state.get("search_results")

    # Si hay resultados de búsqueda *nuevos* (es decir, search_results está seteado en el estado actual),
    # los añadimos como un SystemMessage para el LLM.
    # Esto ocurre después de que el nodo de búsqueda haya puesto los resultados en el estado.
    if search_results_from_state:
        print(f"[PLANNER_DEBUG] Añadiendo resultados de búsqueda (para query: '{last_executed_query_from_state}') al contexto del LLM.")
        # Usamos un SystemMessage para pasar los resultados de búsqueda.
        # Asegúrate que este mensaje NO se acumule si no hay nuevos resultados.
        # El estado 'messages' ya acumula, así que solo añadimos si es relevante para este turno.
        current_messages_for_llm.append(
            SystemMessage(content=f"[Resultados de la búsqueda para \"{last_executed_query_from_state}\"]:\n{search_results_from_state}")
        )
    
    history_for_gemini = []
    for msg in current_messages_for_llm: # msg ya es BaseMessage
        if isinstance(msg, SystemMessage) and msg.content.strip() != system_prompt_planner.strip():
             # Este es para los resultados de búsqueda u otro contexto del sistema.
             # Gemini los prefiere como mensajes de 'user' con un prefijo.
             history_for_gemini.append({'role': 'user', 'parts': [f"[CONTEXTO ADICIONAL DEL SISTEMA]:\n{msg.content}"]})
        elif isinstance(msg, HumanMessage):
            history_for_gemini.append({'role': 'user', 'parts': [msg.content]})
        elif isinstance(msg, AIMessage):
            history_for_gemini.append({'role': 'model', 'parts': [msg.content]})
    
    ai_response_text = ""
    try:
        # Determinar el historial y el mensaje a enviar a Gemini
        if not history_for_gemini:
             # Caso muy raro: no hay historial y no hay mensaje de usuario (el estado messages estaba vacío)
             # Esto no debería pasar si el user_input siempre se añade al estado messages
             # Pero como fallback, usamos el user_input original de la herramienta.
             chat_session = _planner_llm_model.start_chat(history=[])
             message_to_send_gemini = [state.get("user_input", "Hola, por favor ayúdame a planificar.")]
             print(f"[PLANNER_DEBUG] Enviando a Gemini (sin historial previo, usando user_input): {str(message_to_send_gemini)[:300]}...")
        elif len(history_for_gemini) == 1 and history_for_gemini[0]['role'] == 'user':
            # Solo hay un mensaje de usuario (probablemente el inicial o el de contexto de búsqueda)
            chat_session = _planner_llm_model.start_chat(history=[])
            message_to_send_gemini = history_for_gemini[0]['parts']
            print(f"[PLANNER_DEBUG] Enviando a Gemini (un solo mensaje de usuario en historial): {str(message_to_send_gemini)[:300]}...")
        else:
            # Hay historial, enviar el último mensaje y el resto como historial
            chat_session = _planner_llm_model.start_chat(history=history_for_gemini[:-1])
            message_to_send_gemini = history_for_gemini[-1]['parts']
            print(f"[PLANNER_DEBUG] Enviando a Gemini (historial: {len(history_for_gemini)-1} mensajes, último mensaje): {str(message_to_send_gemini)[:300]}...")

        response = chat_session.send_message(message_to_send_gemini)
        ai_response_text = response.text
        print(f"[PLANNER_DEBUG] Respuesta de Gemini: {ai_response_text[:300]}...")

    except Exception as e:
        print(f"Planificador Preciso: Error generando respuesta de Gemini: {e}")
        ai_response_text = "Uff, parece que mis mapas se mezclaron un poco. ¿Podrías repetirme eso o la información anterior?"

    # Detectar solicitud de búsqueda del LLM
    search_request_match = re.search(r'\[BUSCAR_INFO:\s*\"(.*?)\"\]', ai_response_text)
    next_search_query_for_tool_node = None
    
    if search_request_match:
        potential_query = search_request_match.group(1).strip()
        # Evitar búsqueda redundante SI esta misma query fue la ÚLTIMA EJECUTADA Y YA TENEMOS RESULTADOS PARA ELLA
        # (lo que significa que el LLM está pidiendo lo mismo inmediatamente después de recibir resultados para ello)
        if search_results_from_state and last_executed_query_from_state and potential_query.lower() == last_executed_query_from_state.lower():
            print(f"[PLANNER_INFO] LLM intentó búsqueda redundante para '{potential_query}' (ya teníamos resultados recientes para ella). Se eliminará de la respuesta y se le pedirá que use la info.")
            ai_response_text = ai_response_text.replace(search_request_match.group(0), "").strip()
            if not ai_response_text.strip(): # Si la respuesta del LLM era SOLO la búsqueda
                ai_response_text = "Ya tengo información sobre eso de una búsqueda anterior. ¿Cómo quieres que la utilice para tu itinerario o qué más necesitas saber?"
        else:
            next_search_query_for_tool_node = potential_query
            print(f"[PLANNER_INFO] LLM solicitó nueva búsqueda: '{next_search_query_for_tool_node}'")
            # Si se va a realizar una búsqueda. El flujo continuará y la siguiente respuesta del LLM
            # Limpiamos la etiqueta de la respuesta actual por si acaso, aunque idealmente esta respuesta no llega al usuario si se busca.
            ai_response_text_for_message = ai_response_text.replace(search_request_match.group(0), "").strip()
            if not ai_response_text_for_message: # Si la respuesta era SOLO la búsqueda.
                 ai_response_text_for_message = f"Entendido, voy a buscar información sobre: \"{next_search_query_for_tool_node}\"."
            # La AIMessage que se añade al historial SÍ debe reflejar lo que el LLM dijo,
            # incluyendo la solicitud de búsqueda, para que el historial sea coherente.
            # Pero la 'planner_response' que se devuelve al final de la herramienta, si la tarea no ha terminado y
            # se ha hecho una búsqueda, suele ser un mensaje de transición o la propia respuesta del LLM sin la etiqueta.

    # La AIMessage que se añade al estado 'messages' SÍ debe tener el texto original del LLM.
    # La limpieza de [BUSCAR_INFO] para el usuario final se hace al salir de la herramienta.
    return {
        "messages": [AIMessage(content=ai_response_text)], # Acumula el mensaje del LLM
        "search_query": next_search_query_for_tool_node, # Para el nodo de enrutamiento/búsqueda
        "search_results": None, # Limpiar resultados después de que el LLM los haya "visto" (se usaron para current_messages_for_llm)
        # last_executed_search_query se mantiene del estado o se actualiza en el nodo de búsqueda
    }

def web_search_node_planner(state: ItineraryPlannerState) -> dict:
    query_to_execute = state.get("search_query") # Esto viene de la salida de planner_node
    if not query_to_execute:
        # Esto no debería ocurrir si el enrutamiento es correcto
        print("[PLANNER_WARNING] Nodo de búsqueda llamado sin query_to_execute.")
        return {
            "search_results": "Error interno: No se proporcionó una consulta de búsqueda al nodo de búsqueda.",
            "search_query": None,
            "last_executed_search_query": state.get("last_executed_search_query")
        }

    print(f"[PLANNER_INFO] Ejecutando búsqueda web para: '{query_to_execute}'")
    tavily_results_text = tavily_search(query_to_execute)
    
    return {
        # search_query se limpia porque ya se ejecutó.
        "search_query": None,
        "search_results": tavily_results_text,
        "last_executed_search_query": query_to_execute
    }

# --- Conditional Edges para el Planificador ---
def route_after_planner(state: ItineraryPlannerState) -> str:
    # El search_query en el estado es el que el planner_node PUEDE haber establecido.
    if state.get("search_query"):
        print("[PLANNER_ROUTE] Planner -> Perform Search")
        return "perform_search_planner"
    
    # Si no hay search_query, el LLM no pidió buscar (o la búsqueda redundante se evitó y se limpió la query).
    print("[PLANNER_ROUTE] Planner -> END (sin búsqueda solicitada o búsqueda redundante evitada)")
    return END

# --- System Prompt del Planificador Preciso (Revisado) ---
system_prompt_planner = """
ROL Y OBJETIVO PRIMARIO:
Eres "Planificador Preciso", un asistente experto dedicado exclusivamente a la creación de itinerarios de viaje detallados y prácticos. Tu misión es tomar un destino, fechas, número de viajeros e intereses proporcionados y transformarlos en un plan día por día, actividad por actividad. La característica más importante de tus respuestas es que TODA la información factual (horarios, precios estimados, ubicaciones, tiempos de traslado, popularidad) DEBE estar fundamentada en el conocimiento accesible a través de una búsqueda (simulando el uso de Google Search, Maps, guías de viaje online, etc.). Actúa como si hubieras consultado estas fuentes recientemente para cada elemento del itinerario. NO ayudas a elegir el destino; asumes que ya está decidido y se te ha proporcionado.

CAPACIDAD DE BÚSQUEDA DE INFORMACIÓN ACTUALIZADA: Recuerda que la fecha actual para tus consultas es 21 de mayo de 2025.
Si necesitas información muy específica que podría haber cambiado recientemente (horarios exactos de un evento particular, disponibilidad de tours especiales) o para descubrir eventos locales (festivales, conciertos, mercados especiales) que ocurran DURANTE LAS FECHAS DEL VIAJE del usuario, **debes solicitar una búsqueda**.
Para hacerlo, en tu respuesta, incluye la frase [BUSCAR_INFO: "término de búsqueda específico aquí"].
Siempre que dudes de algo o creas que la búsqueda puede aportar valor significativo, **incluye esta solicitud**.
Por ejemplo:
- [BUSCAR_INFO: "eventos culturales en Roma del 10 al 15 de julio 2025"]
- [BUSCAR_INFO: "horario de apertura Museo del Prado Madrid tercera semana de agosto 2025"]
- [BUSCAR_INFO: "mejores mercados callejeros en Bangkok fines de semana de septiembre 2025"]
Yo (el sistema) realizaré la búsqueda y te proporcionaré los resultados (precedidos por "[Resultados de la búsqueda para...]") para que los integres en el itinerario. **Utiliza esta herramienta cuando creas que puede aportar valor significativo con información actualizada o muy específica que no conocerías de forma general.**

**MUY IMPORTANTE - GESTIÓN DE RESULTADOS DE BÚSQUEDA:**
1.  Cuando YO (el sistema) te proporcione resultados de una búsqueda, tu SIGUIENTE RESPUESTA DEBE enfocarse en UTILIZAR Y PRESENTAR esos resultados al usuario para enriquecer el itinerario. Integra la información de forma natural.
2.  NO DEBES REPETIR la misma solicitud [BUSCAR_INFO: ...] en la respuesta inmediata después de recibir los resultados para esa misma consulta. Asume que ya tienes la información de esa búsqueda específica.
3.  Si los resultados que te proporcioné no son suficientes, no son lo que esperabas, o necesitas más detalles:
    a. Explica brevemente al usuario la situación (ej: "La búsqueda anterior no arrojó detalles sobre X, pero encontré Y...").
    b. Si puedes, formula una solicitud [BUSCAR_INFO: ...] *diferente* y más específica.
    c. O bien, pide al usuario que aclare o proporcione más contexto si eso ayudaría.
    d. Si después de una o dos búsquedas la información sigue siendo esquiva, informa al usuario de las limitaciones y procede con la mejor información disponible, indicando incertidumbres.

PROCESO DE INTERACCIÓN Y RECOPILACIÓN DE INFORMACIÓN:
1.  **Saludo Inicial:** Saluda brevemente y confirma tu rol ("¡Hola! Soy Planificador Preciso...").
2.  **Verificación de Datos Esenciales:**
    *   Revisa el mensaje actual del usuario y el historial de conversación. **Si el destino, fechas (o duración), número de viajeros e intereses principales ya han sido claramente establecidos (ya sea en el mensaje actual o previamente), úsalos directamente.**
    *   **Si falta alguno de estos datos cruciales, pídelos inmediatamente y de forma concisa.** Ejemplo: "Para empezar, necesito saber: destino, fechas exactas, número de viajeros e intereses principales para este viaje."
3.  **Información Adicional (Opcional, pero útil):** Una vez tengas lo esencial, puedes preguntar brevemente por:
    *   Presupuesto general para actividades/comidas (ej: económico, medio, lujo).
    *   Ritmo de viaje deseado (ej: relajado, moderado, intenso).
    *   Preferencias de transporte DENTRO del destino.
    *   Puedes hacer estas preguntas de forma agrupada para ser eficiente.
4.  **Clarificación:** Si la información sigue siendo ambigua (ej: "Europa" en lugar de una ciudad), pide la ciudad o región específica.

GENERACIÓN DEL ITINERARIO DETALLADO:
(El resto del prompt para GENERACIÓN, DIRECTRICES DE GROUNDING, TONO Y ESTILO, QUÉ EVITAR, y SEÑAL DE FINALIZACIÓN puede permanecer como lo tenías, ya que es bastante bueno. Solo asegúrate que las frases de grounding reflejen la fecha de "mayo 2025" cuando sea apropiado).
Estructura Obligatoria:
- Presenta el itinerario día por día (ej: "Día 1: [Fecha o Llegada] - [Ciudad]").
- Para cada día, divide las sugerencias en bloques cronológicos (Mañana, Tarde, Noche) o por actividades principales.

Contenido Detallado por Actividad/Sugerencia:
- **Nombre del Lugar/Actividad:** Claro y preciso.
- **Breve Descripción:** ¿Qué se hará/verá? ¿Por qué es relevante para los intereses del usuario?
- **Información Práctica Esencial (Fundamentada):**
    - Ubicación/Dirección: Lo más exacta posible.
    - Horarios de Apertura/Funcionamiento: Menciona "Según información consultada online (mayo 2025)..." o "Generalmente abre de X a Y". Si es crucial y podría variar, considera [BUSCAR_INFO: ...].
    - Precio Estimado de Entrada/Actividad: Indica si es gratuito o el rango de precios (ej: "aprox. €15-€20").
    - Duración Estimada de la Visita/Actividad.
    - Cómo Llegar (opcional, pero útil si implica un traslado significativo desde la actividad anterior o el centro).
- **Consejo Práctico:** (ej: "Compra entradas online para evitar colas", "Mejor ir temprano").
- **Opciones de Comida Cercanas (opcional):** Sugerencias breves si es relevante (ej: "Hay varios cafés cerca para almorzar").
- **Logística Diaria:** Considera tiempos de traslado realistas, agrupa actividades geográficamente para minimizar desplazamientos.
- **Flexibilidad:** Incluye "opción alternativa" o "tiempo libre" donde sea apropiado. No satures los días.

DIRECTRICES DE "FUNDAMENTACIÓN EN BÚSQUEDA" (Grounding):
- **Precisión de Datos:** Esfuérzate por que los horarios, precios y direcciones sean actuales (considerando que "hoy" es mayo de 2025). Si no estás seguro de algo muy específico o variable, usa [BUSCAR_INFO: ...].
- **Verificabilidad Implícita:** Tus sugerencias y datos prácticos deben sonar como si provinieran de una consulta reciente a fuentes fiables.
- **Uso de Frases de Grounding:**
    - "Consultando información online reciente (mayo 2025), el [Lugar] suele abrir de..."
    - "Las guías de viaje sugieren que es mejor visitar [Lugar] por la [mañana/tarde] para..."
    - "Para confirmar eventos específicos durante tus fechas, podría ser útil una búsqueda. ¿Quieres que intente encontrar [BUSCAR_INFO: 'eventos en [ciudad] del [fecha_inicio] al [fecha_fin] 2025']?"

TONO Y ESTILO:
- Profesional, eficiente, amigable, claro y muy organizado.
- Utiliza listas con viñetas o numeradas para facilitar la lectura. Lenguaje preciso.

QUÉ EVITAR ESTRICTAMENTE:
- Ayudar a elegir el destino o las fechas iniciales (puedes ayudar a ajustar fechas si una búsqueda revela un evento interesante en días adyacentes, pero la elección inicial es del usuario y se te debe proporcionar).
- Sugerir opciones de alojamiento o vuelos (salvo logística muy general de llegada/salida relacionada con el primer/último día del itinerario).
- Inventar información. Si no sabes algo y no puedes buscarlo, indícalo.
- Itinerarios demasiado ambiciosos o irrealizables en el tiempo asignado.

**SEÑAL DE FINALIZACIÓN DEL ITINERARIO:**
Cuando consideres que has proporcionado un itinerario completo y detallado que responde a la solicitud del usuario (cubriendo todos los días del viaje), y no necesitas más información o búsquedas para mejorarlo (a menos que el usuario pida cambios), INCLUYE la etiqueta `[ITINERARIO_COMPLETO]` al final de tu respuesta.
Ejemplo: "...y eso concluye las sugerencias para tu viaje. ¡Espero que este itinerario te sea de gran utilidad! [ITINERARIO_COMPLETO]"
Ten en cuenta que el 22 de mayo de 2025 hay un evento de Google en el IFEMA, Madrid
"""


# --- Función de Inicialización para el Planificador ---
def initialize_itinerary_planner():
    global _planner_llm_model, _planner_app
    if _planner_app:
        print("Planificador Preciso ya inicializado.")
        return

    print("Inicializando Planificador Preciso...")
    if not TAVILY_API_KEY or "YOUR_TAVILY_API_KEY" in TAVILY_API_KEY:
        print("ADVERTENCIA: TAVILY_API_KEY no está configurada correctamente. La capacidad de búsqueda del Planificador no funcionará.")
    
    try:
        if not GOOGLE_API_KEY or "YOUR_GOOGLE_API_KEY" in GOOGLE_API_KEY:
            print("Planificador Preciso: GOOGLE_API_KEY no configurado o es un placeholder.")
            _planner_llm_model = None # Asegurar que no se use un modelo no inicializado
            return
        genai.configure(api_key=GOOGLE_API_KEY)
        _planner_llm_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-preview-05-20",
            safety_settings={'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE', 'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE', 'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE', 'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'},
            system_instruction=system_prompt_planner
        )
        print("Planificador Preciso: Modelo Gemini configurado.")
    except Exception as e:
        print(f"Planificador Preciso: Error configurando Gemini - {e}")
        _planner_llm_model = None
        return

    workflow = StateGraph(ItineraryPlannerState)
    workflow.add_node("planner_agent", planner_node)
    workflow.add_node("web_search_planner", web_search_node_planner) # Renombrado para claridad
    
    workflow.set_entry_point("planner_agent")
    
    workflow.add_conditional_edges(
        "planner_agent",
        route_after_planner,
        {
            "perform_search_planner": "web_search_planner",
            END: END
        }
    )
    workflow.add_edge("web_search_planner", "planner_agent") # El nodo de búsqueda vuelve al planificador

    _planner_app = workflow.compile()
    print("Planificador Preciso: Grafo LangGraph compilado y listo.")


# --- Herramienta para el Agente Principal ---
@tool
def itinerary_planner_tool(user_input: str, current_planner_state_messages: Optional[List[dict]] = None) -> dict:
    """
    Ayuda al usuario a crear un itinerario de viaje para un destino y fechas ya decididos.
    Puede buscar información actualizada sobre eventos o detalles específicos si es necesario.
    Debes pasar la última entrada del usuario ('user_input').
    Si estás continuando una conversación con el planificador, pasa su historial de mensajes previo
    como 'current_planner_state_messages' (una lista de diccionarios con formato {'role': ..., 'parts': [{'text': ...}]}).
    La herramienta devolverá la respuesta del "Planificador Preciso", su nuevo historial de mensajes para la siguiente llamada,
    y un indicador de si la tarea de planificación ha finalizado.
    Utiliza esta herramienta para crear itinerarios cuando hayas recabado suficiente información del usuario.
    """
    if _planner_app is None or _planner_llm_model is None: # Comprobar también el modelo
        initialize_itinerary_planner()
        if _planner_app is None or _planner_llm_model is None:
            return {
                "planner_response": "Error crítico: El Planificador Preciso no pudo inicializarse correctamente.",
                "updated_planner_messages_history": current_planner_state_messages or [],
                "is_finished": True,
                "itinerary_text": None
            }

    # --- Construcción del estado inicial para el grafo ---
    messages_for_graph_state: List[BaseMessage] = []
    initial_search_results_for_graph_state: Optional[str] = None
    initial_last_executed_query_for_graph_state: Optional[str] = None
    
    if current_planner_state_messages:
        for msg_dict in current_planner_state_messages:
            role = msg_dict.get("role")
            parts = msg_dict.get("parts")

            # Asegurarse que 'parts' es una lista y tiene al menos un elemento con 'text'
            content_text = None
            if isinstance(parts, list) and parts and isinstance(parts[0], dict) and "text" in parts[0]:
                content_text = parts[0]["text"]
            elif isinstance(parts, str):
                content_text = parts

            if content_text is None and role != "user_internal_context":
                print(f"[PLANNER_TOOL_WARN] Mensaje en historial con formato inesperado o sin contenido: {msg_dict}")
                continue

            if role == "user":
                messages_for_graph_state.append(HumanMessage(content=content_text))
            elif role == "model":
                messages_for_graph_state.append(AIMessage(content=content_text))
            elif role == "user_internal_context":
                initial_search_results_for_graph_state = msg_dict.get("search_results_content")
                initial_last_executed_query_for_graph_state = msg_dict.get("last_executed_query_content")
                print(f"[PLANNER_TOOL_DEBUG] Cargando contexto de búsqueda previo: query='{initial_last_executed_query_for_graph_state}'")

    # Añadir el user_input actual como HumanMessage si no es una repetición del último mensaje humano en el historial.
    # Esto es importante para el flujo dentro del grafo LangGraph.
    if not messages_for_graph_state or \
       not isinstance(messages_for_graph_state[-1], HumanMessage) or \
       messages_for_graph_state[-1].content != user_input:
        messages_for_graph_state.append(HumanMessage(content=user_input))
    
    # El estado que se pasa a app.invoke()
    current_graph_input_state: ItineraryPlannerState = {
        "messages": messages_for_graph_state,
        "user_input": user_input,
        "search_query": None,
        "search_results": initial_search_results_for_graph_state,
        "last_executed_search_query": initial_last_executed_query_for_graph_state
    }
    
    try:
        # Invocamos el grafo LangGraph
        final_graph_output_state = _planner_app.invoke(current_graph_input_state)

        # La respuesta final del LLM al usuario está en el último AIMessage
        planner_response_to_user = ""
        if final_graph_output_state["messages"] and isinstance(final_graph_output_state["messages"][-1], AIMessage):
            planner_response_to_user = final_graph_output_state["messages"][-1].content
        
        # Limpiar etiquetas de la respuesta que va al usuario
        planner_response_to_user_cleaned = re.sub(r'\[BUSCAR_INFO:\s*\"(.*?)\"\]', '', planner_response_to_user).strip()
        
        is_task_finished = False
        completion_tag = "[ITINERARIO_COMPLETO]"
        if completion_tag in planner_response_to_user_cleaned:
            is_task_finished = True
            planner_response_to_user_cleaned = planner_response_to_user_cleaned.replace(completion_tag, "").strip()
            print("[PLANNER_INFO] El planificador ha señalado la finalización del itinerario.")

        # Construir el historial para la *siguiente* posible llamada a esta herramienta
        updated_messages_history_for_next_tool_call: List[dict] = []
        for msg in final_graph_output_state.get("messages", []):
            msg_content_cleaned_for_history = msg.content
            # Limpiar etiquetas también del historial para no confundir al LLM en futuras vueltas si se re-procesa.
            msg_content_cleaned_for_history = re.sub(r'\[BUSCAR_INFO:\s*\"(.*?)\"\]', '', msg_content_cleaned_for_history).strip()
            if completion_tag in msg_content_cleaned_for_history:
                 msg_content_cleaned_for_history = msg_content_cleaned_for_history.replace(completion_tag, "").strip()

            if isinstance(msg, HumanMessage):
                updated_messages_history_for_next_tool_call.append({'role': 'user', 'parts': [{'text': msg_content_cleaned_for_history}]})
            elif isinstance(msg, AIMessage):
                updated_messages_history_for_next_tool_call.append({'role': 'model', 'parts': [{'text': msg_content_cleaned_for_history}]})
        
        # Si la última operación del grafo fue una búsqueda Y el LLM NO pidió otra búsqueda después
        # (es decir, search_query está vacío en final_graph_output_state),
        # entonces los search_results y last_executed_search_query son relevantes para el *siguiente* turno.
        # Guardamos estos en el formato 'user_internal_context' para la próxima llamada a la herramienta.
        if final_graph_output_state.get("search_results") and \
           final_graph_output_state.get("last_executed_search_query") and \
           not final_graph_output_state.get("search_query"):
            updated_messages_history_for_next_tool_call.append({
                "role": "user_internal_context",
                "parts": [{"text": "Contexto de la última búsqueda realizada y sus resultados."}],
                "search_results_content": final_graph_output_state.get("search_results"),
                "last_executed_search_query_content": final_graph_output_state.get("last_executed_search_query")
            })
            print(f"[PLANNER_TOOL_DEBUG] Guardando contexto de búsqueda para próxima llamada: query='{final_graph_output_state.get('last_executed_search_query')}'")
        
        final_itinerary_text = None
        if is_task_finished: # Si está terminado, la respuesta del planificador es el itinerario.
            final_itinerary_text = planner_response_to_user_cleaned
        # Opcionalmente, podrías intentar extraer un "itinerario parcial" si no ha terminado,
        # pero esto puede ser complejo y depende de cómo estructura el LLM sus respuestas intermedias.
        # Por ahora, solo devolvemos el itinerario completo cuando está finalizado.

        return {
            "planner_response": planner_response_to_user_cleaned,
            "updated_planner_messages_history": updated_messages_history_for_next_tool_call,
            "is_finished": is_task_finished,
            "itinerary_text": final_itinerary_text
        }

    except Exception as e:
        import traceback
        print(f"[ERROR CRÍTICO DENTRO DE itinerary_planner_tool] Error: {e}")
        traceback.print_exc()
        return {
            "planner_response": "¡Vaya! El Planificador Preciso tuvo un problema interno inesperado. Quizás necesitemos reiniciar la planificación.",
            "updated_planner_messages_history": current_planner_state_messages or [],
            "is_finished": True,
            "itinerary_text": None
        }