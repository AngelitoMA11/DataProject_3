import os
# import google.generativeai as genai
import json
import re
from typing import TypedDict, Annotated, List, Union, Type, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field # Asegúrate de tener pydantic instalado
import uuid

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# Para pruebas, puedes hardcodearla, pero es mejor usar variables de entorno
API_KEY_TO_USE = os.getenv("TRAVEL_AGENT_API_KEY", GOOGLE_API_KEY if GOOGLE_API_KEY else "YOUR_FALLBACK_API_KEY")
if API_KEY_TO_USE == "YOUR_FALLBACK_API_KEY" or not API_KEY_TO_USE: # Verificación más estricta
    print("ADVERTENCIA: API Key para TravelAgent no configurada o es un placeholder.")
    print("Por favor, configura GOOGLE_API_KEY o TRAVEL_AGENT_API_KEY en tu .env o como variable de entorno.")
    # Podrías decidir salir aquí si la API key es esencial para la prueba.
    # exit()


# --- System Prompt ---
SYSTEM_PROMPT_EXPLORADOR = """
## Rol y Objetivo Primario
Eres el "Explorador de Destinos", un asistente de viajes experto, amigable y muy perspicaz. Tu objetivo principal es ayudar a los usuarios a descubrir y elegir un **destino de viaje ideal y específico (una ciudad, país o región concreta)** basado en sus preferencias, intereses y necesidades. Una vez que este destino esté CLARAMENTE DEFINIDO, debes recopilar toda la información necesaria para planificar su viaje.
## Tono y Estilo de Comunicación
- Cercano y conversacional, como un amigo entusiasta que adora viajar.
- Evita lenguaje corporativo o respuestas genéricas.
- Utiliza emoji ocasionalmente para dar vida a la conversación 🌴✈️🏞️.
- Personalidad cálida pero profesional, transmitiendo pasión por los viajes.
- Ocasionalmente comparte pequeñas anécdotas o datos curiosos sobre destinos.
## Proceso de Interacción y Recopilación de Información
**Fase 1: Definición Obligatoria del Destino**
1.  Tu **PRIMERA Y MÁS IMPORTANTE TAREA** es ayudar al usuario a elegir un **destino específico**. Haz preguntas sobre sus intereses, tipo de viaje deseado (playa, montaña, ciudad, aventura, relax, cultura, etc.), presupuesto general inicial (si lo mencionan espontáneamente, si no, no es prioritario en esta fase), y cualquier otra preferencia que ayude a concretar un LUGAR.
2.  **NO avances a la Fase 2** ni intentes recopilar otros datos (origen, fechas, etc.) hasta que el usuario haya confirmado un destino concreto (e.g., "París, Francia", "Kyoto, Japón", "la costa Amalfitana, Italia", "Tailandia").
3.  Si el usuario da respuestas vagas sobre el destino, sigue preguntando y ofreciendo sugerencias hasta que se decida por un lugar específico. Por ejemplo, si dice "algo con playa", pregunta "¿Prefieres Caribe, Mediterráneo, Sudeste Asiático, o tienes alguna idea más concreta?".
4.  El objetivo de esta fase es que el campo "Destino" del resumen final sea un nombre de lugar geográfico real y no frases como "aún por decidir" o "un lugar cálido".
**Fase 2: Recopilación de Detalles del Viaje (SOLO DESPUÉS DE ELEGIR DESTINO)**
Una vez que el usuario haya elegido un **destino específico y confirmado**, y SOLO ENTONCES, recopila la siguiente información adicional (si no la has obtenido ya):
- Ciudad de origen (de dónde sale el viajero)
- Fechas de viaje (salida y regreso) TEN EN CUENTA QUE ESTAMOS EN mayo de 2025 por tanto las fechas deben ser válidas y futuras.
- Número de viajeros
- Presupuesto aproximado
- Principales intereses EN EL DESTINO ESPECÍFICO YA ELEGIDO
- Correo electrónico de contacto
- Número de teléfono
- Si solo visitará una ciudad o varias (dentro del destino general si es un país/región, o si el destino es una ciudad, si hará excursiones a otras)
## Finalización de la Conversación
1.  **NO finalices la conversación NI generes el resumen** hasta haber recopilado TODA la información listada en la Fase 2, y MUY ESPECIALMENTE, hasta que el campo "Destino" contenga un lugar geográfico concreto y confirmado por el usuario.
2.  Cuando hayas recopilado TODA la información necesaria, incluyendo un **destino específico y válido**, resume los datos y finaliza la conversación de manera formal.
3.  Al finalizar, SIEMPRE incluye un resumen COMPLETO con EXACTAMENTE este formato (en líneas separadas):
    ```
    Origen: [ciudad de origen]
    Destino: [DESTINO ESPECÍFICO ELEGIDO]
    Fecha de salida: [fecha de salida]
    Fecha de regreso: [fecha de regreso]
    Viajeros: [número]
    Presupuesto: [presupuesto]
    Intereses: [intereses principales EN EL DESTINO]
    Correo: [correo electrónico]
    Teléfono: [teléfono]
    ¿Solo una ciudad?: [sí/no]
    ```
4. Es CRUCIAL que incluyas TODOS estos campos al final, y que el campo "Destino" NUNCA esté vacío o sea una frase genérica. Debe ser un lugar.
## Restricciones Clave
-   **Prioridad Absoluta al Destino:** La elección de un destino específico es el paso MÁS CRÍTICO antes de cualquier otra cosa. No te desvíes.
-   **NO generar resumen sin destino:** Bajo NINGUNA circunstancia generes el resumen final si el campo "Destino" no es un lugar geográfico concreto. Si el usuario intenta finalizar antes, recuérdale amablemente que aún falta definir el destino.
-   **Recopilación Completa:** Asegúrate de obtener TODOS los datos de la Fase 2 antes de finalizar.
-   **Formato del Resumen Final:** El resumen final DEBE seguir el formato especificado con exactitud.
"""

# # --- LangGraph State Definition for TravelAgentLangGraph ---
# class TravelAgentState(TypedDict):
#     messages: Annotated[List[BaseMessage], lambda x, y: x + y]
#     user_input: str
#     api_configured: bool
#     summary_detected: bool
#     extracted_data: dict
#     final_answer_generated: bool

# # --- Travel Agent Class (Sub-Agent Logic) ---
# class TravelAgentLangGraph:
#     INITIAL_GREETING = "¡Hola! Soy tu Explorador de Destinos 🧭. ¿Tienes ganas de viajar pero no sabes dónde? ¡Estás en el lugar correcto! Cuéntame un poco qué te apetece: ¿relax total 🏖️, aventura pura 🧗‍♀️, sumergirte en otra cultura 🏛️, probar sabores nuevos 🍜...? ¡Vamos a descubrirlo juntos!"

#     def __init__(self, api_key: str, system_prompt: str, session_id: str = "default_travel_session"):
#         self.api_key = api_key
#         self.system_prompt = system_prompt
#         self.session_id = session_id
#         self.llm_model = None
#         self.app = None
#         self.current_state: TravelAgentState = self._get_initial_state()

#         self._initialize_llm() # Esto puede lanzar una excepción si falla
#         self._build_graph()
#         print(f"[TravelAgent {self.session_id}] Initialized and graph built.")

#     def _get_initial_state(self) -> TravelAgentState:
#         return {
#             "messages": [AIMessage(content=self.INITIAL_GREETING)],
#             "user_input": "",
#             "api_configured": False,
#             "summary_detected": False,
#             "extracted_data": {},
#             "final_answer_generated": False
#         }

#     def reset_state(self):
#         print(f"[TravelAgent {self.session_id}] Resetting state.")
#         self.current_state = self._get_initial_state()

#     def _initialize_llm(self):
#         if not self.api_key or self.api_key == "YOUR_FALLBACK_API_KEY":
#             self.current_state["api_configured"] = False
#             raise ValueError(f"[TravelAgent {self.session_id} ERROR] API Key not provided or is a placeholder.")
#         try:
#             genai.configure(api_key=self.api_key)
#             self.llm_model = genai.GenerativeModel(
#                 model_name="gemini-1.5-flash",
#                 safety_settings={
#                     'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
#                     'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
#                     'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
#                     'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
#                 },
#                 system_instruction=self.system_prompt
#             )
#             self.current_state["api_configured"] = True
#         except Exception as e:
#             self.llm_model = None
#             self.current_state["api_configured"] = False
#             raise ConnectionError(f"[TravelAgent {self.session_id} ERROR] Error configuring Gemini API or Model: {e}") from e

#     @staticmethod
#     def _extract_travel_info(text: str) -> dict:
#         data = {
#             "origin": "", "destination": "", "departure_date": "", "arrival_date": "",
#             "viajeros": "", "presupuesto": "", "intereses": "", "correo": "",
#             "telefono": "", "sola_ciudad": ""
#         }
#         patterns = {
#             "origin": r"Origen:\s*(.+?)(?:\n|$)", "destination": r"Destino:\s*(.+?)(?:\n|$)",
#             "departure_date": r"Fecha de salida:\s*(.+?)(?:\n|$)", "arrival_date": r"Fecha de regreso:\s*(.+?)(?:\n|$)",
#             "viajeros": r"Viajeros:\s*(.+?)(?:\n|$)", "presupuesto": r"Presupuesto:\s*(.+?)(?:\n|$)",
#             "intereses": r"Intereses:\s*(.+?)(?:\n|$)", "correo": r"Correo:\s*(.+?)(?:\n|$)",
#             "telefono": r"Teléfono:\s*(.+?)(?:\n|$)", "sola_ciudad": r"¿Solo una ciudad\??:\s*(.+?)(?:\n|$)"
#         }
#         for field, pattern in patterns.items():
#             match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
#             if match: data[field] = match.group(1).strip()
#         return data

#     @staticmethod
#     def _save_to_json(data: dict, filename_prefix="travel_data_langgraph"):
#         filename = f"{filename_prefix}_{data.get('session_id', 'unknown_session')}.json"
#         try:
#             with open(filename, "w", encoding="utf-8") as f:
#                 json.dump(data, f, indent=4, ensure_ascii=False)
#             print(f"\n[TravelAgent INFO] Datos del viaje guardados en '{filename}'")
#             return True
#         except Exception as e:
#             print(f"\n[TravelAgent ERROR] No se pudo guardar en JSON: {e}")
#             return False

#     def explorador_node(self, state: TravelAgentState) -> dict:
#         if not self.llm_model: return {"messages": [AIMessage(content="Error: LLM no inicializado en TravelAgent.")]}
#         current_messages = state["messages"]
#         history_for_gemini = [{'role': 'user' if isinstance(m, HumanMessage) else 'model', 'parts': [m.content]}
#                               for m in current_messages if not isinstance(m, SystemMessage)]
#         try:
#             chat_session = self.llm_model.start_chat(history=history_for_gemini[:-1] if len(history_for_gemini) > 1 else [])
#             response = chat_session.send_message(history_for_gemini[-1]['parts'] if history_for_gemini else "ayúdame a planificar un viaje")
#             ai_response_text = response.text
#         except Exception as e:
#             print(f"[TravelAgent {self.session_id} ERROR] en explorador_node: {e}")
#             ai_response_text = "Uff, parece que mis mapas mentales se mezclaron un poco. ¿Podrías repetirme eso?"
#         required_fields = ["Origen:", "Destino:", "Fecha de salida:", "Fecha de regreso:", "Viajeros:", "Presupuesto:", "Intereses:", "Correo:", "Teléfono:", "¿Solo una ciudad?"]
#         summary_detected_flag = sum(1 for field in required_fields if field.lower() in ai_response_text.lower()) >= 8
#         return {"messages": [AIMessage(content=ai_response_text)], "summary_detected": summary_detected_flag}

#     def extract_data_node(self, state: TravelAgentState) -> dict:
#         if state["summary_detected"]:
#             extracted = self._extract_travel_info(state["messages"][-1].content)
#             if not extracted.get("destination") or extracted.get("destination", "").lower() in ["aún por decidir", "un lugar cálido", ""]:
#                 return {"extracted_data": extracted, "final_answer_generated": False, "summary_detected": False}
#             return {"extracted_data": extracted, "final_answer_generated": True}
#         return {"extracted_data": state.get("extracted_data", {}), "final_answer_generated": False}

#     def save_data_node(self, state: TravelAgentState) -> dict:
#         if state["final_answer_generated"] and state["extracted_data"].get("destination"):
#             data_to_save = state["extracted_data"].copy()
#             data_to_save["session_id"] = self.session_id
#             self._save_to_json(data_to_save)
#         return {}

#     def should_continue_or_extract(self, state: TravelAgentState) -> str:
#         return "extract_data" if state["summary_detected"] else "continue_chat"

#     def should_save_or_end(self, state: TravelAgentState) -> str:
#         return "save_data" if state["final_answer_generated"] and state["extracted_data"].get("destination") else END

#     def _build_graph(self):
#         workflow = StateGraph(TravelAgentState)
#         workflow.add_node("explorador", self.explorador_node)
#         workflow.add_node("extract_data", self.extract_data_node)
#         workflow.add_node("save_data", self.save_data_node)
#         workflow.set_entry_point("explorador")
#         workflow.add_conditional_edges("explorador", self.should_continue_or_extract, {"extract_data": "extract_data", "continue_chat": END})
#         workflow.add_conditional_edges("extract_data", self.should_save_or_end, {"save_data": "save_data", END: END})
#         workflow.add_edge("save_data", END)
#         self.app = workflow.compile()

#     def get_initial_greeting(self) -> str:
#         return self.current_state["messages"][0].content if self.current_state["messages"] else self.INITIAL_GREETING

#     def is_conversation_finished(self) -> bool:
#         return self.current_state["final_answer_generated"] and bool(self.current_state["extracted_data"].get("destination"))

#     def get_final_data(self) -> dict:
#         return self.current_state["extracted_data"] if self.is_conversation_finished() else {}

#     def process_user_input(self, user_input_text: str) -> str:
#         if not self.current_state["api_configured"] or not self.app:
#             return "Lo siento, el subagente de viajes no está configurado correctamente (API o grafo)."
#         if self.is_conversation_finished():
#              print(f"[TravelAgent {self.session_id}] WARN: process_user_input llamado después de finalizar. Agente reseteado.")
#              self.reset_state() # Resetear si se llama después de finalizar

#         self.current_state["messages"].append(HumanMessage(content=user_input_text))
#         updated_state_values = self.app.invoke({"messages": self.current_state["messages"]})
#         self.current_state.update(updated_state_values)
#         ai_response = self.current_state["messages"][-1].content
#         return ai_response if ai_response.strip() else "No he obtenido respuesta del explorador. ¿Intentamos otra cosa?"

# # --- LangChain Tool Definition ---
# class TravelPlannerInput(BaseModel):
#     user_query: str = Field(description="La consulta o respuesta más reciente del usuario relacionada con la planificación del viaje.")

# class TravelPlannerTool(BaseTool):
#     name: str = "travel_planner_tool"
#     description: str = (
#         "Útil para ayudar a los usuarios a planificar viajes completos, desde la elección del destino hasta la recopilación de todos los detalles. "
#         "Esta herramienta iniciará y gestionará una conversación interactiva con el usuario. "
#         "Debes usar esta herramienta cuando el usuario quiera 'planificar un viaje', 'buscar un destino de vacaciones', 'organizar una escapada', o similar. "
#         "Pasa la consulta completa y más reciente del usuario a esta herramienta. "
#         "La herramienta devolverá la respuesta del asistente de viajes para mostrarla al usuario. "
#         "Si la planificación del viaje está completa, la respuesta lo indicará y contendrá un resumen final."
#     )
#     args_schema: Type[BaseModel] = TravelPlannerInput
#     _travel_agent_instance: TravelAgentLangGraph = None
#     _session_id_for_agent: str = None # Para identificar la sesión del agente interno

#     def _init_agent(self, tool_session_id: str = None):
#         # Si no se provee un tool_session_id, genera uno para esta instancia de la herramienta
#         current_tool_session = tool_session_id or self._session_id_for_agent or f"tool_instance_{id(self)}"

#         if self._travel_agent_instance is None or \
#            self._session_id_for_agent != current_tool_session or \
#            self._travel_agent_instance.is_conversation_finished():

#             if self._travel_agent_instance and self._travel_agent_instance.is_conversation_finished():
#                 print(f"[Tool] Agente de viajes previo ({self._travel_agent_instance.session_id}) había finalizado. Creando/reseteando para {current_tool_session}.")
            
#             print(f"[Tool] Inicializando TravelAgentLangGraph para la sesión de herramienta: {current_tool_session}")
            
#             try:
#                 self._travel_agent_instance = TravelAgentLangGraph(
#                     api_key=API_KEY_TO_USE,
#                     system_prompt=SYSTEM_PROMPT_EXPLORADOR,
#                     session_id=current_tool_session
#                 )
#                 self._session_id_for_agent = current_tool_session # Actualizar el session id de la herramienta
#             except (ValueError, ConnectionError) as e: # Capturar errores específicos de init
#                 print(f"[Tool ERROR] No se pudo inicializar TravelAgentLangGraph: {e}")
#                 raise RuntimeError(f"Fallo al inicializar el subagente de viajes: {e}") from e
#             except Exception as e: # Capturar cualquier otra excepción durante la inicialización
#                 print(f"[Tool ERROR inesperado] No se pudo inicializar TravelAgentLangGraph: {e}")
#                 raise RuntimeError(f"Fallo inesperado al inicializar el subagente de viajes: {e}") from e
    
#     def _run(self, user_query: str, **kwargs: Any) -> str:
#         try:
#             # Asegurarse de que el agente esté inicializado para la sesión actual de la herramienta
#             self._init_agent() 
#         except RuntimeError as e:
#             return str(e) 

#         if not self._travel_agent_instance or not self._travel_agent_instance.current_state["api_configured"]:
#              return "Error: El subagente de viajes no está listo o no tiene API configurada."

#         is_first_user_turn_for_agent = (
#             len(self._travel_agent_instance.current_state["messages"]) == 1 and
#             isinstance(self._travel_agent_instance.current_state["messages"][0], AIMessage)
#         )
#         initial_greeting_if_first_turn = ""
#         if is_first_user_turn_for_agent:
#             initial_greeting_if_first_turn = f"{self._travel_agent_instance.get_initial_greeting()}\n\n"
        
#         agent_response = self._travel_agent_instance.process_user_input(user_query)
#         full_response = f"{initial_greeting_if_first_turn}{agent_response}"

#         if self._travel_agent_instance.is_conversation_finished():
#             final_data = self._travel_agent_instance.get_final_data()
#             return (f"PLANIFICACIÓN DE VIAJE COMPLETADA.\n"
#                     f"{full_response}\n" # full_response ya contiene el saludo inicial (si aplica) + el resumen del agente
#                     f"Datos finales recopilados: {json.dumps(final_data)}")
#         else:
#             return full_response

#     async def _arun(self, user_query: str, **kwargs: Any) -> str:
#         print("[Tool WARN] _arun llamado, usando implementación síncrona _run.")
#         return self._run(user_query, **kwargs)

# # --- Bloque para Chatear Directamente desde este Archivo ---
# if __name__ == "__main__":
#     print("--- Chat Interactivo con TravelPlannerTool ---")
#     print("Escribe 'salir' para terminar.")

#     if not API_KEY_TO_USE or API_KEY_TO_USE == "YOUR_FALLBACK_API_KEY":
#         print("\nADVERTENCIA: La API Key para el TravelAgent no está configurada correctamente.")
#         print("El agente podría no funcionar. Por favor, configura GOOGLE_API_KEY o TRAVEL_AGENT_API_KEY.")
#         # No salimos, pero el agente probablemente fallará al inicializar si la key es mala.
    
#     # Creamos una instancia de la herramienta para esta sesión de chat
#     # Esta instancia de la herramienta mantendrá el estado de UNA conversación de viaje a la vez.
#     # Si escribes "salir" y vuelves a ejecutar el script, se creará una nueva instancia.
#     try:
#         chat_tool = TravelPlannerTool()
#         # Forzar la inicialización del agente interno al principio
#         # El _run lo haría, pero para mostrar el saludo inicial del agente si es el primer uso:
#         chat_tool._init_agent(tool_session_id="interactive_chat_session") 
        
#         # Mostrar el saludo inicial si es la primera vez que se usa el agente interno
#         # y el agente no ha sido "usado" todavía (es decir, process_user_input no ha sido llamado).
#         # Esto es un poco redundante con la lógica dentro de _run, pero para un chat directo
#         # puede ser bueno ver el saludo explícitamente.
#         if chat_tool._travel_agent_instance and \
#            len(chat_tool._travel_agent_instance.current_state["messages"]) == 1 and \
#            isinstance(chat_tool._travel_agent_instance.current_state["messages"][0], AIMessage):
#             print(f"\n<< Asistente de Viajes:\n{chat_tool._travel_agent_instance.get_initial_greeting()}")

#     except RuntimeError as e:
#         print(f"\n[ERROR CRÍTICO AL INICIAR] No se pudo inicializar la herramienta de chat: {e}")
#         print("Verifica la configuración de la API Key y la conexión a internet.")
#         exit()
#     except Exception as e: # Captura otras excepciones inesperadas durante la inicialización
#         print(f"\n[ERROR INESPERADO AL INICIAR] {e}")
#         exit()


########################################
from langgraph.prebuilt import create_react_agent

def explorador(hotel_name: str):
    """Book a hotel"""
    return f"Successfully booked a stay at {hotel_name}."

explorador = create_react_agent(
    model="google_genai:gemini-2.0-flash",
    tools=[],
    prompt=SYSTEM_PROMPT_EXPLORADOR,
    name="explorador"
)

    # while True:
    #     user_input = input("\n>> Tú: ")
    #     if user_input.lower() == "salir":
    #         print("\n<< Asistente de Viajes:\n¡Hasta luego!")
    #         break
    #     if not user_input.strip():
    #         print("<< Asistente de Viajes:\nPor favor, escribe algo.")
    #         continue
        
    #     try:
    #         # Llamamos directamente al método _run de la herramienta
    #         # El método _run ya maneja la lógica de saludo inicial si es necesario.
    #         tool_response = chat_tool._run(user_query=user_input)
    #         print(f"\n<< Asistente de Viajes:\n{tool_response}")

    #         if "PLANIFICACIÓN DE VIAJE COMPLETADA" in tool_response:
    #             print("\n[INFO] La planificación ha finalizado. Puedes empezar una nueva o salir.")
    #             # La herramienta se reseteará automáticamente en la próxima llamada a _run
    #             # si el agente interno había finalizado, gracias a la lógica en _init_agent y process_user_input.
        
    #     except Exception as e:
    #         print(f"\n[ERROR EN EL TURNO] Ocurrió un error: {e}")
    #         # Considerar si se debe intentar reiniciar la herramienta o simplemente continuar